# -*- coding: utf-8 -*-
"""Stili e helper condivisi per i PDF del progetto v2."""
from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
RESULTS = ROOT / "eval" / "results"

# --- palette ---------------------------------------------------------------
CREAM = colors.HexColor("#FAF7F2")
WHITE = colors.white
BROWN = colors.HexColor("#6B4429")
BROWN_DARK = colors.HexColor("#3D2C20")
GREEN = colors.HexColor("#4F6B4D")
GOLD = colors.HexColor("#C89B5A")
INK = colors.HexColor("#252525")
GREY = colors.HexColor("#5B5B5B")
LIGHT_BROWN = colors.HexColor("#F3E9DF")
LIGHT_GREEN = colors.HexColor("#E8EFE6")
LIGHT_BLUE = colors.HexColor("#E9EFF7")
LIGHT_RED = colors.HexColor("#F6E7E4")
LINE = colors.HexColor("#DED2C4")
PALE = colors.HexColor("#F7F3EE")

# --- font ------------------------------------------------------------------
FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_ITALIC = "Helvetica-Oblique"
DISPLAY = "Helvetica-Bold"
MONO = "Courier"

for name, bold, italic in (
    ("C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/calibrib.ttf", "C:/Windows/Fonts/calibrii.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/ariali.ttf"),
):
    if all(Path(path).exists() for path in (name, bold, italic)):
        pdfmetrics.registerFont(TTFont("DocBody", name))
        pdfmetrics.registerFont(TTFont("DocBody-Bold", bold))
        pdfmetrics.registerFont(TTFont("DocBody-Italic", italic))
        pdfmetrics.registerFontFamily(
            "DocBody", normal="DocBody", bold="DocBody-Bold", italic="DocBody-Italic"
        )
        FONT = "DocBody"
        FONT_BOLD = "DocBody-Bold"
        FONT_ITALIC = "DocBody-Italic"
        break

for candidate in ("C:/Windows/Fonts/georgiab.ttf", "C:/Windows/Fonts/arialbd.ttf"):
    if Path(candidate).exists():
        pdfmetrics.registerFont(TTFont("DocDisplay", candidate))
        DISPLAY = "DocDisplay"
        break

for candidate in ("C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/cour.ttf"):
    if Path(candidate).exists():
        pdfmetrics.registerFont(TTFont("DocMono", candidate))
        MONO = "DocMono"
        break

