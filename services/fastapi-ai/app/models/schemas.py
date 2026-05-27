"""Pydantic request / response models for the AI estimator service."""

from decimal import Decimal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

class EstimateRequest(BaseModel):
    """Input for estimate generation."""

    description: str = Field(
        ...,
        min_length=10,
        description="Текстовое описание работ",
    )
    area_sqm: float = Field(
        ...,
        gt=0,
        description="Площадь объекта, м²",
    )
    project_type: str = Field(
        ...,
        description="Тип объекта (квартира, офис, склад и т.д.)",
    )


class OptimizeRequest(BaseModel):
    """Input for estimate optimization."""

    items: list[dict] = Field(
        ...,
        min_length=1,
        description="Позиции сметы для оптимизации",
    )


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class EstimateItem(BaseModel):
    """Single line in an estimate."""

    gesn_code: str = Field(..., description="Код ГЭСН/ФЕР")
    name: str = Field(..., description="Наименование работы")
    unit: str = Field(..., description="Единица измерения (м², м.п., шт)")
    quantity: float = Field(..., ge=0)
    unit_price: Decimal = Field(..., ge=0, decimal_places=2)
    amount: Decimal = Field(..., ge=0, decimal_places=2)


class EstimateResponse(BaseModel):
    """Full estimate returned to the client."""

    items: list[EstimateItem]
    total: Decimal = Field(..., decimal_places=2)
    ai_suggestions: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Health-check payload."""

    status: str = "ok"
    version: str = "0.1.0"
