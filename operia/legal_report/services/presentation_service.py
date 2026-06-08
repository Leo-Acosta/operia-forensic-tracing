from sqlalchemy.orm import object_session

from operia.cases.models import Case
from operia.legal_report.services.report_service import isolated_case_snapshot
from operia.legal_report.services.text_service import normalize_spanish
from operia.mind.models import MindGraphEdge, MindGraphNode
from operia.reports.models import Presentation, PresentationSlide, Report


def _line(text: str, fallback: str = "No informado") -> str:
    return normalize_spanish((text or "").strip() or fallback)


def _limited_lines(items: list[str], fallback: str, limit: int = 6) -> str:
    clean = [normalize_spanish(item).strip() for item in items if normalize_spanish(item).strip()]
    if not clean:
        return fallback
    return "\n".join(f"- {item}" for item in clean[:limit])


def make_slide(number: int, title: str, text: str, notes: str = "") -> PresentationSlide:
    return PresentationSlide(
        slide_number=number,
        title=normalize_spanish(title),
        text=normalize_spanish(text),
        speaker_notes=normalize_spanish(notes),
        confidentiality_level="interno",
    )


def _case_timeline(case) -> str:
    rows = []
    for action in sorted(case.actions, key=lambda item: item.action_at)[:10]:
        rows.append(f"{action.action_at}: {action.action_type} - {action.detailed_description}")
    if not rows and getattr(case, "created_at", None):
        rows.append(f"{case.created_at}: apertura del caso {case.case_code}.")
    return _limited_lines(rows, "Sin línea de tiempo suficiente para exposición oral.", limit=10)


def _evidence_key_points(case) -> str:
    rows = []
    for evidence in case.evidence[:8]:
        hash_text = f"SHA-256 {evidence.sha256_hash[:16]}..." if evidence.sha256_hash else "hash pendiente"
        rows.append(f"Evidencia #{evidence.id}: {evidence.description}. {hash_text}.")
    return _limited_lines(rows, "Sin evidencia clave cargada.", limit=8)


def _legal_key_points(case) -> str:
    approved = [item for item in case.legal_mappings if getattr(item, "decision_status", "") != "descartado"]
    rows = [
        f"{item.norm_reference}: {item.analysis or item.verification_status or 'criterio legal registrado'}"
        for item in approved[:8]
    ]
    return _limited_lines(rows, "Sin normas aprobadas desde biblioteca legal registrada.", limit=8)


def _findings_key_points(case) -> str:
    rows = [
        f"{item.title}. Confianza {item.confidence_level}. Límite: {item.weaknesses_or_limitations or 'requiere corroboración externa'}."
        for item in case.findings[:8]
    ]
    return _limited_lines(rows, "Sin hallazgos técnicos validados.", limit=8)


def _case_theory(case) -> str:
    if case.hypotheses:
        return _limited_lines(
            [
                f"{item.title}: {item.description}. Soporte {item.support_degree}. Conclusión provisional: {item.provisional_conclusion or 'pendiente'}."
                for item in case.hypotheses[:3]
            ],
            "Sin hipótesis cargadas.",
        )
    evidence_count = len(case.evidence)
    finding_count = len(case.findings)
    return normalize_spanish(
        f"Teoría preliminar: el hecho investigado se presenta como {case.incident_type}. "
        f"La hipótesis debe sostenerse con {evidence_count} evidencia(s), {finding_count} hallazgo(s), "
        "cadena de custodia, normas aplicables y límites de atribución."
    )


def _weak_points(case) -> str:
    weak = []
    if not case.evidence:
        weak.append("Falta evidencia digital preservada.")
    if any(not item.sha256_hash for item in case.evidence):
        weak.append("Hay evidencia sin SHA-256 completo.")
    if not case.actions:
        weak.append("Falta cadena de custodia documentada.")
    if not case.findings:
        weak.append("Faltan hallazgos técnicos estructurados.")
    if not case.legal_mappings:
        weak.append("Falta mapeo legal aprobado.")
    if not case.damage_items:
        weak.append("Daño económico sin rubros cuantificados.")
    if not weak:
        weak.append("Evitar atribución personal categórica si no existe corroboración externa suficiente.")
    return _limited_lines(weak, "Sin puntos débiles críticos detectados.", limit=8)


