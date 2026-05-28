from pathlib import Path
import re
from textwrap import wrap

import markdown as md
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from operia.reports.models import Presentation, Report
from operia.legal_report.services.text_service import normalize_spanish
from operia.core.config import settings

EXPORT_DIR = settings.exports_dir


def export_markdown(report: Report) -> Path:
    path = EXPORT_DIR / f"report-{report.id}.md"
    path.write_text(normalize_spanish(report.markdown_content), encoding="utf-8")
    return path


def export_html(report: Report) -> Path:
    html = md.markdown(normalize_spanish(report.markdown_content), extensions=["tables"])
    path = EXPORT_DIR / f"report-{report.id}.html"
    path.write_text(f"<!doctype html><meta charset='utf-8'><body>{html}</body>", encoding="utf-8")
    return path


def _markdown_sections(markdown: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_title = "Informe"
    current_lines: list[str] = []
    for line in normalize_spanish(markdown).splitlines():
        if line.startswith("## "):
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line[3:].strip()
            current_lines = []
        elif line.startswith("# "):
            current_title = line[2:].strip()
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))
    return sections


def _clean_markdown_text(text: str) -> str:
    return (
        normalize_spanish(text)
        .replace("**", "")
        .replace("`", "")
        .replace("| --- | --- | --- | --- | --- |", "")
        .strip()
    )


