"""Elasticsearch service for ГЭСН/ФЕР rate lookup.

Index: gesn_fer_rates — contains ~100K+ rate records with Russian
text fields analyzed via russian_custom analyzer and dense_vector
for semantic (KNN) search.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from elasticsearch import AsyncElasticsearch, NotFoundError

from app.config import Settings
from app.models.schemas import GesnRate

logger = logging.getLogger(__name__)

INDEX_NAME = "gesn_fer_rates"


class GesnSearchService:
    """Thin async wrapper around Elasticsearch for ГЭСН/ФЕР lookups."""

    def __init__(self, settings: Settings) -> None:
        self.es = AsyncElasticsearch(
            hosts=[settings.ELASTICSEARCH_URL],
            request_timeout=10,
        )

    async def close(self) -> None:
        await self.es.close()

    # ------------------------------------------------------------------
    # Full-text search
    # ------------------------------------------------------------------

    async def search_gesn(
        self,
        query: str,
        *,
        size: int = 10,
        rate_type: Optional[str] = None,
    ) -> list[GesnRate]:
        """Full-text search over ГЭСН/ФЕР index.

        Uses multi_match with fuzziness for typo tolerance.
        Optionally filter by rate_type (gesn, fer, ter).
        """
        must_clause: dict = {
            "multi_match": {
                "query": query,
                "fields": ["description^3", "keywords^2", "code"],
                "fuzziness": "AUTO",
            }
        }

        body: dict = {"query": {"bool": {"must": [must_clause]}}, "size": size}

        if rate_type:
            body["query"]["bool"]["filter"] = [
                {"term": {"type": rate_type}}
            ]

        result = await self.es.search(index=INDEX_NAME, body=body)
        return self._hits_to_rates(result)

    # ------------------------------------------------------------------
    # Exact code lookup
    # ------------------------------------------------------------------

    async def get_rate(self, gesn_code: str) -> Optional[GesnRate]:
        """Get a single rate by its exact ГЭСН/ФЕР code."""
        body = {
            "query": {"term": {"code.keyword": gesn_code}},
            "size": 1,
        }
        result = await self.es.search(index=INDEX_NAME, body=body)
        rates = self._hits_to_rates(result)
        return rates[0] if rates else None

    # ------------------------------------------------------------------
    # Bulk validation
    # ------------------------------------------------------------------

    async def bulk_validate(self, codes: list[str]) -> dict[str, bool]:
        """Validate that a list of ГЭСН/ФЕР codes exist in the index.

        Returns a dict mapping each code to True (found) or False.
        """
        if not codes:
            return {}

        body = {
            "query": {"terms": {"code.keyword": codes}},
            "size": len(codes),
            "_source": ["code"],
        }

        try:
            result = await self.es.search(index=INDEX_NAME, body=body)
        except NotFoundError:
            logger.warning("Index %s not found during bulk_validate", INDEX_NAME)
            return {code: False for code in codes}

        found_codes = {
            hit["_source"]["code"]
            for hit in result.get("hits", {}).get("hits", [])
        }
        return {code: (code in found_codes) for code in codes}

    # ------------------------------------------------------------------
    # Semantic (KNN) search
    # ------------------------------------------------------------------

    async def knn_search(
        self,
        query_vector: list[float],
        *,
        k: int = 5,
        num_candidates: int = 50,
    ) -> list[GesnRate]:
        """Semantic search via Elasticsearch KNN on description_vector."""
        body = {
            "knn": {
                "field": "description_vector",
                "query_vector": query_vector,
                "k": k,
                "num_candidates": num_candidates,
            },
            "_source": [
                "code", "type", "description", "unit", "base_rate",
                "overhead_rate", "profit_rate", "category", "keywords",
            ],
        }

        result = await self.es.search(index=INDEX_NAME, body=body)
        return self._hits_to_rates(result)

    # ------------------------------------------------------------------
    # Cross-reference alternatives
    # ------------------------------------------------------------------

    async def find_alternatives(
        self,
        gesn_code: str,
        *,
        size: int = 3,
    ) -> list[GesnRate]:
        """Find alternative rates (ГЭСН <-> ФЕР cross-reference).

        Given a ГЭСН code, find similar ФЕР codes and vice versa.
        """
        source_rate = await self.get_rate(gesn_code)
        if not source_rate:
            return []

        alt_type = "fer" if source_rate.rate_type == "gesn" else "gesn"

        body = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"type": alt_type}},
                        {"match": {"description": source_rate.description}},
                    ]
                }
            },
            "size": size,
        }

        result = await self.es.search(index=INDEX_NAME, body=body)
        return self._hits_to_rates(result)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hits_to_rates(result: dict) -> list[GesnRate]:
        """Convert Elasticsearch hits to GesnRate models."""
        rates: list[GesnRate] = []
        for hit in result.get("hits", {}).get("hits", []):
            src = hit["_source"]
            rates.append(GesnRate(
                code=src.get("code", ""),
                rate_type=src.get("type", "gesn"),
                description=src.get("description", ""),
                unit=src.get("unit", ""),
                base_rate=Decimal(str(src.get("base_rate", "0"))),
                overhead_rate=Decimal(str(src.get("overhead_rate", "0"))),
                profit_rate=Decimal(str(src.get("profit_rate", "0"))),
                category=src.get("category", ""),
                match_score=float(hit.get("_score", 0.0)),
            ))
        return rates