def _questions_and_answers(case) -> str:
    total_damage = sum(item.amount for item in case.damage_items)
    answers = [
        ("¿Qué demuestra el hash?", "Demuestra integridad del archivo preservado, no autoría personal por sí solo."),
        ("¿Por qué la evidencia es relevante?", "Porque conecta el hecho denunciado con objetos digitales, fechas, fuentes, custodia o hallazgos verificables."),
        ("¿Qué norma se aplica?", "Solo las normas aprobadas desde biblioteca legal registrada y vinculadas con la evidencia del caso."),
        ("¿Se puede atribuir autoría?", "Solo si existen elementos técnicos y externos suficientes; de lo contrario se informa imposibilidad de atribución concluyente."),
        ("¿Cómo se cuantificó el daño?", f"Con rubros cargados y soporte documental. Total preliminar: {total_damage:.2f} ARS."),
    ]
    return "\n".join(f"- {question} {answer}" for question, answer in answers)


def _graph_summary(case: Case) -> str:
    db = object_session(case)
    if not db or not getattr(case, "id", None):
        return "Sin grafo relacional cargado."
    nodes = db.query(MindGraphNode).filter(MindGraphNode.case_id == case.id).limit(60).all()
    edges = db.query(MindGraphEdge).filter(MindGraphEdge.case_id == case.id).limit(60).all()
    if not nodes and not edges:
        return "Sin grafo relacional cargado."
    labels = {node.node_key: node.label for node in nodes}
    rows = [f"Nodos: {len(nodes)}. Relaciones: {len(edges)}."]
    for edge in edges[:8]:
        source = labels.get(edge.source_node_key, edge.source_node_key)
        target = labels.get(edge.target_node_key, edge.target_node_key)
        rows.append(f"{source} --{edge.relation_type}--> {target}.")
    return _limited_lines(rows, "Sin grafo relacional cargado.", limit=9)


def _oral_three_minutes(case) -> str:
    return normalize_spanish(
        f"En tres minutos: este caso trata sobre {case.incident_type}. "
        f"El objeto es explicar qué ocurrió según la evidencia preservada, qué hallazgos se pudieron sostener, "
        f"qué normas argentinas resultan aplicables y qué límites impiden afirmar más de lo probado. "
        f"El caso cuenta con {len(case.evidence)} evidencia(s), {len(case.actions)} acción(es) de custodia, "
        f"{len(case.findings)} hallazgo(s), {len(case.legal_mappings)} mapeo(s) legal(es) y "
        f"daño económico preliminar por {sum(item.amount for item in case.damage_items):.2f} ARS."
    )


def _oral_ten_minutes(case) -> str:
    return normalize_spanish(
        "En diez minutos, la exposición debe seguir este orden: "
        "1) identificación del caso y alcance; "
        "2) relato cronológico del incidente; "
        "3) evidencia clave y preservación; "
        "4) hallazgos técnicos y límites; "
        "5) normas argentinas aprobadas y relación con evidencia; "
        "6) daño económico; "
        "7) teoría del caso; "
        "8) preguntas previsibles; "
        "9) conclusión prudente y recomendaciones procesales."
    )


