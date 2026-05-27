"""Pydantic request / response models for the AI estimator service."""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

class EstimateRequest(BaseModel):
    """Input for estimate generation."""

    description: str = Field(
        ...,
        min_length=20,
        description="Текстовое описание работ (>= 20 символов)",
    )
    area_sqm: float = Field(
        ...,
        gt=0,
        description="Площадь объекта, м²",
    )
    project_type: str = Field(
        default="квартира",
        description="Тип объекта (квартира, офис, склад и т.д.)",
    )
    region: str = Field(
        default="moscow",
        description="Субъект РФ для индексов Минстроя",
    )


class OptimizeRequest(BaseModel):
    """Input for estimate optimization."""

    items: list[dict] = Field(
        ...,
        min_length=1,
        description="Позиции сметы для оптимизации",
    )


class ExportRequest(BaseModel):
    """Input for PDF/XLSX export of an estimate."""

    format: str = Field(
        default="pdf",
        pattern=r"^(pdf|xlsx)$",
        description="Формат экспорта: pdf или xlsx",
    )
    company_name: str = Field(
        default="",
        description="Название компании для шапки",
    )
    company_inn: str = Field(
        default="",
        description="ИНН компании для шапки",
    )


# ---------------------------------------------------------------------------
# Domain value objects
# ---------------------------------------------------------------------------

class GesnRate(BaseModel):
    """Single ГЭСН/ФЕР rate record from Elasticsearch."""

    code: str = Field(..., description="Код ГЭСН/ФЕР")
    rate_type: str = Field(..., description="gesn | fer | ter")
    description: str = Field(..., description="Описание работ")
    unit: str = Field(..., description="Единица измерения")
    base_rate: Decimal = Field(..., ge=0, decimal_places=2)
    overhead_rate: Decimal = Field(default=Decimal("0"), decimal_places=4)
    profit_rate: Decimal = Field(default=Decimal("0"), decimal_places=4)
    category: str = Field(default="", description="Категория работ для индексов")
    match_score: float = Field(default=0.0, description="Оценка релевантности")


class OptimizationSuggestion(BaseModel):
    """Single optimization suggestion for an estimate line."""

    suggestion_type: str = Field(
        ...,
        description="OVERPRICED | ALTERNATIVE",
    )
    line_gesn_code: str = Field(..., description="Код ГЭСН/ФЕР исходной позиции")
    alternative_code: Optional[str] = Field(
        default=None,
        description="Альтернативный код ГЭСН/ФЕР",
    )
    message: str = Field(..., description="Описание рекомендации")
    deviation_pct: Optional[Decimal] = Field(
        default=None,
        decimal_places=1,
        description="Отклонение от рыночной цены, %",
    )
    potential_savings: Decimal = Field(
        ...,
        ge=0,
        decimal_places=2,
        description="Потенциальная экономия, руб.",
    )


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class EstimateItem(BaseModel):
    """Single line in an estimate."""

    gesn_code: str = Field(..., description="Код ГЭСН/ФЕР")
    name: str = Field(..., description="Наименование работы")
    unit: str = Field(..., description="Единица измерения (м², м.п., шт)")
    quantity: Decimal = Field(..., ge=0, decimal_places=4)
    base_rate: Decimal = Field(..., ge=0, decimal_places=2)
    index_coefficient: Decimal = Field(
        default=Decimal("1.0000"),
        decimal_places=4,
        description="Индекс пересчёта Минстроя",
    )
    unit_price: Decimal = Field(..., ge=0, decimal_places=2)
    amount: Decimal = Field(..., ge=0, decimal_places=2)
    match_score: float = Field(default=0.0, description="AI confidence")
    is_overpriced: bool = Field(default=False)
    manual_override: bool = Field(default=False)


class EstimateResponse(BaseModel):
    """Full estimate returned to the client."""

    items: list[EstimateItem]
    subtotal: Decimal = Field(..., decimal_places=2)
    nds_rate: Decimal = Field(default=Decimal("0.20"), decimal_places=2)
    nds_amount: Decimal = Field(..., decimal_places=2)
    grand_total: Decimal = Field(..., decimal_places=2)
    ai_suggestions: list[str] = Field(default_factory=list)
    optimization: list[OptimizationSuggestion] = Field(default_factory=list)


class OptimizeResponse(BaseModel):
    """Optimization result."""

    suggestions: list[OptimizationSuggestion]
    total_potential_savings: Decimal = Field(..., decimal_places=2)


class ExportResponse(BaseModel):
    """Export result — returns raw bytes info."""

    filename: str
    content_type: str
    size_bytes: int


class HealthResponse(BaseModel):
    """Health-check payload."""

    status: str = "ok"
    version: str = "0.1.0"
