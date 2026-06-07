from operia.cases.models import Case
from operia.legal_report.services.text_service import normalize_spanish
from operia.reports.models import Presentation, PresentationSlide, Report


def make_slide(number: int, title: str, text: str, notes: str = "") -> PresentationSlide:
    return PresentationSlide(
        slide_number=number,
        title=normalize_spanish(title),
        text=normalize_spanish(text),
        speaker_notes=normalize_spanish(notes),
        confidentiality_level="interno",
    )


def build_presentation(case: Case, report: Report, presentation_type: str = "Exposición ejecutiva del caso") -> Presentation:
    total_damage = sum(item.amount for item in case.damage_items)
    top_findings = sorted(case.findings, key=lambda f: f.confidence_level == "alto", reverse=True)[:4]
    evidence = case.evidence[:5]
    legal = case.legal_mappings[:5]
    damages = case.damage_items[:6]

    presentation = Presentation(
        case=case,
        source_report_id=report.id,
        title=f"Exposición del caso - {case.title}",
        presentation_type=presentation_type,
        author=report.author,
        selected_fragments=(
            "Resumen ejecutivo; teoría del caso; línea de tiempo; evidencia clave; "
            "cuantificación; encuadre legal; conclusión defendible."
        ),
    )

    slides = [
        make_slide(
            1,
            "Apertura de la exposición",
            f"{case.title}\nCaso {case.case_code}\nTipo de incidente: {case.incident_type}\nEstado: {case.status}",
            "Abrir con el objeto de la exposición, el alcance de la investigación y el rol del analista.",
        ),
        make_slide(
            2,
            "Resumen ejecutivo",
            (
                f"Se analiza un incidente de {case.incident_type}. "
                f"Daño económico estimado: {total_damage:.2f} ARS. "
                "La conclusión se formula según la evidencia preservada y las limitaciones registradas."
            ),
            "Explicar que la exposición resume el informe y que cada afirmación debe apoyarse en evidencia o fuente legal registrada.",
        ),
        make_slide(
            3,
            "Teoría del caso",
            case.description or "Teoría del caso pendiente de completar con datos técnicos y evidencia preservada.",
            "Conectar hecho investigado, evidencia, hallazgo, hipótesis, encuadre legal y daño.",
        ),
        make_slide(
            4,
            "Línea de tiempo",
            "\n".join(f"{a.action_at}: {a.action_type} - {a.detailed_description}" for a in case.actions[:8])
            or "Sin eventos registrados.",
            "Ordenar cronológicamente y señalar puntos de preservación, análisis y revisión.",
        ),
        make_slide(
            5,
            "Mapa de evidencia",
            "\n".join(f"Evidencia #{e.id}: {e.description}. Hash: {e.sha256_hash or 'pendiente'}" for e in evidence)
            or "Sin evidencia cargada.",
            "Aclarar que el hash verifica integridad, pero no demuestra por sí solo autoría.",
        ),
        make_slide(
            6,
            "Hallazgos principales",
            "\n".join(f"{f.title}: {f.technical_finding}. Confianza: {f.confidence_level}" for f in top_findings)
            or "Sin hallazgos validados.",
            "Distinguir hechos observados de inferencias.",
        ),
        make_slide(
            7,
            "Hipótesis investigativa principal",
            "\n".join(f"{h.title}: {h.description}. Soporte: {h.support_degree}" for h in case.hypotheses[:3])
            or "Sin hipótesis cargadas.",
            "Presentar la hipótesis como provisional si falta prueba complementaria.",
        ),
        make_slide(
            8,
            "Encuadre jurídico preliminar",
            "\n".join(f"{m.legal_area}: {m.norm_reference}. {m.verification_status}" for m in legal)
            or "Fuente pendiente de verificación.",
            "Explicar norma, elemento típico y evidencia que sostiene o limita la aplicación.",
        ),
        make_slide(
            9,
            "Cuantificación económica del daño",
            "\n".join(f"{d.concept}: {d.amount:.2f} {d.currency}. Fórmula: {d.formula_used or 'pendiente'}" for d in damages)
            or "Sin daños cargados.",
            "Separar daño patrimonial directo, costos de respuesta, interrupción operativa, lucro cesante y soporte documental.",
        ),
        make_slide(
            10,
            "Conclusión jurídicamente defendible",
            (
                "La evidencia resulta compatible con los hallazgos indicados, con el alcance y limitaciones del informe. "
                "La atribución personal requiere corroboración externa suficiente y valoración jurídica independiente."
            ),
            "Cerrar con límites, próximos pasos y valor probatorio.",
        ),
        make_slide(
            11,
            "Preguntas esperables del jurado",
            (
                "¿Qué demuestra el hash?\n"
                "¿Qué no puede concluirse todavía?\n"
                "¿Cómo se conecta la evidencia con el daño?\n"
                "¿Qué fuentes legales están verificadas?"
            ),
            "Responder en lenguaje claro, breve y no categórico.",
        ),
    ]
    for slide in slides:
        slide.presentation = presentation
    presentation.slides = slides
    return presentation