def export_docx(report: Report) -> Path:
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)

    styles = document.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(10.5)
    styles["Title"].font.name = "Aptos Display"
    styles["Title"].font.size = Pt(24)
    styles["Title"].font.bold = True
    styles["Heading 1"].font.color.rgb = RGBColor(15, 23, 42)
    styles["Heading 2"].font.color.rgb = RGBColor(21, 94, 117)

    logo = _logo_path()
    if logo:
        paragraph = document.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run()
        run.add_picture(str(logo), width=Inches(3.6))

    title = document.add_heading(normalize_spanish(report.title), 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = document.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.add_run(f"Caso {report.case.case_code} | {normalize_spanish(report.case.incident_type)}").bold = True
    document.add_paragraph("Documento asistido por IA. Requiere revisión humana profesional.").alignment = WD_ALIGN_PARAGRAPH.CENTER

    table = document.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    headers = ["Evidencias", "Hallazgos", "Daño estimado", "Estado"]
    values = [
        str(len(report.case.evidence)),
        str(len(report.case.findings)),
        f"{sum(item.amount for item in report.case.damage_items):,.2f} ARS",
        normalize_spanish(report.status),
    ]
    for index, cell in enumerate(table.rows[0].cells):
        cell.text = f"{headers[index]}\n{values[index]}"

    document.add_page_break()
    for line in normalize_spanish(report.markdown_content).splitlines():
        if line.startswith("# "):
            document.add_heading(line[2:], level=1)
        elif line.startswith("## "):
            document.add_heading(line[3:], level=2)
        elif line.startswith("### "):
            document.add_heading(line[4:], level=3)
        elif line.startswith("|") and "---" not in line:
            document.add_paragraph(_clean_markdown_text(line))
        elif line.strip():
            document.add_paragraph(_clean_markdown_text(line))
    path = EXPORT_DIR / f"report-{report.id}.docx"
    document.save(path)
    return path


def export_pdf(report: Report) -> Path:
    path = EXPORT_DIR / f"report-{report.id}.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    case = report.case
    logo = _logo_path()
    sections = _markdown_sections(report.markdown_content)
    total_damage = sum(item.amount for item in case.damage_items)

    def report_background(page_label: str = "", show_header_logo: bool = True) -> None:
        c.setFillColor(colors.white)
        c.rect(0, 0, width, height, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#f6f9fd"))
        c.roundRect(28, 28, width - 56, height - 56, 16, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.roundRect(44, 44, width - 88, height - 88, 14, fill=1, stroke=0)
        c.setStrokeColor(colors.HexColor("#dbe5f1"))
        c.roundRect(44, 44, width - 88, height - 88, 14, fill=0, stroke=1)
        c.setStrokeColor(colors.HexColor("#18a999"))
        c.setLineWidth(2)
        c.line(64, height - 78, width - 64, height - 78)
        if logo and show_header_logo:
            c.drawImage(ImageReader(str(logo)), 60, height - 68, width=120, height=44, preserveAspectRatio=True, mask="auto")
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.HexColor("#64748b"))
        c.drawRightString(width - 60, height - 49, "INFORME FORENSE-JURÍDICO")
        if page_label:
            c.drawRightString(width - 60, 34, page_label)

    report_background(show_header_logo=False)
    if logo:
        c.drawImage(ImageReader(str(logo)), 72, height - 188, width=230, height=88, preserveAspectRatio=True, mask="auto")
    _draw_chip(c, 72, height - 210, "INFORME INTEGRAL", "#eef8f7", "#b9ebe4", "#087f5b")
    _draw_chip(c, 190, height - 210, "REVISIÓN HUMANA REQUERIDA", "#fff7ed", "#fed7aa", "#9a3412")
    c.setFont("Helvetica-Bold", 26)
    c.setFillColor(colors.HexColor("#0f172a"))
    _draw_wrapped(c, normalize_spanish(report.title), 72, height - 260, width - 144, "Helvetica-Bold", 26, 31, colors.HexColor("#0f172a"), max_lines=3)
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.HexColor("#475467"))
    c.drawString(74, height - 330, normalize_spanish(f"Caso {case.case_code} | {case.incident_type}"))
    c.drawString(74, height - 350, normalize_spanish(f"Responsable: {case.responsible or 'pendiente'}"))
    c.drawString(74, height - 370, normalize_spanish(f"Jurisdicción: {case.jurisdiction}"))

    card_y = 142
    _draw_metric(c, 72, card_y, "Evidencias", str(len(case.evidence)), "#155e75")
    _draw_metric(c, 230, card_y, "Hallazgos", str(len(case.findings)), "#087f5b")
    _draw_metric(c, 388, card_y, "Daño estimado", f"{total_damage:,.0f} ARS", "#b7791f")
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#64748b"))
    c.drawRightString(width - 72, 74, "Operia Forensic Legal Report | Documento asistido por IA, no sustituye revisión profesional")
    c.showPage()

    page = 1
    for title, content in sections:
        if not content and title == "Operia Forensic Legal Report":
            continue
        report_background(f"Página {page:02d}")
        c.setFont("Helvetica-Bold", 19)
        c.setFillColor(colors.HexColor("#0f172a"))
        y = height - 112
        y = _draw_wrapped(c, normalize_spanish(title), 68, y, width - 136, "Helvetica-Bold", 19, 23, colors.HexColor("#0f172a"), max_lines=2) - 10

        c.setFillColor(colors.HexColor("#f8fbff"))
        c.setStrokeColor(colors.HexColor("#dbe5f1"))
        c.roundRect(64, 76, width - 128, y - 86, 12, fill=1, stroke=1)
        c.setStrokeColor(colors.HexColor("#18a999"))
        c.setLineWidth(3)
        c.line(82, y - 22, 82, 98)
        y -= 25

        for paragraph in _clean_markdown_text(content).splitlines():
            paragraph = paragraph.strip()
            if not paragraph or paragraph.startswith("| ---"):
                y -= 6
                continue
            if y < 110:
                c.showPage()
                page += 1
                report_background(f"Página {page:02d}")
                y = height - 112
            if paragraph.startswith("- "):
                c.setFillColor(colors.HexColor("#18a999"))
                c.circle(94, y + 4, 2.5, fill=1, stroke=0)
                y = _draw_wrapped(c, paragraph[2:], 108, y, width - 176, "Helvetica", 10.5, 14, colors.HexColor("#25324a"), max_lines=6) - 4
            elif paragraph.startswith("|"):
                y = _draw_wrapped(c, paragraph.replace("|", "  "), 96, y, width - 166, "Helvetica", 8.5, 12, colors.HexColor("#25324a"), max_lines=5) - 2
            else:
                y = _draw_wrapped(c, paragraph, 96, y, width - 166, "Helvetica", 10.5, 15, colors.HexColor("#25324a"), max_lines=10) - 6
        c.showPage()
        page += 1

    c.save()
    return path


def _logo_path() -> Path | None:
    project_root = Path(__file__).resolve().parents[3]
    for name in ("operia-logo-cropped.png", "operia-logo.png"):
        candidate = project_root / "frontend" / "src" / "assets" / name
        if candidate.exists():
            return candidate
    return None


def _fit_text(text: str, width: float, font: str, size: int) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines() or [""]:
        words = raw.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            test = f"{current} {word}"
            if stringWidth(test, font, size) <= width:
                current = test
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def _draw_wrapped(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    font: str = "Helvetica",
    size: int = 11,
    leading: int = 15,
    color=colors.HexColor("#25324a"),
    max_lines: int | None = None,
) -> float:
    c.setFont(font, size)
    c.setFillColor(color)
    lines = _fit_text(text, width, font, size)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = f"{lines[-1][: max(0, len(lines[-1]) - 3)]}..."
    for line in lines:
        c.drawString(x, y, line)
        y -= leading
    return y


def _draw_chip(c: canvas.Canvas, x: float, y: float, text: str, fill: str, stroke: str, ink: str) -> None:
    width = stringWidth(text, "Helvetica-Bold", 8) + 18
    c.setFillColor(colors.HexColor(fill))
    c.setStrokeColor(colors.HexColor(stroke))
    c.roundRect(x, y - 13, width, 19, 6, fill=1, stroke=1)
    c.setFillColor(colors.HexColor(ink))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x + 9, y - 8, text)


