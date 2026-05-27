"""PDF generation for construction estimates.

Uses reportlab for PDF rendering. All money values are Decimal — formatted
with 2 decimal places and thousands separator.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime, timezone
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_money(value: Decimal) -> str:
    """Format Decimal as string with thousands separator and 2 decimals.

    Example: Decimal("1234567.89") -> "1 234 567.89"
    """
    formatted = f"{value:,.2f}"
    # Replace comma with space for Russian formatting
    return formatted.replace(",", " ")


def _try_register_font() -> str:
    """Try to register a font that supports Cyrillic.

    Returns the font name to use.  Falls back to Helvetica if no
    Cyrillic-capable font is available (PDF will render Latin chars only
    in that case but won't crash).
    """
    # Common paths for DejaVu Sans on Linux
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ]
    for path in font_paths:
        try:
            pdfmetrics.registerFont(TTFont("DejaVuSans", path))
            return "DejaVuSans"
        except Exception:
            continue

    logger.warning(
        "DejaVuSans font not found — PDF will use Helvetica "
        "(Cyrillic characters may not render correctly)"
    )
    return "Helvetica"


# ---------------------------------------------------------------------------
# PDF Generator
# ---------------------------------------------------------------------------


def generate_estimate_pdf(
    items: list[dict],
    subtotal: Decimal,
    nds_amount: Decimal,
    grand_total: Decimal,
    company_name: str = "",
    company_inn: str = "",
    nds_rate: Decimal = Decimal("0.20"),
) -> bytes:
    """Generate a PDF document for a construction estimate.

    Args:
        items: List of estimate line dicts with keys: gesn_code, name,
               unit, quantity, unit_price, amount.
        subtotal: Sum of all line amounts (Decimal).
        nds_amount: VAT amount (Decimal).
        grand_total: Final total including VAT (Decimal).
        company_name: Company name for header.
        company_inn: Company INN for header.
        nds_rate: VAT rate as decimal (0.20 = 20%).

    Returns:
        PDF file content as bytes.
    """
    buffer = io.BytesIO()
    font_name = _try_register_font()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "EstimateTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=16,
        spaceAfter=6 * mm,
    )
    normal_style = ParagraphStyle(
        "EstimateNormal",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9,
    )
    header_style = ParagraphStyle(
        "EstimateHeader",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=10,
        spaceAfter=2 * mm,
    )
    disclaimer_style = ParagraphStyle(
        "EstimateDisclaimer",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=8,
        textColor=colors.grey,
        spaceBefore=10 * mm,
    )

    elements: list = []

    # --- Company header ---
    if company_name:
        elements.append(Paragraph(company_name, header_style))
    if company_inn:
        elements.append(Paragraph(f"INN: {company_inn}", header_style))
    if company_name or company_inn:
        elements.append(Spacer(1, 4 * mm))

    # --- Title ---
    now = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    elements.append(
        Paragraph(f"Smeta ot {now}", title_style)
    )

    # --- Estimate table ---
    table_header = [
        "#",
        "Kod GESN",
        "Naimenovanie",
        "Ed.",
        "Kol-vo",
        "Tsena",
        "Summa",
    ]

    table_data = [table_header]
    for idx, item in enumerate(items, start=1):
        quantity = Decimal(str(item.get("quantity", 0)))
        unit_price = Decimal(str(item.get("unit_price", 0)))
        amount = Decimal(str(item.get("amount", 0)))

        row = [
            str(idx),
            str(item.get("gesn_code", "")),
            str(item.get("name", ""))[:60],  # Truncate long names
            str(item.get("unit", "")),
            f"{quantity:.4f}",
            _format_money(unit_price),
            _format_money(amount),
        ]
        table_data.append(row)

    col_widths = [10 * mm, 35 * mm, 55 * mm, 15 * mm, 20 * mm, 22 * mm, 25 * mm]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), font_name),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTNAME", (0, 1), (-1, -1), font_name),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        # Alignment
        ("ALIGN", (0, 0), (0, -1), "CENTER"),    # #
        ("ALIGN", (3, 0), (3, -1), "CENTER"),    # unit
        ("ALIGN", (4, 0), (-1, -1), "RIGHT"),    # numbers right-aligned
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        # Padding
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))

    # Highlight overpriced lines in yellow
    for idx, item in enumerate(items, start=1):
        if item.get("is_overpriced", False):
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, idx), (-1, idx), colors.HexColor("#fff3cd")),
            ]))

    elements.append(table)
    elements.append(Spacer(1, 5 * mm))

    # --- Totals ---
    nds_pct = int(nds_rate * Decimal("100"))
    totals_data = [
        ["Itogo:", _format_money(subtotal)],
        [f"NDS {nds_pct}%:", _format_money(nds_amount)],
        ["VSEGO:", _format_money(grand_total)],
    ]
    totals_table = Table(
        totals_data,
        colWidths=[130 * mm, 50 * mm],
    )
    totals_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 2), (-1, 2), font_name),
        ("LINEABOVE", (0, 2), (-1, 2), 1, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    elements.append(totals_table)

    # --- Disclaimer ---
    elements.append(
        Paragraph(
            "Predvaritelnaya otsenka. Tochnost zavisit ot polnoty opisaniya rabot.",
            disclaimer_style,
        )
    )

    doc.build(elements)
    return buffer.getvalue()
