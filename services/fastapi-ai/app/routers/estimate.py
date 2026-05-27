"""Estimate generation and optimization endpoints."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import (
    EstimateItem,
    EstimateRequest,
    EstimateResponse,
    OptimizeRequest,
)

router = APIRouter(prefix="/api/v1/estimate", tags=["estimates"])


@router.post("/generate", response_model=EstimateResponse)
async def generate_estimate(body: EstimateRequest, request: Request) -> EstimateResponse:
    """Generate a construction estimate from a text description."""
    ai_client = request.app.state.ai_client

    result = await ai_client.generate_estimate(
        description=body.description,
        area_sqm=body.area_sqm,
        project_type=body.project_type,
    )

    items = [
        EstimateItem(
            gesn_code=it.get("gesn_code", ""),
            name=it.get("name", ""),
            unit=it.get("unit", ""),
            quantity=it.get("quantity", 0),
            unit_price=Decimal(str(it.get("unit_price", 0))),
            amount=Decimal(str(it.get("amount", 0))),
        )
        for it in result["items"]
    ]

    return EstimateResponse(
        items=items,
        total=Decimal(str(result["total"])),
        ai_suggestions=result.get("ai_suggestions", []),
    )


@router.post("/optimize")
async def optimize_estimate(body: OptimizeRequest, request: Request) -> dict:
    """Return optimization suggestions for an existing estimate."""
    ai_client = request.app.state.ai_client
    suggestions = await ai_client.optimize_estimate(body.items)
    return {"suggestions": suggestions}


@router.get("/{estimate_id}")
async def get_estimate(estimate_id: int) -> dict:
    """Retrieve a previously generated estimate by ID.

    TODO: wire up to database once persistence layer is implemented.
    """
    raise HTTPException(
        status_code=501,
        detail="Estimate storage is not yet implemented",
    )
