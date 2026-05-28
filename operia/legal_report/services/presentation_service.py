from operia.cases.models import Case
from operia.reports.models import Presentation, PresentationSlide, Report
from operia.legal_report.services.text_service import normalize_spanish


def make_slide(number: int, title: str, text: str, notes: str = "") -> PresentationSlide:
    return PresentationSlide(
        slide_number=number,
        title=title,
        text=text,
        speaker_notes=notes,
        confidentiality_level="interno",
    )


def build_presentation(case: Case, report: Report, presentation_type: str = "Presentaci?n ejecutiva breve") -> Presentation:
    total_damage = sum(item.amount for item in case.damage_items)
    top_findings = sorted(case.findings, key=lambda f: f.confidence_level == "alto", reverse=True)[:4]
    evidence = case.evidence[:4]
    legal = case.legal_mappings[:3]
    damages = case.damage_items[:5]

    presentation = Presentation(
        case=case,
        source_report_id=report.id,
        title=f"Presentaci?n ejecutiva - {case.title}",
        presentation_type=presentation_type,
        author=report.author,
        selected_fragments="Resumen ejecutivo; hallazgos principales; evidencia clave; cuantificación; conclusión defendible.",
    )

    slides = [
        make_slide(
            1,
            "Portada profesional",
            normalize_spanish(f"{case.title}\nCaso {case.case_code}\nTipo de incidente: {case.incident_type}\nResponsable: {case.responsible or 'pendiente'}"),
            "Abrir con alcance, rol profesional y advertencia de revisión humana.",
        ),
        make_slide(
            2,
            "Resumen ejecutivo",
            normalize_spanish(f"Se analiza un incidente de {case.incident_type}. Daño económico estimado: {total_damage:.2f} ARS. La conclusión se formula con alcance preliminar y limitaciones expresas."),
            "Explicar que la presentación resume el informe y no sustituye el documento completo.",
        ),
        make_slide(
            3,
            "Teoría del caso",
            normalize_spanish(case.description) or "Teoría del caso pendiente de completar con datos técnicos y evidencia preservada.",
            "Conectar dato técnico, evidencia, hallazgo, hipótesis y daño.",
        ),
        make_slide(
            4,
            "L?nea de tiempo visual",
            normalize_spanish("\n".join(f"{a.action_at}: {a.action_type} - {a.detailed_description}" for a in case.actions[:6])) or "Sin eventos registrados.",
            "Ordenar cronológicamente y señalar puntos de preservación.",
        ),
        make_slide(
            5,
            "Mapa de evidencia",
            normalize_spanish("\n".join(f"Evidencia #{e.id}: {e.description}. Hash: {e.sha256_hash or 'pendiente'}" for e in evidence)) or "Sin evidencia cargada.",
            "Aclarar que el hash verifica integridad, no autoría.",
        ),
        make_slide(
            6,
            "Hallazgos principales",
            normalize_spanish("\n".join(f"{f.title}: {f.technical_finding}. Confianza: {f.confidence_level}" for f in top_findings)) or "Sin hallazgos validados.",
            "Distinguir hechos observados de inferencias.",
        ),
        make_slide(
            7,
            "Hip?tesis investigativa principal",
            normalize_spanish("\n".join(f"{h.title}: {h.description}. Soporte: {h.support_degree}" for h in case.hypotheses[:3])) or "Sin hipótesis cargadas.",
            "Presentar hipótesis como provisional si falta prueba complementaria.",
        ),
        make_slide(
            8,
            "Encuadre jurídico preliminar",
            normalize_spanish("\n".join(f"{m.legal_area}: {m.norm_reference}. {m.verification_status}" for m in legal)) or "Fuente pendiente de verificación.",
            "Recordar que el encuadre requiere revisión de abogado matriculado.",
        ),
        make_slide(
            9,
            "Cuantificación económica del daño",
            normalize_spanish("\n".join(f"{d.concept}: {d.amount:.2f} {d.currency}. Fórmula: {d.formula_used or 'pendiente'}" for d in damages)) or "Sin daños cargados.",
            "Separar daño patrimonial directo, lucro cesante y otros conceptos.",
        ),
        make_slide(
            10,
            "Conclusión jurídicamente defendible",
            "La evidencia resulta compatible con los hallazgos indicados, con el alcance y limitaciones del informe. No resulta posible afirmar autoría personal sin medidas complementarias.",
            "Cerrar con limites, proximos pasos y valor probatorio.",
        ),
        make_slide(
            11,
            "Preguntas esperables del jurado",
            "¿Qué demuestra el hash?\n¿Qué no puede concluirse todavía?\n¿Cómo se conecta la evidencia con el daño?\n¿Qué fuentes legales están verificadas?",
            "Responder en lenguaje claro, breve y no categórico.",
        ),
    ]
    for slide in slides:
        slide.title = normalize_spanish(slide.title)
        slide.text = normalize_spanish(slide.text)
        slide.speaker_notes = normalize_spanish(slide.speaker_notes)
        slide.presentation = presentation
    presentation.slides = slides
    return presentation