def build_presentation(case: Case, report: Report, presentation_type: str = "Exposición ejecutiva del caso") -> Presentation:
    scoped_case = isolated_case_snapshot(case)
    total_damage = sum(item.amount for item in scoped_case.damage_items)
    title = f"Exposición del caso - {scoped_case.title}"

    presentation = Presentation(
        case=case,
        source_report_id=report.id,
        title=normalize_spanish(title),
        presentation_type=normalize_spanish(presentation_type),
        author=report.author,
        selected_fragments=normalize_spanish(
            "Resumen oral; línea de tiempo; teoría del caso; evidencias clave; normas aplicadas; "
            "puntos débiles; preguntas posibles; versión de 3 minutos; versión de 10 minutos."
        ),
    )

    slides = [
        make_slide(
            1,
            "Apertura y alcance",
            (
                f"{scoped_case.title}\n"
                f"Caso {scoped_case.case_code}\n"
                f"Tipo de incidente: {scoped_case.incident_type}\n"
                f"Estado: {scoped_case.status}\n"
                f"Jurisdicción: {scoped_case.jurisdiction}"
            ),
            "Abrir con el objeto de la exposición, alcance, rol del analista y límites de atribución.",
        ),
        make_slide(
            2,
            "Resumen oral",
            _oral_three_minutes(scoped_case),
            "Usar esta versión como apertura breve ante jurado, audiencia o comité técnico.",
        ),
        make_slide(
            3,
            "Línea de tiempo",
            _case_timeline(scoped_case),
            "Mostrar secuencia temporal: recepción, preservación, análisis, hallazgo y revisión.",
        ),
        make_slide(
            4,
            "Teoría del caso",
            _case_theory(scoped_case),
            "Conectar hecho, evidencia, hallazgo, hipótesis, norma y daño. Evitar saltos lógicos.",
        ),
        make_slide(
            5,
            "Evidencias clave",
            _evidence_key_points(scoped_case),
            "Explicar qué encontró el analista, cómo se preservó y qué demuestra cada evidencia.",
        ),
        make_slide(
            6,
            "Hallazgos e hipótesis",
            _findings_key_points(scoped_case),
            "Distinguir observación técnica, inferencia e hipótesis investigativa.",
        ),
        make_slide(
            7,
            "Normativa argentina aplicada",
            _legal_key_points(scoped_case),
            "Citar solo normas registradas y aprobadas; explicar elemento típico y evidencia de soporte.",
        ),
        make_slide(
            8,
            "Daño económico y significancia",
            (
                f"Daño estimado: {total_damage:.2f} ARS.\n"
                + _limited_lines(
                    [
                        f"{item.concept}: {item.amount:.2f} {item.currency}. Fuente: {item.value_source or 'pendiente'}."
                        for item in scoped_case.damage_items[:6]
                    ],
                    "Sin rubros económicos cargados.",
                )
            ),
            "Separar pérdida directa, recuperación, indisponibilidad, reposición, pericia y soporte documental.",
        ),
        make_slide(
            9,
            "Grafo relevante del caso",
            _graph_summary(case),
            "Usar el grafo para explicar vínculos entre evidencia, hallazgos, normas, informes y notas del mismo caso.",
        ),
        make_slide(
            10,
            "Puntos débiles y límites",
            _weak_points(scoped_case),
            "Anticipar objeciones: integridad, custodia, atribución, prueba faltante, fuente legal y daño.",
        ),
        make_slide(
            11,
            "Preguntas posibles y respuestas sugeridas",
            _questions_and_answers(scoped_case),
            "Responder de forma breve, prudente y basada en evidencia.",
        ),
        make_slide(
            12,
            "Versión de 10 minutos",
            _oral_ten_minutes(scoped_case),
            "Usar como guion extendido cuando el jurado pida explicación completa del caso.",
        ),
        make_slide(
            13,
            "Conclusión de exposición",
            (
                "La conclusión debe sostenerse en evidencia preservada, hallazgos verificables, normativa registrada "
                "y límites probatorios explícitos. La atribución penal individual exige corroboración suficiente y valoración judicial."
            ),
            "Cerrar con recomendaciones procesales y medidas pendientes.",
        ),
    ]
    for slide in slides:
        slide.presentation = presentation
    presentation.slides = slides
    return presentation
