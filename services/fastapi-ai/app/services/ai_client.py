"""OpenAI-compatible AI client for Cloud.ru / OpenAI Foundation Models.

Provider switch is purely env-based: change AI_BASE_URL. No LiteLLM.
All money calculations use Decimal(str(...)) — never Decimal(float).
"""

from __future__ import annotations

import json
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from openai import AsyncOpenAI

from app.config import Settings
from app.models.schemas import GesnRate, OptimizationSuggestion

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompts — instruct model to return structured JSON
# ---------------------------------------------------------------------------

_ESTIMATE_SYSTEM = (
    "Ты — профессиональный сметчик для строительных проектов в России. "
    "Используй нормативные базы ГЭСН/ФЕР. "
    "Разбери описание работ на отдельные позиции сметы.\n\n"
    "Ответ — ТОЛЬКО валидный JSON-объект с полем \"items\" — массивом объектов. "
    "Каждый объект содержит поля:\n"
    "  - gesn_code: строка — код ГЭСН или ФЕР (например \"ГЭСНр 61-01-001-01\")\n"
    "  - name: строка — наименование работы\n"
    "  - unit: строка — единица измерения (м², м.п., шт, комплект)\n"
    "  - quantity: число — объём работ\n"
    "  - unit_price: число — цена за единицу в рублях (2 знака)\n\n"
    "Не добавляй пояснений, комментариев или текста вне JSON."
)

_OPTIMIZE_SYSTEM = (
    "Ты — аналитик строительных смет. "
    "Для каждой позиции сравни цену со среднерыночной. "
    "Если цена > 10% выше среднерыночной — создай рекомендацию.\n\n"
    "Ответ — ТОЛЬКО валидный JSON-объект с полем \"suggestions\" — массивом. "
    "Каждый объект содержит:\n"
    "  - type: \"OVERPRICED\" или \"ALTERNATIVE\"\n"
    "  - line_gesn_code: код исходной позиции\n"
    "  - alternative_code: код альтернативы (или null)\n"
    "  - message: описание рекомендации на русском\n"
    "  - deviation_pct: отклонение от рынка в % (число)\n"
    "  - potential_savings: экономия в рублях (число с 2 знаками)\n\n"
    "Не добавляй пояснений вне JSON."
)


# ---------------------------------------------------------------------------
# Input sanitization — strip prompt injection attempts
# ---------------------------------------------------------------------------

# Patterns commonly used in prompt injection
_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(previous|above|all)\s+(instructions?|prompts?)",
    r"(?i)you\s+are\s+now",
    r"(?i)system\s*:\s*",
    r"(?i)assistant\s*:\s*",
    r"(?i)forget\s+(everything|all)",
    r"(?i)\[INST\]",
    r"(?i)<\|im_start\|>",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS))


