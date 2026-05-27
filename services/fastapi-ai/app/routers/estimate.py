"""Estimate generation, optimization, and export endpoints."""

from __future__ import annotations

import logging
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.models.schemas import (
    EstimateItem,
    EstimateRequest,
    EstimateResponse,
    ExportRequest,
    ExportResponse,
    OptimizationSuggestion,
    OptimizeRequest,
    OptimizeResponse,
)
from app.services.pdf_generator import generate_estimate_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/estimate", tags=["estimates"])

_NDS_RATE = Decimal("0.20")


# ---------------------------------------------------------------------------
# POST /api/v1/estimate/generate
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=EstimateResponse)
async def generate_estimate(
    body: EstimateRequest,
    request: Request,
) -> EstimateResponse:
    """Generate a construction estimate from a text description.

    Calls Cloud.ru AI via OpenAI SDK, parses response into structured
    estimate items.  Validates ГЭСН codes against Elasticsearch index
    when available.  Applies Минстрой index coefficients.
    All money as Decimal — never float.
    """
    ai_client = request.app.state.ai_client

    # Try to use ГЭСН validation if Elasticsearch is available
    gesn_service = getattr(request.app.state, "gesn_service", None)

    try:
        if gesn_service:
            # Full pipeline: AI -> ГЭСН lookup -> Минстрой indices
            result = await _generate_with_validation(
                ai_client=ai_client,
                gesn_service=gesn_service,
                description=body.description,
                area_sqm=body.area_sqm,
                project_type=body.project_type,
                region=body.region,
            )
        else:
            # Fallback: AI-only estimate (no Elasticsearch)
            result = await ai_client.generate_estimate(
                description=body.description,
                area_sqm=body.area_sqm,
                project_type=body.project_type,
            )
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="AI provider timeout — try again later",
        )
    except Exception as exc:
        logger.exception("Estimate generation failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Estimate generation failed — AI service unavailable",
        )

    items = _build_estimate_items(result["items"])
    subtotal = Decimal(str(result.get("subtotal", sum(i.amount for i in items))))
    nds_amount = (subtotal * _NDS_RATE).quantize(Decimal("0.01"))
    grand_total = subtotal + nds_amount

    return EstimateResponse(
        items=items,
        subtotal=subtotal,
        nds_rate=_NDS_RATE,
        nds_amount=nds_amount,
        grand_total=grand_total,
        ai_suggestions=result.get("ai_suggestions", []),
    )


async def _generate_with_validation(
    ai_client,
    gesn_service,
    description: str,
    area_sqm: float,
    project_type: str,
    region: str,
) -> dict:
    """Generate estimate with ГЭСН validation against Elasticsearch."""
    # Step 1: Get raw AI estimate
    raw_result = await ai_client.generate_estimate(
        description=description,
        area_sqm=area_sqm,
        project_type=project_type,
    )

    # Step 2: Validate ГЭСН codes
    codes = [item["gesn_code"] for item in raw_result["items"] if item.get("gesn_code")]
    if codes:
        try:
            validation = await gesn_service.bulk_validate(codes)
            invalid_codes = [c for c, valid in validation.items() if not valid]
            if invalid_codes:
                logger.warning(
                    "Invalid ГЭСН codes from AI: %s — searching for alternatives",
                    invalid_codes,
                )
        except Exception as exc:
            logger.warning("ГЭСН validation failed (ES unavailable): %s", exc)

    # Step 3: Search for real ГЭСН rates for each item
    gesn_rates = []
    for item in raw_result["items"]:
        try:
            search_query = f"{item.get('name', '')} {item.get('gesn_code', '')}"
            rates = await gesn_service.search_gesn(search_query, size=1)
            if rates:
                gesn_rates.append(rates[0])
        except Exception as exc:
            logger.warning("ГЭСН search failed for %s: %s", item.get("gesn_code"), exc)

    # Step 4: Enrich with validated rates
    if gesn_rates:
        return await ai_client.generate_estimate_with_validation(
            description=description,
            area_sqm=area_sqm,
            project_type=project_type,
            gesn_rates=gesn_rates,
        )

    return raw_result


# ---------------------------------------------------------------------------
# POST /api/v1/estimate/optimize
# ---------------------------------------------------------------------------