# --- styles ----------------------------------------------------------------
_ss = getSampleStyleSheet()
STYLE = {
    "body": ParagraphStyle(
        "Body",
        parent=_ss["BodyText"],
        fontName=FONT,
        fontSize=9.8,
        leading=14.4,
        alignment=TA_JUSTIFY,
        textColor=INK,
        spaceAfter=6,
    ),
    "lead": ParagraphStyle(
        "Lead",
        parent=_ss["BodyText"],
        fontName=FONT,
        fontSize=11.2,
        leading=16,
        alignment=TA_LEFT,
        textColor=BROWN_DARK,
        spaceAfter=10,
    ),
    "small": ParagraphStyle(
        "Small",
        parent=_ss["BodyText"],
        fontName=FONT,
        fontSize=8.6,
        leading=12,
        textColor=GREY,
        spaceAfter=4,
    ),
    "caption": ParagraphStyle(
        "Caption",
        parent=_ss["BodyText"],
        fontName=FONT_ITALIC,
        fontSize=8,
        leading=11,
        textColor=GREY,
        spaceAfter=4,
    ),
    "h1": ParagraphStyle(
        "H1",
        parent=_ss["Heading1"],
        fontName=DISPLAY,
        fontSize=18,
        leading=22,
        textColor=BROWN_DARK,
        spaceBefore=4,
        spaceAfter=6,
    ),
    "h2": ParagraphStyle(
        "H2",
        parent=_ss["Heading2"],
        fontName=DISPLAY,
        fontSize=13,
        leading=17,
        textColor=BROWN,
        spaceBefore=12,
        spaceAfter=4,
    ),
    "h3": ParagraphStyle(
        "H3",
        parent=_ss["Heading3"],
        fontName=FONT_BOLD,
        fontSize=10.5,
        leading=14,
        textColor=BROWN_DARK,
        spaceBefore=8,
        spaceAfter=3,
    ),
    "bullet": ParagraphStyle(
        "Bullet",
        parent=_ss["BodyText"],
        fontName=FONT,
        fontSize=9.6,
        leading=13.6,
        leftIndent=14,
        bulletIndent=4,
        textColor=INK,
        spaceAfter=3,
    ),
    "table": ParagraphStyle(
        "TableCell",
        parent=_ss["BodyText"],
        fontName=FONT,
        fontSize=8.6,
        leading=11.4,
        textColor=INK,
    ),
    "table_header": ParagraphStyle(
        "TableHeader",
        parent=_ss["BodyText"],
        fontName=FONT_BOLD,
        fontSize=8.6,
        leading=11.4,
        textColor=WHITE,
    ),
    "table_small": ParagraphStyle(
        "TableCellSmall",
        parent=_ss["BodyText"],
        fontName=FONT,
        fontSize=7.9,
        leading=10.2,
        textColor=INK,
    ),
    "table_header_small": ParagraphStyle(
        "TableHeaderSmall",
        parent=_ss["BodyText"],
        fontName=FONT_BOLD,
        fontSize=7.9,
        leading=10.2,
        textColor=WHITE,
    ),
    "code": ParagraphStyle(
        "Code",
        parent=_ss["Code"],
        fontName=MONO,
        fontSize=8.2,
        leading=11,
        textColor=colors.HexColor("#2B2B2B"),
    ),
    "cover_kicker": ParagraphStyle(
        "CoverKicker",
        parent=_ss["BodyText"],
        fontName=FONT_BOLD,
        fontSize=10,
        leading=12,
        textColor=GOLD,
        spaceAfter=10,
    ),
    "cover_title": ParagraphStyle(
        "CoverTitle",
        parent=_ss["Title"],
        fontName=DISPLAY,
        fontSize=30,
        leading=36,
        textColor=BROWN_DARK,
        alignment=TA_LEFT,
        spaceAfter=10,
    ),
    "cover_sub": ParagraphStyle(
        "CoverSub",
        parent=_ss["BodyText"],
        fontName=FONT,
        fontSize=13,
        leading=19,
        textColor=GREY,
        alignment=TA_LEFT,
        spaceAfter=18,
    ),
}


def load_json(name: str) -> dict:
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def load_final() -> dict:
    return load_json("latest.json")


def load_llama() -> dict | None:
    candidates = sorted(RESULTS.glob("local_2026*.json"))
    for path in reversed(candidates):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        summary = payload.get("summary", {})
        if "llama-3.2-3b" in str(summary.get("model", "")) and summary.get("total") == 31:
            return payload
    return None


def esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def pct(value, digits: int = 1) -> str:
    if value is None:
        return "n/d"
    quantum = Decimal(1).scaleb(-digits)
    rounded = (Decimal(str(value)) * 100).quantize(
        quantum, rounding=ROUND_HALF_UP
    )
    return f"{rounded:.{digits}f}%".replace(".", ",")


def eur(value: float) -> str:
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " EUR"


def P(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, STYLE[style])


def bullets(items: list[str]) -> list[Paragraph]:
    return [Paragraph(item, STYLE["bullet"], bulletText="•") for item in items]


def section(number: str, title: str) -> list:
    return [
        Spacer(1, 0.15 * cm),
        HRFlowable(width="100%", thickness=2, color=GOLD, spaceBefore=2, spaceAfter=8),
        P(f"{number}. {title}", "h1"),
    ]


def h2(text: str) -> Paragraph:
    return Paragraph(text, STYLE["h2"])


def h3(text: str) -> Paragraph:
    return Paragraph(text, STYLE["h3"])


def table(
    rows: list[list[str]],
    widths: list[float],
    *,
    header: bool = True,
    small: bool = False,
    align_center_from: int = 99,
    zebra: bool = True,
) -> Table:
    data = []
    for r, row in enumerate(rows):
        cells = []
        for c, value in enumerate(row):
            if small:
                style = "table_header_small" if header and r == 0 else "table_small"
            else:
                style = "table_header" if header and r == 0 else "table"
            cells.append(Paragraph(str(value), STYLE[style]))
        data.append(cells)
    obj = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), BROWN))
        commands.append(("TEXTCOLOR", (0, 0), (-1, 0), WHITE))
    if zebra:
        for r in range(1 if header else 0, len(data)):
            if (r - (1 if header else 0)) % 2 == 1:
                commands.append(("BACKGROUND", (0, r), (-1, r), PALE))
    for c in range(align_center_from, len(widths)):
        commands.append(("ALIGN", (c, 1), (c, -1), "CENTER"))
    obj.setStyle(TableStyle(commands))
    return obj