def sanitize_ai_input(text: str) -> str:
    """Remove prompt injection patterns from user text input."""
    cleaned = _INJECTION_RE.sub("", text)
    # Collapse multiple whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


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

        Calls Cloud.ru via OpenAI SDK, parses response into structured items.
        Validates ГЭСН codes against provided gesn_rates if available.
        All money as Decimal(str(...)).

        Returns a dict with keys:
          - items: list[dict] with gesn_code, name, unit, quantity, unit_price, amount
          - subtotal: Decimal
          - ai_suggestions: list[str]
        """
        sanitized = sanitize_ai_input(description)

        user_prompt = (
            f"Описание работ: {sanitized}\n"
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
            timeout=30,
        )

        raw = response.choices[0].message.content or "{}"
        parsed = self._parse_json(raw, fallback={"items": []})

        # Normalize: handle both list and dict responses
        if isinstance(parsed, list):
            raw_items = parsed
        else:
            raw_items = parsed.get("items", [])

        items: list[dict] = []
        subtotal = Decimal("0")

        for it in raw_items:
            try:
                quantity = Decimal(str(it.get("quantity", 0)))
                unit_price = Decimal(str(it.get("unit_price", 0)))
                amount = quantity * unit_price
                # Round to 2 decimal places for money
                amount = amount.quantize(Decimal("0.01"))

                items.append({
                    "gesn_code": str(it.get("gesn_code", "")),
                    "name": str(it.get("name", "")),
                    "unit": str(it.get("unit", "")),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "amount": amount,
                })
                subtotal += amount
            except (InvalidOperation, TypeError, ValueError) as exc:
                logger.warning(
                    "Skipping malformed item from AI response: %s — %s",
                    it, exc,
                )
                continue

        return {
            "items": items,
            "subtotal": subtotal,
            "ai_suggestions": [],
        }

    # ------------------------------------------------------------------
    # Estimate with ГЭСН validation and Минстрой indices
    # ------------------------------------------------------------------

    async def generate_estimate_with_validation(
        self,
        description: str,
        area_sqm: float,
        project_type: str,
        gesn_rates: Optional[list[GesnRate]] = None,
        index_coefficients: Optional[dict[str, Decimal]] = None,
    ) -> dict:
        """Generate estimate and enrich with validated ГЭСН rates and indices.

        If gesn_rates are provided (from Elasticsearch), cross-reference
        AI output against real rates. Apply Минстрой index_coefficients
        when available.

        Returns dict with items containing base_rate, index_coefficient,
        unit_price (indexed), amount.
        """
        result = await self.generate_estimate(
            description=description,
            area_sqm=area_sqm,
            project_type=project_type,
        )

        if not gesn_rates:
            return result

        # Build lookup by code for O(1) access
        rates_by_code: dict[str, GesnRate] = {r.code: r for r in gesn_rates}

        enriched_items: list[dict] = []
        subtotal = Decimal("0")

        for item in result["items"]:
            gesn_code = item["gesn_code"]
            quantity = item["quantity"]

            if gesn_code in rates_by_code:
                rate = rates_by_code[gesn_code]
                base_rate = rate.base_rate
                category = rate.category
                match_score = rate.match_score

                # Применяем индекс Минстроя
                coefficient = Decimal("1.0000")
                if index_coefficients and category in index_coefficients:
                    coefficient = index_coefficients[category]

                # Расчёт по ГЭСН с применением индекса Минстроя
                base_cost = base_rate * quantity
                indexed_cost = base_cost * coefficient
                overhead = indexed_cost * rate.overhead_rate
                profit = indexed_cost * rate.profit_rate
                total = (indexed_cost + overhead + profit).quantize(Decimal("0.01"))
                unit_price = (total / quantity).quantize(Decimal("0.01")) if quantity else Decimal("0")

                enriched_items.append({
                    "gesn_code": gesn_code,
                    "name": rate.description or item["name"],
                    "unit": rate.unit or item["unit"],
                    "quantity": quantity,
                    "base_rate": base_rate,
                    "index_coefficient": coefficient,
                    "unit_price": unit_price,
                    "amount": total,
                    "match_score": match_score,
                    "is_overpriced": False,
                    "manual_override": False,
                })
                subtotal += total
            else:
                # ГЭСН код не найден в базе — используем AI-данные как есть
                logger.warning(
                    "ГЭСН code %s not found in validated rates, using AI data",
                    gesn_code,
                )
                enriched_items.append({
                    **item,
                    "base_rate": item["unit_price"],
                    "index_coefficient": Decimal("1.0000"),
                    "match_score": 0.0,
                    "is_overpriced": False,
                    "manual_override": False,
                })
                subtotal += item["amount"]

        return {
            "items": enriched_items,
            "subtotal": subtotal,
            "ai_suggestions": [],
        }

    # ------------------------------------------------------------------
    # Optimization suggestions
    # ------------------------------------------------------------------

    async def optimize_estimate(
        self,
        items: list[dict],
    ) -> list[OptimizationSuggestion]:
        """Compare estimate items to market benchmarks via AI.

        Returns structured OptimizationSuggestion objects.
        Flags items >10% above average.
        """
        user_prompt = (
            "Позиции сметы:\n"
            + json.dumps(
                items, ensure_ascii=False, indent=2, default=str,
            )
            + "\n\nДай рекомендации по оптимизации."
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _OPTIMIZE_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            timeout=30,
        )

        raw = response.choices[0].message.content or "{}"
        parsed = self._parse_json(raw, fallback={"suggestions": []})

        if isinstance(parsed, list):
            raw_suggestions = parsed
        else:
            raw_suggestions = parsed.get("suggestions", [])

        suggestions: list[OptimizationSuggestion] = []
        for s in raw_suggestions:
            try:
                suggestions.append(OptimizationSuggestion(
                    suggestion_type=str(s.get("type", "OVERPRICED")),
                    line_gesn_code=str(s.get("line_gesn_code", "")),
                    alternative_code=s.get("alternative_code"),
                    message=str(s.get("message", "")),
                    deviation_pct=(
                        Decimal(str(s["deviation_pct"]))
                        if s.get("deviation_pct") is not None
                        else None
                    ),
                    potential_savings=Decimal(str(s.get("potential_savings", 0))),
                ))
            except (InvalidOperation, TypeError, ValueError) as exc:
                logger.warning(
                    "Skipping malformed suggestion: %s — %s", s, exc,
                )
                continue

        # Sort by potential savings descending
        suggestions.sort(key=lambda x: x.potential_savings, reverse=True)
        return suggestions

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json(text: str, fallback):  # noqa: ANN001
        """Best-effort JSON extraction from model output."""
        cleaned = text.strip()
        # Strip markdown fences if present
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
