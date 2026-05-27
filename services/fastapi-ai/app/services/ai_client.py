"""OpenAI-compatible AI client for Cloud.ru / OpenAI Foundation Models.

Provider switch is purely env-based: change AI_BASE_URL. No LiteLLM.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal

from openai import AsyncOpenAI

from app.config import Settings

logger = logging.getLogger(__name__)

# System prompt grounding the model in Russian construction pricing norms.
_ESTIMATE_SYSTEM = (
    "Ты — ИИ-сметчик для строительных проектов в России. "
    "Используй расценки ГЭСН/ФЕР и актуальные индексы Минстроя. "
    "Ответ — ТОЛЬКО валидный JSON-массив объектов с полями: "
    "gesn_code, name, unit, quantity, unit_price, amount. "
    "unit_price и amount — числа с 2 знаками после запятой. "
    "Не добавляй пояснений вне JSON."
)

_OPTIMIZE_SYSTEM = (
    "Ты — аналитик строительных смет. "
    "Для каждой позиции сравни цену со среднерыночной. "
    "Если цена > 10% выше среднерыночной — отметь. "
    "Ответ — ТОЛЬКО валидный JSON-массив строк-рекомендаций на русском языке. "
    "Не добавляй пояснений вне JSON."
)


class AIClient:
    """Thin wrapper around AsyncOpenAI that targets a single model."""

    def __init__(self, settings: Settings) -> None:
        self.client = AsyncOpenAI(
            base_url=settings.AI_BASE_URL,
            api_key=settings.AI_API_KEY,
        )
        self.model = settings.AI_MODEL

    # ------------------------------------------------------------------
    # Estimate generation
    # ------------------------------------------------------------------

    async def generate_estimate(
        self,
        description: str,
        area_sqm: float,
        project_type: str = "квартира",
    ) -> dict:
        """Generate a structured estimate from a text description.

        Returns a dict with keys ``items`` (list[dict]) and
        ``ai_suggestions`` (list[str]).
        """
        user_prompt = (
            f"Описание работ: {description}\n"
            f"Площадь: {area_sqm} м²\n"
            f"Тип объекта: {project_type}\n\n"
            "Сформируй смету."
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _ESTIMATE_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )

        raw = response.choices[0].message.content or "[]"
        items = self._parse_json(raw, fallback=[])

        # Compute total using Decimal to avoid float rounding errors.
        total = sum(Decimal(str(it.get("amount", 0))) for it in items)

        return {
            "items": items,
            "total": total,
            "ai_suggestions": [],
        }

    # ------------------------------------------------------------------
    # Optimization suggestions
    # ------------------------------------------------------------------

    async def optimize_estimate(self, items: list[dict]) -> list[str]:
        """Compare estimate items to market benchmarks and return suggestions."""
        user_prompt = (
            "Позиции сметы:\n"
            + json.dumps(items, ensure_ascii=False, indent=2)
            + "\n\nДай рекомендации по оптимизации."
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _OPTIMIZE_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )

        raw = response.choices[0].message.content or "[]"
        return self._parse_json(raw, fallback=[])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json(text: str, fallback):  # noqa: ANN001
        """Best-effort JSON extraction from model output."""
        # Strip markdown fences if present.
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse AI response as JSON: %s", text[:200])
            return fallback