@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_estimate(
    body: OptimizeRequest,
    request: Request,
) -> OptimizeResponse:
    """Return optimization suggestions for estimate items.

    Compares items to market benchmarks, flags items >10% above average.
    Returns up to 10 suggestions sorted by potential savings.
    """
    ai_client = request.app.state.ai_client

    try:
        suggestions = await ai_client.optimize_estimate(body.items)
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="AI provider timeout during optimization",
        )
    except Exception as exc:
        logger.exception("Optimization failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Optimization failed — AI service unavailable",
        )

    # Limit to top 10 suggestions
    top_suggestions = suggestions[:10]
    total_savings = sum(s.potential_savings for s in top_suggestions)

    return OptimizeResponse(
        suggestions=top_suggestions,
        total_potential_savings=total_savings,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/estimate/export/pdf
# ---------------------------------------------------------------------------

@router.post("/export/pdf")
async def export_estimate_pdf(
    body: ExportRequest,
    request: Request,
) -> Response:
    """Generate a PDF from estimate items stored in request state.

    For the MVP the caller must pass items in the request body.
    In full version, estimate_id will fetch from the database.
    """
    # In full version this would fetch from DB by estimate_id.
    # For now, this endpoint demonstrates the PDF generation pipeline.
    # The caller should POST items along with export params.
    raise HTTPException(
        status_code=501,
        detail=(
            "Full export requires estimate persistence (database). "
            "Use POST /api/v1/estimate/generate and render the result client-side, "
            "or use the /api/v1/estimate/render-pdf endpoint with items in the body."
        ),
    )


@router.post("/render-pdf")
async def render_pdf(body: dict) -> Response:
    """Render a PDF directly from estimate data provided in the request body.

    Expected body:
    {
        "items": [...],          # list of estimate items
        "subtotal": "100.00",    # Decimal as string
        "nds_amount": "20.00",
        "grand_total": "120.00",
        "company_name": "...",   # optional
        "company_inn": "..."     # optional
    }
    """
    items = body.get("items", [])
    if not items:
        raise HTTPException(status_code=422, detail="No items provided")

    try:
        subtotal = Decimal(str(body.get("subtotal", 0)))
        nds_amount = Decimal(str(body.get("nds_amount", 0)))
        grand_total = Decimal(str(body.get("grand_total", 0)))
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid money values — use string Decimals")

    try:
        pdf_bytes = generate_estimate_pdf(
            items=items,
            subtotal=subtotal,
            nds_amount=nds_amount,
            grand_total=grand_total,
            company_name=body.get("company_name", ""),
            company_inn=body.get("company_inn", ""),
        )
    except Exception as exc:
        logger.exception("PDF generation failed: %s", exc)
        raise HTTPException(status_code=500, detail="PDF generation failed")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=estimate.pdf",
        },
    )


# ---------------------------------------------------------------------------
# GET /api/v1/estimate/{estimate_id}
# ---------------------------------------------------------------------------

@router.get("/{estimate_id}")
async def get_estimate(estimate_id: int) -> dict:
    """Retrieve a previously generated estimate by ID.

    TODO: wire up to database once persistence layer is implemented.
    """
    raise HTTPException(
        status_code=501,
        detail="Estimate storage is not yet implemented",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_estimate_items(raw_items: list[dict]) -> list[EstimateItem]:
    """Convert raw AI output dicts to validated EstimateItem models."""
    items: list[EstimateItem] = []
    for it in raw_items:
        try:
            quantity = Decimal(str(it.get("quantity", 0)))
            unit_price = Decimal(str(it.get("unit_price", 0)))
            amount = Decimal(str(it.get("amount", 0)))
            base_rate = Decimal(str(it.get("base_rate", unit_price)))
            index_coefficient = Decimal(str(it.get("index_coefficient", "1.0000")))

            items.append(EstimateItem(
                gesn_code=str(it.get("gesn_code", "")),
                name=str(it.get("name", "")),
                unit=str(it.get("unit", "")),
                quantity=quantity,
                base_rate=base_rate,
                index_coefficient=index_coefficient,
                unit_price=unit_price,
                amount=amount,
                match_score=float(it.get("match_score", 0.0)),
                is_overpriced=bool(it.get("is_overpriced", False)),
                manual_override=bool(it.get("manual_override", False)),
            ))
        except Exception as exc:
            logger.warning("Skipping malformed item: %s — %s", it, exc)
            continue

    return items