def _draw_page_background(c: canvas.Canvas, width: float, height: float) -> None:
    c.setFillColor(colors.white)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#f5f8fc"))
    c.roundRect(28, 28, width - 56, height - 56, 18, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.roundRect(48, 48, width - 96, height - 96, 18, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#dbe5f1"))
    c.setLineWidth(0.8)
    c.roundRect(48, 48, width - 96, height - 96, 18, fill=0, stroke=1)
    c.setStrokeColor(colors.HexColor("#18a999"))
    c.setLineWidth(2)
    c.line(70, height - 72, width - 70, height - 72)


def _draw_header(c: canvas.Canvas, presentation: Presentation, width: float, height: float, page_number: int) -> None:
    logo = _logo_path()
    if logo:
        c.drawImage(ImageReader(str(logo)), 66, height - 64, width=118, height=45, preserveAspectRatio=True, mask="auto")
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(width - 66, height - 45, normalize_spanish(presentation.presentation_type).upper())
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#667085"))
    c.drawRightString(width - 66, height - 58, f"Página {page_number:02d}")


def _draw_metric(c: canvas.Canvas, x: float, y: float, label: str, value: str, color: str) -> None:
    c.setFillColor(colors.HexColor("#ffffff"))
    c.setStrokeColor(colors.HexColor("#dbe5f1"))
    c.roundRect(x, y, 145, 52, 10, fill=1, stroke=1)
    c.setFillColor(colors.HexColor(color))
    c.circle(x + 17, y + 27, 5, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica-Bold", 7)
    c.drawString(x + 31, y + 32, label.upper())
    c.setFillColor(colors.HexColor("#101828"))
    c.setFont("Helvetica-Bold", 13)
    c.drawString(x + 31, y + 14, value)


def _premium_bg(c: canvas.Canvas, width: float, height: float) -> None:
    c.setFillColor(colors.HexColor("#fbfdff"))
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#f2f7fb"))
    c.roundRect(24, 24, width - 48, height - 48, 22, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.roundRect(42, 42, width - 84, height - 84, 18, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#d8e4ee"))
    c.setLineWidth(0.8)
    c.roundRect(42, 42, width - 84, height - 84, 18, fill=0, stroke=1)
    c.setFillColor(colors.HexColor("#e8f7f3"))
    c.rect(42, height - 74, width - 84, 32, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#0f766e"))
    c.rect(42, height - 76, width - 84, 3, fill=1, stroke=0)


def _premium_header(c: canvas.Canvas, presentation: Presentation, width: float, height: float, page_number: int) -> None:
    logo = _logo_path()
    if logo:
        c.drawImage(ImageReader(str(logo)), 62, height - 70, width=128, height=44, preserveAspectRatio=True, mask="auto")
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.HexColor("#0f766e"))
    c.drawRightString(width - 62, height - 53, normalize_spanish(presentation.presentation_type).upper())
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#64748b"))
    c.drawRightString(width - 62, 32, f"Página {page_number:02d} | Operia Forensic Legal Report")


def _premium_chip(c: canvas.Canvas, x: float, y: float, text: str, tone: str = "info") -> float:
    palette = {
        "info": ("#eef6ff", "#bfdbfe", "#1d4ed8"),
        "valid": ("#ecfdf5", "#bbf7d0", "#047857"),
        "warn": ("#fffbeb", "#fde68a", "#a16207"),
        "risk": ("#fef2f2", "#fecaca", "#b91c1c"),
        "neutral": ("#f8fafc", "#cbd5e1", "#334155"),
    }
    fill, stroke, ink = palette.get(tone, palette["info"])
    text = normalize_spanish(text)
    w = stringWidth(text.upper(), "Helvetica-Bold", 7.5) + 20
    c.setFillColor(colors.HexColor(fill))
    c.setStrokeColor(colors.HexColor(stroke))
    c.roundRect(x, y - 14, w, 22, 7, fill=1, stroke=1)
    c.setFillColor(colors.HexColor(ink))
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x + 10, y - 7, text.upper())
    return w


def _premium_stat(c: canvas.Canvas, x: float, y: float, w: float, label: str, value: str, tone: str) -> None:
    colors_by_tone = {"valid": "#059669", "info": "#0e7490", "warn": "#b7791f", "risk": "#dc2626", "neutral": "#475569"}
    accent = colors_by_tone.get(tone, "#0e7490")
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.HexColor("#d8e4ee"))
    c.roundRect(x, y, w, 66, 13, fill=1, stroke=1)
    c.setFillColor(colors.HexColor(accent))
    c.roundRect(x, y, 6, 66, 3, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.HexColor("#64748b"))
    c.drawString(x + 18, y + 43, normalize_spanish(label).upper())
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor("#0f172a"))
    c.drawString(x + 18, y + 18, normalize_spanish(value))


def _premium_panel(c: canvas.Canvas, x: float, y: float, w: float, h: float, title: str, tone: str = "info") -> None:
    accent = {"info": "#0e7490", "valid": "#059669", "warn": "#b7791f", "risk": "#dc2626", "neutral": "#64748b"}.get(tone, "#0e7490")
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.HexColor("#d8e4ee"))
    c.roundRect(x, y, w, h, 14, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#f8fbff"))
    c.roundRect(x + 1, y + h - 34, w - 2, 33, 13, fill=1, stroke=0)
    c.setFillColor(colors.HexColor(accent))
    c.roundRect(x + 14, y + h - 24, 6, 12, 3, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x + 28, y + h - 22, normalize_spanish(title).upper())


def _slide_tone(title: str, text: str) -> str:
    haystack = normalize_spanish(f"{title} {text}").lower()
    if any(term in haystack for term in ["riesgo", "limitación", "pendiente", "advertencia"]):
        return "warn"
    if any(term in haystack for term in ["conclusión", "defendible", "validado"]):
        return "valid"
    if any(term in haystack for term in ["daño", "cuantificación", "monto"]):
        return "warn"
    if any(term in haystack for term in ["jurídico", "ley", "norma"]):
        return "info"
    return "neutral"


def _draw_bullets(c: canvas.Canvas, items: list[str], x: float, y: float, width: float, max_items: int, font_size: int = 11) -> float:
    for item in items[:max_items]:
        item = normalize_spanish(item.strip())
        if not item:
            continue
        c.setFillColor(colors.HexColor("#0f766e"))
        c.circle(x, y + 4, 3, fill=1, stroke=0)
        y = _draw_wrapped(c, item, x + 16, y, width - 18, "Helvetica", font_size, font_size + 5, colors.HexColor("#25324a"), max_lines=3) - 5
    return y


def _draw_premium_slide(c: canvas.Canvas, presentation: Presentation, slide, width: float, height: float, page_number: int) -> None:
    _premium_bg(c, width, height)
    _premium_header(c, presentation, width, height, page_number)
    tone = _slide_tone(slide.title, slide.text)

    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor("#0f766e"))
    c.drawString(68, height - 105, f"{page_number:02d}")
    y = _draw_wrapped(c, normalize_spanish(slide.title), 104, height - 98, width - 300, "Helvetica-Bold", 25, 30, colors.HexColor("#0f172a"), max_lines=2)
    _premium_chip(c, width - 202, height - 101, normalize_spanish(slide.confidentiality_level), "neutral" if slide.confidentiality_level == "interno" else ("risk" if slide.confidentiality_level == "confidencial" else "valid"))

    body = normalize_spanish(slide.text or "Contenido pendiente de completar.")
    raw_items = [line.strip("- • ") for line in body.splitlines() if line.strip()]
    if len(raw_items) <= 1:
        raw_items = [part.strip() for part in re.split(r"(?<=[.;])\s+", body) if part.strip()]

    main_x, main_y, main_w, main_h = 68, 114, width - 316, height - 244
    side_x, side_w = main_x + main_w + 22, 204
    _premium_panel(c, main_x, main_y, main_w, main_h, "Contenido ejecutivo", tone)
    _draw_bullets(c, raw_items, main_x + 30, main_y + main_h - 62, main_w - 58, 8, 12)

    _premium_panel(c, side_x, main_y + main_h - 122, side_w, 122, "Clave de lectura", "info")
    cues = []
    text_l = body.lower()
    if "hash" in text_l or "sha-256" in text_l:
        cues.append("Integridad verificable")
    if "fuente pendiente" in text_l or "pendiente" in text_l:
        cues.append("Requiere verificación")
    if "compatible" in text_l or "limitaciones" in text_l:
        cues.append("Lenguaje defendible")
    if "daño" in text_l or "monto" in text_l:
        cues.append("Impacto económico")
    if not cues:
        cues = ["Síntesis para exposición", "Revisión humana requerida"]
    _draw_bullets(c, cues, side_x + 24, main_y + main_h - 62, side_w - 44, 4, 9)

    _premium_panel(c, side_x, main_y + 78, side_w, 150, "Notas del expositor", "valid")
    note = normalize_spanish(slide.speaker_notes or "Agregar explicación oral: qué demuestra, qué no demuestra y cómo se conecta con la hipótesis.")
    _draw_wrapped(c, note, side_x + 20, main_y + 184, side_w - 40, "Helvetica", 9, 13, colors.HexColor("#14532d"), max_lines=7)

    _premium_panel(c, side_x, main_y, side_w, 58, "Control probatorio", "warn")
    control = "Evitar atribución personal sin evidencia complementaria."
    _draw_wrapped(c, control, side_x + 20, main_y + 26, side_w - 40, "Helvetica", 8.5, 11, colors.HexColor("#713f12"), max_lines=2)


def export_presentation_pdf(presentation: Presentation) -> Path:
    path = EXPORT_DIR / f"presentation-{presentation.id}.pdf"
    c = canvas.Canvas(str(path), pagesize=landscape(A4))
    width, height = landscape(A4)
    slides = sorted(presentation.slides, key=lambda item: item.slide_number)
    case = presentation.case
    logo = _logo_path()
    total_damage = sum(item.amount for item in case.damage_items) if case else 0

    _premium_bg(c, width, height)
    if logo:
        c.drawImage(ImageReader(str(logo)), 80, height - 160, width=305, height=112, preserveAspectRatio=True, mask="auto")
    _premium_chip(c, 82, height - 190, "Deck ejecutivo premium", "valid")
    _premium_chip(c, 232, height - 190, "Revisión humana requerida", "warn")
    _premium_chip(c, 410, height - 190, normalize_spanish(presentation.status), "info")

    title = normalize_spanish(case.title if case else presentation.title)
    y = _draw_wrapped(c, title, 82, height - 248, width - 164, "Helvetica-Bold", 34, 39, colors.HexColor("#0f172a"), max_lines=2)
    subtitle = normalize_spanish(f"Caso {case.case_code if case else '-'} | {presentation.presentation_type}")
    _draw_wrapped(c, subtitle, 84, y - 8, width - 168, "Helvetica", 13, 18, colors.HexColor("#475569"), max_lines=2)

    _premium_panel(c, 82, 172, width - 164, 122, "Teoría ejecutiva del caso", "info")
    intro = normalize_spanish(slides[0].text if slides else presentation.title)
    _draw_wrapped(c, intro, 108, 248, width - 216, "Helvetica", 12, 17, colors.HexColor("#25324a"), max_lines=5)

    gap = 16
    stat_w = (width - 164 - gap * 3) / 4
    _premium_stat(c, 82, 86, stat_w, "Evidencias", str(len(case.evidence) if case else 0), "info")
    _premium_stat(c, 82 + stat_w + gap, 86, stat_w, "Hallazgos", str(len(case.findings) if case else 0), "valid")
    _premium_stat(c, 82 + (stat_w + gap) * 2, 86, stat_w, "Daño estimado", f"{total_damage:,.0f} ARS", "warn")
    _premium_stat(c, 82 + (stat_w + gap) * 3, 86, stat_w, "Score deck", str(presentation.review_score or 0), "neutral")
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#64748b"))
    c.drawRightString(width - 82, 56, "Operia Forensic Legal Report | Presentación asistida por IA, no sustituye revisión profesional")
    c.showPage()

    content_slides = slides[1:] if len(slides) > 1 and "portada" in normalize_spanish(slides[0].title).lower() else slides
    for index, slide in enumerate(content_slides, start=1):
        _draw_premium_slide(c, presentation, slide, width, height, index)
        c.showPage()

    _premium_bg(c, width, height)
    _premium_header(c, presentation, width, height, len(content_slides) + 1)
    _premium_chip(c, 82, height - 112, "Cierre profesional", "valid")
    _draw_wrapped(c, "Conclusión para exposición oral", 82, height - 158, width - 164, "Helvetica-Bold", 30, 35, colors.HexColor("#0f172a"), max_lines=2)
    _premium_panel(c, 82, 150, width - 164, 220, "Conclusión defendible", "valid")
    closing = (
        "La presentación sintetiza los elementos centrales del informe, con alcance preliminar, "
        "limitaciones expresas y necesidad de revisión humana profesional. Las afirmaciones fuertes "
        "deben sostenerse con evidencia preservada, cadena de custodia y fuentes verificadas."
    )
    _draw_wrapped(c, closing, 112, 308, width - 224, "Helvetica", 15, 22, colors.HexColor("#25324a"), max_lines=7)
    _draw_wrapped(c, "Próximo paso sugerido: revisar recomendaciones del revisor automático y regenerar el PDF final.", 112, 205, width - 224, "Helvetica-Bold", 12, 18, colors.HexColor("#0f766e"), max_lines=2)
    c.showPage()

    c.save()
    presentation.exported_file = str(path)
    return path