def callout(title: str, body: str, *, accent: colors.Color = GOLD, bg: colors.Color = LIGHT_BROWN) -> Table:
    content = [
        Paragraph(f"<b>{title}</b>", STYLE["body"]),
        Paragraph(body, STYLE["body"]),
    ]
    obj = Table([[content]], colWidths=[16.0 * cm])
    obj.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("BOX", (0, 0), (-1, -1), 0.8, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return obj


def code_block(text: str) -> Table:
    obj = Table([[Preformatted(text, STYLE["code"])]], colWidths=[16.0 * cm])
    obj.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F1EC")),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return obj


def image(path: Path, width: float, caption: str | None = None) -> list:
    from PIL import Image as PILImage

    with PILImage.open(path) as img:
        w, h = img.size
    height = width * h / w
    out = [Image(str(path), width=width, height=height)]
    if caption:
        out.append(P(caption, "caption"))
    return out


def stat_row(items: list[tuple[str, str]]) -> Table:
    cells = []
    for value, label in items:
        cells.append(
            [
                Paragraph(f"<b>{value}</b>", ParagraphStyle(
                    "StatValue", parent=STYLE["body"], fontName=DISPLAY, fontSize=19,
                    leading=22, textColor=BROWN, alignment=TA_CENTER, spaceAfter=2,
                )),
                Paragraph(label, ParagraphStyle(
                    "StatLabel", parent=STYLE["small"], alignment=TA_CENTER,
                )),
            ]
        )
    obj = Table([cells], colWidths=[16.0 * cm / len(items)] * len(items))
    obj.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return obj


# --- page templates --------------------------------------------------------
PAGE_W, PAGE_H = A4
MARGIN_L = MARGIN_R = 2.0 * cm
MARGIN_T = 2.1 * cm
MARGIN_B = 1.9 * cm
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.6)
    canvas.line(MARGIN_L, 1.45 * cm, PAGE_W - MARGIN_R, 1.45 * cm)
    canvas.setFont(FONT, 7.8)
    canvas.setFillColor(GREY)
    canvas.drawString(MARGIN_L, 1.05 * cm, "Casa & Regali · assistente clienti · v2")
    canvas.drawRightString(PAGE_W - MARGIN_R, 1.05 * cm, f"{doc.page}")
    canvas.restoreState()


def cover_page(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFillColor(CREAM)
    canvas.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    canvas.setFillColor(GOLD)
    canvas.rect(0, PAGE_H - 0.55 * cm, PAGE_W, 0.55 * cm, stroke=0, fill=1)
    canvas.setFillColor(BROWN)
    canvas.rect(MARGIN_L, 3.2 * cm, 1.1 * cm, 0.09 * cm, stroke=0, fill=1)
    canvas.restoreState()


def later_page(canvas, doc) -> None:
    _footer(canvas, doc)


def build_pdf(path: Path, story: list, *, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=MARGIN_L,
        rightMargin=MARGIN_R,
        topMargin=MARGIN_T,
        bottomMargin=MARGIN_B,
        title=title,
        author="Casa & Regali",
        subject="Progetto finale LLM & Agentic AI",
    )
    frame = Frame(
        MARGIN_L, MARGIN_B, CONTENT_W, PAGE_H - MARGIN_T - MARGIN_B, id="body"
    )
    doc.addPageTemplates(
        [
            PageTemplate(id="cover", frames=[frame], onPage=cover_page),
            PageTemplate(id="content", frames=[frame], onPage=later_page),
        ]
    )
    doc.build(story)
    print(f"Scritto {path}")


def cover(
    kicker: str,
    title: str,
    subtitle: str,
    meta: list[str],
) -> list:
    from reportlab.platypus import NextPageTemplate

    out = [
        NextPageTemplate("cover"),
        Spacer(1, 4.0 * cm),
        P(kicker.upper(), "cover_kicker"),
        P(title, "cover_title"),
        P(subtitle, "cover_sub"),
        Spacer(1, 1.2 * cm),
        HRFlowable(width="100%", thickness=1, color=LINE, spaceAfter=14),
    ]
    for line in meta:
        out.append(P(line, "small"))
    out += [NextPageTemplate("content"), PageBreak()]
    return out
