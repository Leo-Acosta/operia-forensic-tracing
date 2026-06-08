import json
from hashlib import sha256
from types import SimpleNamespace
from typing import Any

from sqlalchemy.orm import object_session

from operia.cases.models import Case
from operia.mind.models import MindGraphEdge, MindGraphNode, MindNote
from operia.reports.models import Report, ReportSection, ReportVersion
from operia.legal_report.services.text_service import normalize_spanish
from operia.shared.time import utcnow

NO_ATTRIBUTION_TEXT = (
    "Del análisis efectuado no surgen elementos técnicos suficientes que permitan atribuir el ataque informático "
    "a una persona física, grupo organizado, entidad u organización determinada."
)

ATTRIBUTION_METHOD_NOTE = (
    "La atribución técnica de un ciberataque no debe confundirse con la atribución penal de autoría: la primera "
    "identifica patrones, infraestructura, indicadores y probabilidades; la segunda exige prueba jurídicamente "
    "valorable, individualización subjetiva y control contradictorio en el proceso penal."
)

REPORT_SECTIONS = [
    "Carátula",
    "Datos del caso",
    "Personas y entidades vinculadas",
    "Objeto del informe",
    "Alcance del análisis",
    "Limitaciones",
    "Metodología utilizada",
    "Resumen ejecutivo",
    "Descripción del incidente",
    "Evidencia recibida",
    "Registro de cadena de custodia",
    "Línea de tiempo de eventos",
    "Análisis técnico-forense",
    "Matriz dato técnico -> evidencia -> hallazgo",
    "Autenticacion de medios y analisis deepfake",
    "Analisis forense de blockchain",
    "Analisis forense de dispositivos IoT",
    "Hallazgos principales",
    "Hipótesis investigativas",
    "Evaluación de hipótesis alternativas",
    "Conclusiones técnicas",
    "Encuadre jurídico argentino",
    "Matriz legal-probatoria aplicada",
    "Sem?foro de suficiencia legal",
    "Responsabilidad penal preliminar",
    "Responsabilidad civil preliminar",
    "Protección de datos personales",
    "Defensa del consumidor",
    "Cuantificación económica del daño",
    "Conclusión jurídicamente defendible",
    "Recomendaciones",
    "Recomendaciones procesales autom?ticas",
    "Anexos",
    "Glosario técnico",
    "Preguntas y respuestas para testimonio experto",
]


def isolated_case_snapshot(case: Case) -> Any:
    """Return a read-only case-shaped object with only records that belong to this case."""
    case_id = getattr(case, "id", None)

    def belongs(item: Any) -> bool:
        return getattr(item, "case_id", case_id) == case_id

    evidence = [item for item in getattr(case, "evidence", []) or [] if belongs(item)]
    evidence_ids = {item.id for item in evidence}
    technical_data = [item for item in getattr(case, "technical_data", []) or [] if belongs(item)]
    actions = [
        item
        for item in getattr(case, "actions", []) or []
        if belongs(item) and (getattr(item, "evidence_id", None) is None or getattr(item, "evidence_id", None) in evidence_ids)
    ]
    findings = [
        item
        for item in getattr(case, "findings", []) or []
        if belongs(item) and (getattr(item, "evidence_id", None) is None or getattr(item, "evidence_id", None) in evidence_ids)
    ]
    hypotheses = [item for item in getattr(case, "hypotheses", []) or [] if belongs(item)]
    legal_mappings = [item for item in getattr(case, "legal_mappings", []) or [] if belongs(item)]
    damage_items = [item for item in getattr(case, "damage_items", []) or [] if belongs(item)]
    participants = [item for item in getattr(case, "participants", []) or [] if belongs(item)]
    reports = [item for item in getattr(case, "reports", []) or [] if belongs(item)]
    presentations = [item for item in getattr(case, "presentations", []) or [] if belongs(item)]
    rubric_evaluations = [item for item in getattr(case, "rubric_evaluations", []) or [] if belongs(item)]

    def linked(items: list[Any]) -> list[Any]:
        return [
            item
            for item in items
            if belongs(item) and (getattr(item, "evidence_id", None) is None or getattr(item, "evidence_id", None) in evidence_ids)
        ]

    return SimpleNamespace(
        id=case.id,
        organization_id=getattr(case, "organization_id", None),
        case_code=case.case_code,
        title=case.title,
        description=case.description,
        responsible=case.responsible,
        client_or_victim=case.client_or_victim,
        incident_type=case.incident_type,
        status=case.status,
        jurisdiction=case.jurisdiction,
        general_observations=case.general_observations,
        created_at=getattr(case, "created_at", None),
        updated_at=getattr(case, "updated_at", None),
        technical_data=technical_data,
        evidence=evidence,
        actions=actions,
        findings=findings,
        hypotheses=hypotheses,
        legal_mappings=legal_mappings,
        participants=participants,
        damage_items=damage_items,
        reports=reports,
        presentations=presentations,
        rubric_evaluations=rubric_evaluations,
        deepfake_analyses=linked(getattr(case, "deepfake_analyses", []) or []),
        blockchain_transactions=linked(getattr(case, "blockchain_transactions", []) or []),
        iot_devices=linked(getattr(case, "iot_devices", []) or []),
    )


def _mapping_links_for_case(mapping: Any, case: Any | None = None) -> list[Any]:
    case_id = getattr(case, "id", getattr(mapping, "case_id", None))
    return [
        link
        for link in getattr(mapping, "evidence_links", []) or []
        if getattr(link, "case_id", case_id) == case_id
        and getattr(link, "legal_mapping_id", getattr(mapping, "id", None)) == getattr(mapping, "id", None)
        and getattr(getattr(link, "evidence", None), "case_id", case_id) == case_id
    ]


def _mind_case_context_markdown(case: Case) -> str:
    """Public, case-scoped memory/graph summary for reports.

    This intentionally avoids exposing prompts, agents, model names or internal
    automation details. It only renders case notes and graph relations already
    stored as forensic memory for the same case_id.
    """
    db = object_session(case)
    case_id = getattr(case, "id", None)
    if not db or not case_id:
        return ""

    nodes = (
        db.query(MindGraphNode)
        .filter(MindGraphNode.case_id == case_id)
        .order_by(MindGraphNode.node_type.asc(), MindGraphNode.label.asc())
        .limit(80)
        .all()
    )
    edges = (
        db.query(MindGraphEdge)
        .filter(MindGraphEdge.case_id == case_id)
        .order_by(MindGraphEdge.relation_type.asc(), MindGraphEdge.created_at.asc())
        .limit(80)
        .all()
    )
    notes = (
        db.query(MindNote)
        .filter(MindNote.case_id == case_id)
        .order_by(MindNote.updated_at.desc())
        .limit(12)
        .all()
    )
    if not nodes and not edges and not notes:
        return ""

    labels = {node.node_key: node.label for node in nodes}
    node_counts: dict[str, int] = {}
    for node in nodes:
        node_counts[node.node_type] = node_counts.get(node.node_type, 0) + 1

    lines = [
        "## Memoria forense y grafo relacional del caso",
        "",
        "La siguiente síntesis se limita a notas y relaciones registradas para este caso. No incorpora datos de otros expedientes.",
        "",
    ]
    if node_counts:
        lines.append("### Inventario relacional")
        lines.append("")
        for node_type, count in sorted(node_counts.items()):
            lines.append(f"- {node_type}: {count}.")
        lines.append("")
    if edges:
        lines.append("### Relaciones relevantes")
        lines.append("")
        for edge in edges[:20]:
            source = labels.get(edge.source_node_key, edge.source_node_key)
            target = labels.get(edge.target_node_key, edge.target_node_key)
            label = f" ({edge.label})" if edge.label else ""
            lines.append(f"- {source} --{edge.relation_type}--> {target}{label}. Confianza: {edge.confidence}.")
        lines.append("")
    if notes:
        lines.append("### Notas persistentes del caso")
        lines.append("")
        for note in notes:
            summary = note.summary or note.content[:180] or "Sin resumen cargado."
            lines.append(f"- {note.note_type}: {note.title}. {summary}")
        lines.append("")
    return normalize_spanish("\n".join(lines)).strip()


def build_integral_markdown(case: Case, legal_recommendations: list[Any] | None = None) -> str:
    mind_context_lines = _mind_case_context_markdown(case)
    case = isolated_case_snapshot(case)
    total_damage = sum(item.amount for item in case.damage_items)
    case_narrative = _case_narrative_markdown(case)
    evidence_overview = _evidence_overview_markdown(case)
    investigative_techniques = _investigative_techniques_markdown(case)
    evidence_identification = _evidence_identification_markdown(case)
    investigated_documentation = _investigated_documentation_markdown(case)
    analysis_evidence = _analysis_evidence_markdown(case)
    damage_methodology = _damage_methodology_markdown(case, total_damage)
    participant_lines = "\n".join(
        (
            f"- {p.display_name} ({p.person_type}; rol: {p.participant_type}). "
            f"Relacion: {p.relationship_to_case or p.role_description or 'pendiente'}. "
            f"Sensibilidad: {p.sensitivity_level}."
        )
        for p in case.participants
    ) or "- Sin personas o entidades vinculadas cargadas."
    evidence_lines = "\n".join(
        f"- Evidencia #{e.id}: {e.description}. SHA-256: `{e.sha256_hash or 'pendiente'}`. Integridad: {e.integrity_status}."
        for e in case.evidence
    ) or "- Sin evidencia cargada."
    custody_lines = "\n".join(
        f"- {a.action_at}: {a.action_type} - {a.detailed_description}."
        for a in sorted(case.actions, key=lambda action: action.action_at)
    ) or "- Sin acciones registradas."
    finding_lines = "\n".join(
        f"- {f.title}: {f.technical_finding}. Confianza: {f.confidence_level}. Limitaciones: {f.weaknesses_or_limitations or 'no indicadas'}."
        for f in case.findings
    ) or "- Sin hallazgos cargados."
    hypothesis_lines = "\n".join(
        f"- {h.title}: {h.description}. Soporte: {h.support_degree}. Conclusión provisional: {h.provisional_conclusion or 'pendiente'}."
        for h in case.hypotheses
    ) or "- Sin hipótesis cargadas."
    approved_mappings = [
        m for m in case.legal_mappings if getattr(m, "decision_status", "sugerido") != "descartado"
    ]
    legal_lines = "\n".join(
        f"- {m.legal_area}: {m.norm_reference}. {m.analysis}. Estado: {m.verification_status}."
        + _legal_mapping_evidence_suffix(m)
        for m in approved_mappings
    ) or "- Sin encuadre legal cargado. Fuente pendiente de verificación."
    if not case.hypotheses:
        hypothesis_lines = _default_hypotheses_markdown(case)
    if not approved_mappings:
        legal_lines = _legal_recommendation_markdown(legal_recommendations or [])
    damage_lines = "\n".join(
        f"| {d.concept} | {d.amount:.2f} {d.currency} | {d.formula_used or 'pendiente'} | {d.value_source or 'pendiente'} | {d.certainty_level} |"
        for d in case.damage_items
    ) or "| Sin conceptos | 0 | pendiente | pendiente | bajo |"

    matrix_lines = "\n".join(
        f"| Dato #{f.technical_data_id or '-'} | Evidencia #{f.evidence_id or '-'} | {f.title} | {f.confidence_level} | {f.preliminary_legal_relevance or 'pendiente'} |"
        for f in case.findings
    ) or "| - | - | Pendiente | bajo | pendiente |"
    legal_probatory = legal_probatory_assessment(case)
    legal_probatory_lines = _legal_probatory_matrix_markdown(legal_probatory)
    legal_sufficiency_lines = _legal_sufficiency_markdown(legal_probatory)
    penal_legal_theory = _penal_legal_theory_markdown(case, legal_probatory)
    procedural_recommendations = _procedural_recommendations_markdown(case, legal_probatory)
    exportability = report_exportability_assessment(case, legal_probatory)
    executive_summary = build_smart_executive_summary(case, legal_probatory, exportability)
    exportability_lines = exportability_markdown(exportability)
    media_authentication_lines = _media_authentication_markdown(case)
    blockchain_forensics_lines = _blockchain_forensics_markdown(case)
    iot_forensics_lines = _iot_forensics_markdown(case)
    challenge_2026_lines = _challenge_2026_markdown(
        case,
        legal_probatory,
        media_authentication_lines,
        blockchain_forensics_lines,
        iot_forensics_lines,
    )
    technical_overview_lines = _technical_forensic_overview_markdown(
        media_authentication_lines,
        blockchain_forensics_lines,
        iot_forensics_lines,
    )
    rubric_lines = ""
    if getattr(case, "rubric_evaluations", None):
        from operia.rubrics.service import rubric_markdown

        latest_rubric = sorted(case.rubric_evaluations, key=lambda item: (getattr(item, "route_order", 0) or 999999, item.created_at), reverse=True)[0]
        rubric_lines = "\n\n" + rubric_markdown(latest_rubric)

    responsible_text = case.responsible or NO_ATTRIBUTION_TEXT
    client_or_victim = case.client_or_victim or ""
    description_text = case.description or ""

    markdown = f"""# Operia Forensic Legal Report

## Carátula

**Caso:** {case.title}  
**ID:** {case.case_code}  
**Responsable:** {responsible_text}
**Cliente/Víctima:** {client_or_victim}
**Jurisdicción:** {case.jurisdiction}

## Datos del caso

- Tipo de incidente: {case.incident_type}
- Estado: {case.status}
- Nivel de exportabilidad: {exportability['level']}
- Descripción: {description_text}
- Observaciones: {case.general_observations or 'sin observaciones'}

## Personas y entidades vinculadas

{participant_lines}

## Objeto del informe

Ordenar datos técnicos, evidencia preservada, hallazgos, hipótesis, encuadre legal argentino y cuantificación económica del daño para una conclusión defendible.

## Alcance del análisis

El alcance se limita a los datos, archivos, evidencias, fuentes legales y cálculos cargados en la plataforma.

## Limitaciones

La herramienta asiste, pero no reemplaza revisión profesional humana. No se afirma autoría personal sin medidas complementarias.

## Metodología utilizada

Se preservaron datos técnicos, se registraron acciones de cadena de custodia, se calcularon hashes cuando hubo archivos y se construyó la matriz dato técnico -> evidencia -> hallazgo -> hipótesis -> conclusión.

## Tecnicas usadas, herramientas forenses y metodologia

{investigative_techniques}

## Resumen ejecutivo

{executive_summary}

### Narrativa ejecutiva del caso

{case_narrative}

### Nivel de exportabilidad del informe

{exportability_lines}

{challenge_2026_lines}

## Descripción del incidente

{description_text}

## Evidencia recibida

{evidence_lines}

## Identificacion, categorizacion y preservacion de evidencia

{evidence_identification}

### Punteo pericial de evidencias informáticas

{evidence_overview}

## Documentacion investigada

{investigated_documentation}

## Evidencia de analisis y trazabilidad del hallazgo

{analysis_evidence}

{mind_context_lines}

## Registro de cadena de custodia

{custody_lines}

## Línea de tiempo de eventos

{custody_lines}

## Análisis técnico-forense

{technical_overview_lines}

{f'## Autenticacion de medios y analisis deepfake\n\n{media_authentication_lines}' if media_authentication_lines else ''}

{f'## Analisis forense de blockchain\n\n{blockchain_forensics_lines}' if blockchain_forensics_lines else ''}

{f'## Analisis forense de dispositivos IoT\n\n{iot_forensics_lines}' if iot_forensics_lines else ''}

## Matriz dato técnico -> evidencia -> hallazgo

| Dato técnico | Evidencia | Hallazgo | Confianza | Relevancia jurídica |
| --- | --- | --- | --- | --- |
{matrix_lines}

## Hallazgos principales

{finding_lines}

## Hipótesis investigativas

{hypothesis_lines}

## Evaluación de hipótesis alternativas

Las hipótesis alternativas deben conservarse abiertas cuando existan hechos faltantes o riesgos de error.

## Conclusiones técnicas

Con el alcance y limitaciones indicadas, los hallazgos permiten sostener preliminarmente compatibilidades técnicas, no atribuciones personales definitivas.

## Encuadre jurídico argentino

{legal_lines}

## Fundamentacion penal y legal aplicada

{penal_legal_theory}

## Matriz legal-probatoria aplicada

| Norma | Elemento legal | Evidencia | Estado | Fuerza | Riesgo | Medida recomendada |
| --- | --- | --- | --- | --- | --- | --- |
{legal_probatory_lines}

## Semáforo de suficiencia legal

{legal_sufficiency_lines}

### Método de aplicación normativa

{_normative_application_method(legal_probatory)}

## Responsabilidad penal preliminar

Debe ser revisada por abogado matriculado. No se atribuye autoría penal sin evidencia suficiente.

## Responsabilidad civil preliminar

Debe ser evaluada según nexo causal, daño acreditado y sujetos intervinientes.

## Protección de datos personales

Debe revisarse posible aplicación de Ley 25.326 cuando existan datos personales comprometidos.

## Defensa del consumidor

Debe evaluarse si existe relación de consumo, plataformas, bancos, fintech, exchanges o proveedores digitales involucrados.

## Cuantificación económica del daño

| Concepto | Monto | Formula | Fuente | Certeza |
| --- | ---: | --- | --- | --- |
{damage_lines}

**Daño total estimado:** {total_damage:.2f} ARS.

{damage_methodology}

## Conclusión jurídicamente defendible

La evidencia resulta compatible con los hallazgos indicados, con las limitaciones explicitadas. La conclusión requiere validación humana técnica y jurídica.

### Sintesis aplicada al caso

{_incident_conclusion_frame(case, legal_probatory)}

{build_matrix_based_conclusion(case)}

{_incident_specific_conclusion(case)}

## Recomendaciones

- Completar fuentes pendientes de verificación.
- Validar hashes, bitácora y anexos.
- Reformular afirmaciones categóricas en términos técnicos probabilísticos.

## Recomendaciones procesales autom?ticas

{procedural_recommendations}
{rubric_lines}

## Anexos

Anexos pendientes de selección y exportación.

## Glosario técnico

- SHA-256: función criptográfica usada para verificar integridad.
- Cadena de custodia: registro cronológico de preservación y manipulación de evidencia.

## Preguntas y respuestas para testimonio experto

**Pregunta:** ¿Qué demuestra un hash?  
**Respuesta sugerida:** Permite verificar integridad del archivo analizado, pero no demuestra por sí solo autoría personal.
"""
    return normalize_spanish(markdown)


def _challenge_2026_markdown(
    case: Case,
    legal_probatory: dict,
    media_authentication_lines: str,
    blockchain_forensics_lines: str,
    iot_forensics_lines: str,
) -> str:
    technical_rows = _challenge_technical_rows(
        case,
        bool(media_authentication_lines),
        bool(blockchain_forensics_lines),
        bool(iot_forensics_lines),
    )
    evidence_rows = _challenge_evidence_rows(case)
    legal_rows = _challenge_legal_rows(case, legal_probatory)
    findings_rows = _challenge_findings_rows(case)
    summary_lines = _challenge_summary_lines(case)
    return normalize_spanish(
        "\n".join(
            [
                "## Written Legal Evidence Report 2026",
                "",
                "### A. Technical Approach & Investigative Techniques Used",
                "",
                "| Herramienta o metodologia | Motivo de seleccion | Tareas investigativas realizadas | Limites |",
                "| --- | --- | --- | --- |",
                *technical_rows,
                "",
                "### B. Evidence Identification, Categorization & Handling",
                "",
                "| Evidencia | Tipo o categoria | Preservacion e integridad | Hash | Manejo y custodia |",
                "| --- | --- | --- | --- | --- |",
                *evidence_rows,
                "",
                "### C. Legal Authority & Investigative Requests",
                "",
                "| Autoridad legal | Solicitud investigativa | Fundamento | Estado o resolucion | Documentacion |",
                "| --- | --- | --- | --- | --- |",
                *legal_rows,
                "",
                "### D. Summary Analysis of Evidence & Investigative Findings",
                "",
                "| Evidencia o hallazgo | Relevancia investigativa | Significancia legal | Atribucion y limites |",
                "| --- | --- | --- | --- |",
                *findings_rows,
                "",
                "### Final Investigative Summary",
                "",
                *summary_lines,
            ]
        )
    )


def _challenge_technical_rows(case: Case, has_media: bool, has_blockchain: bool, has_iot: bool) -> list[str]:
    rows: list[str] = []
    tools = []
    for evidence in case.evidence:
        if evidence.tool_used:
            tools.append(evidence.tool_used)
    for action in case.actions:
        if action.tool_used:
            tools.append(action.tool_used)
    for finding in case.findings:
        if finding.tools_used:
            tools.append(finding.tools_used)
    for tool in dict.fromkeys(normalize_spanish(item).strip() for item in tools if normalize_spanish(item).strip()):
        rows.append(
            f"| {tool} | Seleccionada por su relacion con la evidencia cargada. | Preservacion, verificacion, analisis o documentacion segun registro del caso. | No sustituye validacion pericial ni autorizacion legal cuando corresponda. |"
        )
    if has_media:
        rows.append(
            "| Autenticacion de medios | Necesaria para evaluar imagen, video, audio, documento o captura sospechosa. | Revision de origen, hash, metadatos, inconsistencias, comparacion y limitaciones. | Resultado preliminar; no afirma autenticidad, falsedad ni autoria sin corroboracion. |"
        )
    if has_blockchain:
        rows.append(
            "| Analisis forense de blockchain | Necesario para registrar transacciones, wallets y ruta economica. | Registro de hash, red, monto, URL aportada, hipotesis de ruta y evidencia vinculada. | Una wallet no identifica por si sola a una persona. |"
        )
    if has_iot:
        rows.append(
            "| Analisis forense de dispositivos conectados | Necesario para documentar dispositivo, firmware, red, logs y evidencia. | Identificacion, preservacion de estado, checklist, puertos observados y limitaciones. | IP, MAC, puerto o firmware no acreditan autoria sin evidencia externa. |"
        )
    if not rows:
        rows.append(
            "| Metodologia documental forense | Adecuada al estado inicial del caso. | Ordenamiento de evidencia, custodia, hallazgos, matriz legal-probatoria y conclusiones prudentes. | Requiere completar evidencia tecnica y revision profesional. |"
        )
    return rows


def _challenge_evidence_rows(case: Case) -> list[str]:
    rows = []
    for evidence in case.evidence:
        custody = [
            action.action_type
            for action in case.actions
            if getattr(action, "evidence_id", None) == evidence.id
        ]
        rows.append(
            f"| Evidencia #{evidence.id}: {evidence.description} | {evidence.evidence_type or 'digital'} | {evidence.preservation_method or evidence.integrity_status or 'preservacion pendiente de detalle'} | `{evidence.sha256_hash or 'pendiente'}` | {', '.join(custody) if custody else 'cadena de custodia pendiente de ampliar'} |"
        )
    if not rows:
        rows.append("| Sin evidencia individual cargada | Pendiente | Pendiente de preservacion | pendiente | Pendiente de custodia |")
    return rows


def _challenge_legal_rows(case: Case, legal_probatory: dict) -> list[str]:
    rows = []
    approved = [
        item for item in case.legal_mappings if getattr(item, "decision_status", "sugerido") != "descartado"
    ]
    for mapping in approved:
        rows.append(
            f"| {mapping.norm_reference} | Medidas de corroboracion y autorizaciones necesarias segun hechos del caso. | {mapping.applicability_to_case or mapping.analysis or 'fundamento pendiente de ampliar'} | {getattr(mapping, 'decision_status', '') or mapping.verification_status} | {mapping.probatory_limits or 'documentacion y fuente registradas en biblioteca legal'} |"
        )
    if not rows:
        measures = legal_probatory.get("recommended_measures") if isinstance(legal_probatory, dict) else None
        measure_text = "; ".join(measures[:2]) if measures else "Completar mapeo legal y solicitudes investigativas."
        rows.append(
            f"| Autoridad legal pendiente de vincular | {measure_text} | No se formula encuadre definitivo sin evidencia y fuente legal registrada. | Pendiente | Registrar autorizacion, oficio, requerimiento o decision profesional aplicable. |"
        )
    return rows


def _challenge_findings_rows(case: Case) -> list[str]:
    rows = []
    for finding in case.findings:
        rows.append(
            f"| {finding.title} | {finding.technical_finding or finding.supporting_evidence or 'hallazgo pendiente de ampliar'} | {finding.preliminary_legal_relevance or 'relevancia legal pendiente de matriz'} | {finding.weaknesses_or_limitations or 'no atribuir autoria personal sin evidencia suficiente'} |"
        )
    if not rows:
        rows.append(
            "| Sin hallazgos conclusivos cargados | El caso requiere analisis adicional. | No corresponde sostener significancia legal definitiva. | No atribuir autoria ni identidad sin evidencia suficiente. |"
        )
    return rows


def _challenge_summary_lines(case: Case) -> list[str]:
    major_findings = "; ".join(f.title for f in case.findings[:3]) or "hallazgos mayores pendientes de carga"
    next_steps = []
    if not case.evidence:
        next_steps.append("incorporar evidencia identificable")
    if not any(e.sha256_hash for e in case.evidence):
        next_steps.append("calcular o registrar hash")
    if not case.actions:
        next_steps.append("registrar cadena de custodia")
    if not case.legal_mappings:
        next_steps.append("vincular matriz legal-probatoria")
    if not next_steps:
        next_steps.append("mantener revision profesional, anexos y corroboracion externa")
    return [
        f"- Importancia general: el informe organiza el incidente {case.incident_type} con evidencia, custodia, hallazgos y encuadre legal disponible.",
        f"- Hallazgos mayores: {major_findings}.",
        "- Observaciones y limitaciones: las conclusiones son prudentes y no atribuyen autoria personal sin evidencia tecnica y legal suficiente.",
        f"- Proximos pasos: {', '.join(next_steps)}.",
    ]


def _technical_forensic_overview_markdown(
    media_authentication_lines: str,
    blockchain_forensics_lines: str,
    iot_forensics_lines: str,
) -> str:
    sections = []
    if media_authentication_lines:
        sections.append(f"### Autenticacion de medios\n{media_authentication_lines}")
    if blockchain_forensics_lines:
        sections.append(f"### Blockchain y criptoactivos\n{blockchain_forensics_lines}")
    if iot_forensics_lines:
        sections.append(f"### Dispositivos conectados\n{iot_forensics_lines}")
    if not sections:
        sections.append(
            "El analisis tecnico especifico se documenta en las secciones de evidencia, custodia, hallazgos y matriz legal-probatoria cargadas para el caso."
        )
    return normalize_spanish("\n\n".join(sections))


def _media_authentication_markdown(case: Case) -> str:
    analyses = sorted(getattr(case, "deepfake_analyses", []) or [], key=lambda item: (getattr(item, "route_order", 0) or 999999, item.created_at), reverse=True)
    if not analyses:
        return ""
    lines = []
    for analysis in analyses:
        evidence_ref = f"Evidencia #{analysis.evidence_id}" if analysis.evidence_id else "Evidencia no vinculada"
        hash_value = analysis.evidence_hash or "pendiente"
        legal_refs = analysis.legal_mapping_ids or "pendiente"
        lines.append(
            "\n".join(
                [
                    f"- Medio #{analysis.id}: {analysis.media_type}. {evidence_ref}. SHA-256: `{hash_value}`.",
                    f"  - Origen: {analysis.source_origin or 'pendiente'}.",
                    f"  - Herramienta o técnica: {analysis.tool_used or 'pendiente'}.",
                    f"  - Metadatos/resumen: {analysis.metadata_summary or 'pendiente'}.",
                    f"  - Hallazgos: {analysis.findings or 'sin hallazgos concluyentes cargados'}.",
                    f"  - Clasificación preliminar: {analysis.classification}.",
                    f"  - Límites: {analysis.limitations or 'requiere pericia especializada y corroboración independiente'}.",
                    f"  - Normas aplicables vinculadas: {legal_refs}.",
                ]
            )
        )
    lines.append(
        "Conclusión prudente: la autenticación de medios es preliminar y no permite afirmar de forma concluyente que el archivo sea deepfake, auténtico o atribuible a una persona sin pericia especializada, preservación del original y corroboración independiente."
    )
    return normalize_spanish("\n".join(lines))


def _blockchain_forensics_markdown(case: Case) -> str:
    all_transactions = getattr(case, "blockchain_transactions", []) or []
    selected = [item for item in all_transactions if getattr(item, "include_in_report", True)]
    transactions = sorted(selected or all_transactions, key=lambda item: (getattr(item, "route_order", 0) or 999999, item.created_at))
    if not transactions:
        return ""
    route_lines = _blockchain_multihop_lines(transactions)
    critical_lines = _blockchain_critical_lines(transactions)
    request_lines = _blockchain_request_lines(transactions)
    annex_lines = _blockchain_annex_lines(transactions)
    rows = [
        "| ID | Red | Hash / fuente | Ruta documentada | Token/monto | Soporte probatorio | Clasificacion |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ]
    details = []
    for tx in transactions:
        readiness_label, readiness_score, readiness_missing = _blockchain_readiness(tx)
        rows.append(
            f"| #{tx.id} | {tx.blockchain} | `{tx.tx_hash}`<br>{tx.explorer_url or 'URL no informada'} | {tx.source_wallet or 'pendiente'} -> {tx.destination_wallet or 'pendiente'} | {tx.amount:.8g} {tx.token}<br>Valor aprox. {tx.approximate_value:.2f} | Evidencia #{tx.evidence_id or '-'}<br>Hash: `{tx.evidence_hash or 'pendiente'}`<br>Herramienta: {tx.tool_used or 'pendiente'}<br>Suficiencia: {readiness_label} ({readiness_score}/100) | {tx.wallet_classification} |"
        )
        details.append(
            "\n".join(
                [
                    f"- Transaccion #{tx.id}: red {tx.blockchain}, token {tx.token}, monto {tx.amount:.8g}, valor aproximado {tx.approximate_value:.2f}, fecha/hora {tx.tx_datetime or 'pendiente'}.",
                    f"  - Ruta documentada: {tx.source_wallet or 'origen pendiente'} -> {tx.destination_wallet or 'destino pendiente'}.",
                    f"  - Fuente preservada: {tx.explorer_url or 'pendiente'}; herramienta/metodo: {tx.tool_used or 'pendiente'}.",
                    f"  - Hipotesis de ruta: {tx.route_hypothesis or 'pendiente'}.",
                    f"  - Evidencia que sostiene o limita: evidencia #{tx.evidence_id or '-'}, hash `{tx.evidence_hash or 'pendiente'}`; limites: {tx.limitations or 'requiere corroboracion externa'}.",
                    f"  - Suficiencia preliminar: {readiness_label} ({readiness_score}/100). Faltantes principales: {', '.join(readiness_missing[:5]) if readiness_missing else 'sin faltantes criticos para documentacion inicial'}.",
                    f"  - Normas aplicables vinculadas: {tx.legal_mapping_ids or 'pendiente'}.",
                ]
            )
        )
    measures = "\n".join(
        [
            "- Preservar captura del explorador y registrar fecha/hora.",
            "- Guardar URL usada manualmente y anexar captura o acta.",
            "- Identificar exchange/plataforma si aplica y solicitar informacion por via legal.",
            "- Correlacionar wallets con comunicaciones, pagos, cuentas, IPs y demas evidencia del caso.",
            "- Evitar atribucion personal solo por wallet.",
        ]
    )
    return normalize_spanish(
        "\n".join(
            [
                *rows,
                "",
                "### Ruta multi-salto observada",
                *route_lines,
                "",
                "### Hipotesis de ruta y limites",
                *details,
                "",
                "### Anexo blockchain profesional",
                *annex_lines,
                "",
                "### Puntos criticos de trazabilidad",
                *critical_lines,
                "",
                "### Requerimientos sugeridos",
                *request_lines,
                "",
                "### Medidas procesales recomendadas",
                measures,
                "",
                "Limite de atribucion: una wallet o transaccion permite orientar trazabilidad economica, pero no identifica por si sola a una persona sin evidencia externa corroborante, informacion de plataforma, comunicaciones, cuentas, IPs u otros registros.",
            ]
        )
    )


def _blockchain_annex_lines(transactions: list[Any]) -> list[str]:
    lines: list[str] = [
        "| Registro | Acta de consulta | Preservación | Checklist | Uso pericial |",
        "| --- | --- | --- | --- | --- |",
    ]
    for tx in sorted(transactions, key=lambda item: (getattr(item, "route_order", 0) or 999999, item.created_at)):
        readiness_label, readiness_score, readiness_missing = _blockchain_readiness(tx)
        source = getattr(tx, "explorer_url", "") or "fuente no informada"
        evidence = f"evidencia #{getattr(tx, 'evidence_id', None)}" if getattr(tx, "evidence_id", None) else "sin evidencia vinculada"
        evidence_hash = getattr(tx, "evidence_hash", "") or "hash pendiente"
        act = (
            f"{getattr(tx, 'tx_datetime', '') or 'fecha/hora pendiente'}; "
            f"{getattr(tx, 'tool_used', '') or 'herramienta pendiente'}; "
            f"{source}"
        )
        preservation = (
            f"{evidence}; hash {evidence_hash}; "
            f"wallet origen {getattr(tx, 'source_wallet', '') or 'pendiente'}; "
            f"wallet destino {getattr(tx, 'destination_wallet', '') or 'pendiente'}"
        )
        checklist = f"{readiness_label} ({readiness_score}/100); faltantes: {', '.join(readiness_missing[:4]) if readiness_missing else 'sin faltantes criticos'}"
        use = (
            "Orienta trazabilidad economica y medidas investigativas; "
            "no acredita identidad personal ni titularidad efectiva sin corroboracion externa."
        )
        lines.append(f"| #{tx.id} | {act} | {preservation} | {checklist} | {use} |")
    if len(lines) == 2:
        lines.append("| - | Sin transacciones registradas | - | - | - |")
    return lines


def _blockchain_critical_lines(transactions: list[Any]) -> list[str]:
    lines: list[str] = []
    for tx in sorted(transactions, key=lambda item: (getattr(item, "route_order", 0) or 999999, item.created_at)):
        missing: list[str] = []
        if not getattr(tx, "evidence_id", None):
            missing.append("evidencia preservada")
        if not getattr(tx, "explorer_url", ""):
            missing.append("URL/captura del explorador")
        if not getattr(tx, "tx_datetime", ""):
            missing.append("fecha y hora de consulta")
        if not getattr(tx, "finding_id", None):
            missing.append("hallazgo tecnico")
        if not getattr(tx, "legal_mapping_ids", ""):
            missing.append("normas vinculadas")
        classification = (getattr(tx, "wallet_classification", "") or "").lower()
        if classification in {"mixer", "bridge", "contrato inteligente"}:
            lines.append(f"- Transaccion #{tx.id}: punto de cautela reforzada por {classification}; no sostener atribucion sin corroboracion externa.")
        if missing:
            lines.append(f"- Transaccion #{tx.id}: faltan {', '.join(missing)}.")
    if not lines:
        lines.append("- No se registran puntos criticos adicionales en la documentacion blockchain cargada.")
    return lines


def _blockchain_request_lines(transactions: list[Any]) -> list[str]:
    classifications = {(getattr(tx, "wallet_classification", "") or "").lower() for tx in transactions}
    lines: list[str] = []
    if "exchange" in classifications:
        lines.append("- Requerir a exchange o plataforma informacion de KYC, titularidad, logs, IPs, fechas, dispositivo y movimientos relacionados.")
    if "mixer" in classifications:
        lines.append("- Documentar limite por mixer y solicitar analisis complementario antes de sostener continuidad de fondos o atribucion.")
    if "bridge" in classifications:
        lines.append("- Preservar ambos lados del bridge: red origen, red destino, hash, monto, wallet y fecha/hora.")
    if "contrato inteligente" in classifications:
        lines.append("- Revisar contrato inteligente, eventos, funciones invocadas, direccion del contrato y wallets firmantes.")
    if any(not getattr(tx, "evidence_id", None) for tx in transactions):
        lines.append("- Vincular cada transaccion relevante con captura, comprobante, exportacion del explorador o evidencia hashada.")
    if any(not getattr(tx, "finding_id", None) for tx in transactions):
        lines.append("- Convertir los movimientos relevantes en hallazgos tecnicos antes de cerrar el informe.")
    if not lines:
        lines.append("- Mantener preservacion de capturas, hashes, URL, fecha/hora, herramienta usada y analista interviniente.")
    return lines


def _blockchain_multihop_lines(transactions: list[Any]) -> list[str]:
    if not transactions:
        return ["- No hay transacciones registradas."]
    ordered = sorted(transactions, key=lambda item: (getattr(item, "route_order", 0) or 999999, item.created_at))
    links: dict[str, int] = {}
    for tx in ordered:
        if tx.source_wallet:
            links[tx.source_wallet.strip()] = links.get(tx.source_wallet.strip(), 0) + 1
        if tx.destination_wallet:
            links[tx.destination_wallet.strip()] = links.get(tx.destination_wallet.strip(), 0) + 1
    repeated = [wallet for wallet, count in links.items() if count > 1]
    lines = [
        f"- Salto {index}: {tx.source_wallet or 'origen pendiente'} -> {tx.destination_wallet or 'destino pendiente'}; {tx.amount:.8g} {tx.token}; hash `{tx.tx_hash or 'pendiente'}`."
        for index, tx in enumerate(ordered, start=1)
    ]
    if repeated:
        lines.append(f"- Wallets que conectan saltos: {', '.join(repeated)}.")
    else:
        lines.append("- No se detectaron wallets repetidas entre saltos cargados; la ruta debe interpretarse como trazabilidad documental preliminar.")
    return lines


def _blockchain_readiness(tx: Any) -> tuple[str, int, list[str]]:
    checks = [
        ("hash de transaccion", bool(getattr(tx, "tx_hash", ""))),
        ("URL o fuente preservada", bool(getattr(tx, "explorer_url", ""))),
        ("wallet origen y destino", bool(getattr(tx, "source_wallet", "") and getattr(tx, "destination_wallet", ""))),
        ("monto y token", bool((getattr(tx, "amount", 0) or 0) > 0 and getattr(tx, "token", ""))),
        ("fecha/hora observada", bool(getattr(tx, "tx_datetime", ""))),
        ("evidencia vinculada", bool(getattr(tx, "evidence_id", None))),
        ("hipotesis de ruta", bool(getattr(tx, "route_hypothesis", ""))),
        ("hallazgo creado", bool(getattr(tx, "finding_id", None))),
        ("normas aplicadas", bool(getattr(tx, "legal_mapping_ids", ""))),
    ]
    ok_count = sum(1 for _, ok in checks if ok)
    score = round((ok_count / len(checks)) * 100)
    missing = [label for label, ok in checks if not ok]
    if score >= 78:
        return "listo para informe", score, missing
    if score >= 45:
        return "requiere refuerzo", score, missing
    return "insuficiente", score, missing


def _iot_forensics_markdown(case: Case) -> str:
    devices = sorted(getattr(case, "iot_devices", []) or [], key=lambda item: (getattr(item, "route_order", 0) or 999999, item.created_at), reverse=True)
    if not devices:
        return ""
    rows = [
        "| ID | Dispositivo | Fabricante/modelo | Firmware | IP interna/externa | Evidencia |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    details = []
    for device in devices:
        checklist = _iot_checklist_summary(device.checklist or "")
        rows.append(
            f"| #{device.id} | {device.device_type} | {device.manufacturer or 'pendiente'} {device.model or ''} | {device.firmware or 'pendiente'} | {device.internal_ip or '-'} / {device.external_ip or '-'} | #{device.evidence_id or '-'} / {device.evidence_hash or 'pendiente'} |"
        )
        details.append(
            "\n".join(
                [
                    f"- Dispositivo #{device.id}: MAC {device.mac or 'pendiente'}; puertos observados: {device.open_ports or 'pendiente'}.",
                    f"  - Metodologia/herramienta: {device.tool_used or 'OPERIA IoT Forensics'}; no se ejecutan escaneos reales automaticamente.",
                    f"  - Timeline pericial: identificacion, preservacion, observacion tecnica, hallazgo, norma aplicable e incorporacion al informe.",
                    f"  - Checklist: {checklist}.",
                    f"  - Logs disponibles: {device.logs_available or 'pendiente'}.",
                    f"  - Vulnerabilidades conocidas: {device.known_vulnerabilities or 'pendiente'}.",
                    f"  - Evidencia: #{device.evidence_id or '-'}, hash `{device.evidence_hash or 'pendiente'}`.",
                    f"  - Limites: {device.limitations or 'requiere preservacion de estado, autorizacion y correlacion externa'}.",
                    f"  - Normas aplicables vinculadas: {device.legal_mapping_ids or 'pendiente'}.",
                ]
            )
        )
    measures = "\n".join(
        [
            "- Preservar fotografia, captura, configuracion exportada o acta del dispositivo.",
            "- Registrar fecha/hora, ubicacion, responsable y estado observable.",
            "- Vincular evidencia con hash y cadena de custodia.",
            "- Documentar firmware, configuracion, logs disponibles y timeline.",
            "- Correlacionar con logs de red, usuarios, IPs y comunicaciones.",
            "- Evitar atribucion personal por IP, MAC, puerto o nombre de dispositivo sin corroboracion.",
        ]
    )
    return normalize_spanish(
        "\n".join(
            [
                *rows,
                "",
                "### Metodologia, hallazgos y limites",
                *details,
                "",
                "### Medidas recomendadas",
                measures,
                "",
                "Limite de atribucion: un dispositivo IoT, IP, MAC, puerto o firmware observado no identifica por si solo a una persona ni acredita acceso ilegitimo sin logs, autorizaciones, timeline y evidencia externa corroborante.",
            ]
        )
    )


def _iot_checklist_summary(raw_checklist: str) -> str:
    labels = {
        "physical_identification": "identificacion fisica",
        "photo_capture": "fotografia/captura",
        "hash_evidence": "hash de evidencia",
        "firmware": "firmware",
        "configuration": "configuracion",
        "logs": "logs",
        "ports": "puertos",
        "default_credentials": "credenciales por defecto",
        "network_connection": "conexion a red",
        "timeline": "linea temporal",
        "state_preservation": "preservacion de estado",
        "alteration_risk": "riesgo de alteracion",
    }
    try:
        parsed = json.loads(raw_checklist or "{}")
    except json.JSONDecodeError:
        return "checklist no estructurado"
    done = [labels.get(key, key) for key, value in parsed.items() if isinstance(value, dict) and value.get("ok")]
    if not done:
        return "sin controles marcados"
    return ", ".join(done)


def _case_narrative_markdown(case: Case) -> str:
    incident = normalize_spanish(case.incident_type or "incidente digital").strip()
    description = normalize_spanish(case.description or "").strip()
    evidence_count = len(case.evidence)
    custody_count = len(case.actions)
    finding_count = len(case.findings)
    damage_total = sum(item.amount for item in case.damage_items)
    opening = (
        f"El caso se inicia a partir de un hecho descripto como {incident}."
        if not description
        else f"El caso se inicia a partir del siguiente hecho investigado: {description}."
    )
    connectors = [
        opening,
        f"A partir de esa hipótesis fáctica, se incorporaron {evidence_count} evidencia(s) digital(es) y {custody_count} acción(es) de cadena de custodia vinculadas exclusivamente a este caso.",
    ]
    if finding_count:
        connectors.append(
            f"Sobre esa base se registraron {finding_count} hallazgo(s) técnico(s), que permiten ordenar la teoría del caso sin confundir indicios técnicos con atribución penal definitiva."
        )
    else:
        connectors.append(
            "Todavía no se cargaron hallazgos técnicos autónomos; por ello, la narrativa conserva carácter preliminar y se apoya en la evidencia preservada, la descripción del hecho y el encuadre legal aprobado."
        )
    if case.legal_mappings:
        norms = ", ".join(list(dict.fromkeys(mapping.norm_reference for mapping in case.legal_mappings if mapping.norm_reference))[:4])
        connectors.append(f"El encuadre jurídico de trabajo se estructura sobre {norms or 'las normas seleccionadas por el analista'}, siempre sujeto a validación humana y a la prueba efectivamente reunida.")
    if damage_total:
        connectors.append(f"En el plano económico, el daño preliminar cargado asciende a {damage_total:.2f} ARS, compuesto únicamente por conceptos documentados en el caso.")
    else:
        connectors.append("No se registró todavía una cuantificación económica positiva; la sección de daño queda limitada a metodología y datos pendientes.")
    connectors.append("La lectura integral debe seguir esta secuencia: hecho denunciado, evidencia preservada, custodia, hallazgos, matriz legal-probatoria, daño acreditado y conclusión técnico-jurídica.")
    return normalize_spanish("\n\n".join(connectors))


def _evidence_overview_markdown(case: Case) -> str:
    if not case.evidence:
        return "No hay evidencia informática cargada para puntear."
    rows = []
    custody_by_evidence: dict[int, list[Any]] = {}
    for action in case.actions:
        if getattr(action, "evidence_id", None):
            custody_by_evidence.setdefault(action.evidence_id, []).append(action)
    for evidence in case.evidence:
        linked_findings = [finding for finding in case.findings if getattr(finding, "evidence_id", None) == evidence.id]
        custody_count = len(custody_by_evidence.get(evidence.id, []))
        what_proves = (
            "; ".join(finding.title for finding in linked_findings[:3])
            if linked_findings
            else "presencia, origen declarado o contenido observable de la pieza incorporada"
        )
        what_limits = []
        if not evidence.sha256_hash:
            what_limits.append("falta hash SHA-256")
        if custody_count == 0:
            what_limits.append("falta acción de custodia vinculada")
        if evidence.was_altered:
            what_limits.append("existe alteración declarada que debe justificarse")
        limit_text = "; ".join(what_limits) if what_limits else "sin límite crítico registrado en integridad básica"
        rows.append(
            "\n".join(
                [
                    f"- Evidencia #{evidence.id}: {evidence.description}.",
                    f"  - Tipo/categoría: {evidence.evidence_type or 'digital'}; fuente: {evidence.source or 'no informada'}.",
                    f"  - Hash SHA-256: `{evidence.sha256_hash or 'pendiente'}`; integridad: {evidence.integrity_status}.",
                    f"  - Aporta al caso: {what_proves}.",
                    f"  - Límite probatorio: {limit_text}.",
                ]
            )
        )
    return normalize_spanish("\n".join(rows))


def _investigative_techniques_markdown(case: Case) -> str:
    rows = [
        "| Tecnica o herramienta | Quien la aplico | Como se uso | Resultado esperado | Limite pericial |",
        "| --- | --- | --- | --- | --- |",
    ]
    seen: set[str] = set()

    def add(tool: str, actor: str, method: str, result: str, limit: str) -> None:
        key = f"{tool}|{actor}|{method}"
        if key in seen:
            return
        seen.add(key)
        rows.append(f"| {tool} | {actor or 'Analista interviniente'} | {method} | {result} | {limit} |")

    for evidence in case.evidence:
        add(
            evidence.tool_used or "Preservacion documental y hash",
            evidence.responsible or evidence.custodian,
            f"Se identifico y preservo la evidencia #{evidence.id}: {evidence.description}.",
            f"Control de integridad: SHA-256 {evidence.sha256_hash or 'pendiente'}; estado {evidence.integrity_status}.",
            "El hash acredita integridad del objeto preservado, no autoria personal.",
        )
    for action in case.actions:
        add(
            action.tool_used or "Cadena de custodia",
            action.user_responsible or action.validated_by,
            action.command_or_procedure or action.detailed_description,
            action.result_obtained or f"Accion registrada como {action.action_type}.",
            action.legal_observations or "Requiere continuidad cronologica y validacion de responsables.",
        )
    for finding in case.findings:
        add(
            finding.tools_used or "Analisis tecnico-forense",
            "Analista interviniente",
            finding.technical_finding or finding.explanation,
            finding.preliminary_legal_relevance or "Hallazgo incorporado a la teoria del caso.",
            finding.weaknesses_or_limitations or "No sostener atribucion personal sin corroboracion externa.",
        )
    if not seen:
        add(
            "Metodologia documental forense",
            "Analista interviniente",
            "Ordenamiento inicial del caso, definicion de alcance, preservacion pendiente y matriz legal-probatoria.",
            "Base minima para planificar la investigacion.",
            "Requiere evidencia, hash, custodia y revision profesional.",
        )
    return normalize_spanish("\n".join(rows))


def _evidence_identification_markdown(case: Case) -> str:
    if not case.evidence:
        return "No hay evidencia identificada para esta seccion."
    rows = [
        "| Evidencia | Categoria | Quien la identifico | Como se encontro | Preservacion | Hash | Estado |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for evidence in case.evidence:
        how_found = evidence.source or evidence.custody_observations or "Incorporada por el analista a partir del relato y los archivos disponibles."
        who = evidence.responsible or evidence.custodian or "Analista interviniente"
        rows.append(
            f"| #{evidence.id} {evidence.description} | {evidence.evidence_type or 'digital'} | {who} | {how_found} | {evidence.preservation_method or evidence.evidence_nature or 'preservacion pendiente de ampliar'} | `{evidence.sha256_hash or 'pendiente'}` | {evidence.integrity_status} |"
        )
    return normalize_spanish("\n".join(rows))


def _investigated_documentation_markdown(case: Case) -> str:
    rows = [
        "| Documento o fuente | Quien lo reviso | Metodo de revision | Relevancia | Pendiente o limite |",
        "| --- | --- | --- | --- | --- |",
    ]
    for evidence in case.evidence:
        rows.append(
            f"| Evidencia #{evidence.id}: {evidence.description} | {evidence.responsible or evidence.custodian or 'Analista interviniente'} | Verificacion de descripcion, fuente, hash, preservacion y custodia. | Soporta la existencia material del hecho o un indicador del caso. | {evidence.custody_observations or 'Ampliar contexto, origen y autorizacion si corresponde.'} |"
        )
    for action in case.actions:
        rows.append(
            f"| Registro de custodia #{action.id} | {action.user_responsible or action.validated_by or 'Analista interviniente'} | Revision cronologica de accion, procedimiento, resultado y hashes. | Permite reconstruir manipulacion, preservacion o analisis de la evidencia. | {action.legal_observations or 'Mantener bitacora completa y validacion posterior.'} |"
        )
    for mapping in case.legal_mappings:
        if getattr(mapping, "decision_status", "sugerido") == "descartado":
            continue
        rows.append(
            f"| Fuente legal {mapping.norm_reference} | {mapping.analyst_name or 'Analista legal'} | Contraste con biblioteca legal registrada y decision del analista. | Fundar la tipificacion preliminar y la relevancia probatoria. | {mapping.probatory_limits or 'Vincular evidencia concreta a cada elemento del tipo penal.'} |"
        )
    if len(rows) == 2:
        rows.append("| Sin documentacion investigada cargada | Analista interviniente | Pendiente | Pendiente | Incorporar evidencia, custodia y fuentes legales. |")
    return normalize_spanish("\n".join(rows))


def _analysis_evidence_markdown(case: Case) -> str:
    rows = [
        "| Elemento analizado | Quien lo encontro | Como lo encontro | Que sostiene | Que no permite afirmar |",
        "| --- | --- | --- | --- | --- |",
    ]
    for finding in case.findings:
        evidence = next((item for item in case.evidence if item.id == getattr(finding, "evidence_id", None)), None)
        who = evidence.responsible if evidence else "Analista interviniente"
        how = evidence.source if evidence and evidence.source else finding.tools_used or "Analisis de la evidencia cargada."
        supports = finding.supporting_evidence or finding.technical_finding or finding.explanation
        limits = finding.weaknesses_or_limitations or "No permite condena ni atribucion penal por si solo; requiere corroboracion externa y valoracion judicial."
        rows.append(f"| {finding.title} | {who or 'Analista interviniente'} | {how} | {supports} | {limits} |")
    if not case.findings:
        for evidence in case.evidence:
            rows.append(
                f"| Evidencia #{evidence.id}: {evidence.description} | {evidence.responsible or evidence.custodian or 'Analista interviniente'} | {evidence.source or 'Incorporacion documental al expediente tecnico.'} | Permite demostrar existencia, contenido o indicador tecnico preservado. | No permite por si sola identificar autor, dolo, participacion o responsabilidad penal definitiva. |"
            )
    if len(rows) == 2:
        rows.append("| Sin evidencia analitica cargada | Analista interviniente | Pendiente | Pendiente | No formular conclusiones condenatorias sin evidencia. |")
    return normalize_spanish("\n".join(rows))


def _penal_legal_theory_markdown(case: Case, legal_probatory: dict) -> str:
    approved = [
        mapping for mapping in case.legal_mappings if getattr(mapping, "decision_status", "sugerido") != "descartado"
    ]
    intro = [
        "La aplicacion penal se formula como hipotesis juridico-probatoria, no como declaracion de culpabilidad. Para sostener una imputacion o eventual condena se requiere acreditar materialidad del hecho, tipicidad objetiva, elemento subjetivo, nexo causal, autoria o participacion, antijuridicidad, culpabilidad y prueba valorable bajo control judicial.",
        "En el contexto de OPERIA, la norma aplicable solo puede sostenerse cuando proviene de la biblioteca legal registrada y se vincula con evidencia concreta del caso.",
    ]
    if not approved:
        intro.append(
            "Actualmente no hay normas aprobadas por analista en el caso. No corresponde afirmar delito aplicable ni responsabilidad penal hasta completar el mapeo legal y la matriz probatoria."
        )
        return normalize_spanish("\n\n".join(intro))

    blocks = intro + [
        "| Norma | Por que resulta relevante | Evidencia que la sostiene | Que falta para una condena o reproche penal robusto |",
        "| --- | --- | --- | --- |",
    ]
    for mapping in approved:
        links = _mapping_links_for_case(mapping, case)
        linked_evidence = []
        missing = []
        for link in links:
            evidence = getattr(link, "evidence", None)
            if evidence:
                linked_evidence.append(
                    f"Evidencia #{evidence.id}: {evidence.description} ({link.legal_element or 'elemento legal no indicado'}, fuerza {link.probatory_strength})"
                )
            if getattr(link, "missing_evidence", ""):
                missing.append(link.missing_evidence)
            elif getattr(link, "recommended_measure", ""):
                missing.append(link.recommended_measure)
        evidence_text = "; ".join(linked_evidence) if linked_evidence else "Sin evidencia vinculada de manera especifica."
        missing_text = "; ".join(missing) if missing else mapping.probatory_limits or "Corroborar todos los elementos del tipo penal, autoria, dolo, nexo causal y alcance del dano."
        relevance = mapping.applicability_to_case or mapping.analysis or "Relevancia pendiente de ampliar por analista."
        blocks.append(f"| {mapping.norm_reference} | {relevance} | {evidence_text} | {missing_text} |")

    score = legal_probatory.get("score", 0) if isinstance(legal_probatory, dict) else 0
    risk = legal_probatory.get("risk_level", "pendiente") if isinstance(legal_probatory, dict) else "pendiente"
    blocks.append(
        f"\nEvaluacion de suficiencia: score legal-probatorio {score}/100; riesgo {risk}. Si el soporte probatorio es parcial, el informe debe hablar de compatibilidad juridica y medidas investigativas, no de condena asegurada."
    )
    return normalize_spanish("\n".join(blocks))


def _damage_methodology_markdown(case: Case, total_damage: float) -> str:
    base = (
        "Metodología de cuantificación: el daño económico preliminar se calcula como suma de conceptos individualizados "
        "y documentados en el caso: pérdida directa acreditada, costos razonables de respuesta, recuperación o remediación, "
        "lucro cesante documentado cuando exista soporte suficiente y costos periciales necesarios. La fórmula aplicada "
        "no presume perjuicios no cargados ni sustituye determinación judicial."
    )
    legal_basis = (
        "Base normativa civil registrada para futuras validaciones: Código Civil y Comercial de la Nación, arts. 1716, "
        "1737, 1738, 1739 y 1740, en cuanto orientan deber de reparar, concepto de daño, indemnización, prueba del daño "
        "y reparación plena. La cita específica debe mantenerse vinculada a fuente oficial registrada en la biblioteca legal."
    )
    if not case.damage_items:
        return normalize_spanish(
            "\n".join(
                [
                    base,
                    legal_basis,
                    "Resultado: no hay conceptos económicos cargados; el monto informado permanece en 0.00 ARS hasta que se incorporen comprobantes, presupuestos, facturas, registros contables, trazabilidad de pagos o documentación equivalente.",
                ]
            )
        )
    supported = [item for item in case.damage_items if item.value_source or item.supporting_evidence]
    unsupported = [item for item in case.damage_items if not item.value_source and not item.supporting_evidence]
    lines = [
        base,
        legal_basis,
        f"Resultado: se computan {len(case.damage_items)} concepto(s) por un total preliminar de {total_damage:.2f} ARS.",
        f"Soporte documental: {len(supported)} concepto(s) con fuente o evidencia indicada; {len(unsupported)} concepto(s) requieren respaldo adicional.",
    ]
    if unsupported:
        lines.append("Advertencia metodológica: los conceptos sin fuente o evidencia se informan como estimación débil y no deben presentarse como daño acreditado.")
    return normalize_spanish("\n".join(lines))


def _default_hypotheses_markdown(case: Case) -> str:
    evidence_count = len(case.evidence)
    custody_count = len(case.actions)
    incident = normalize_spanish(case.incident_type or "incidente digital")
    incident_l = incident.lower()
    if evidence_count <= 1 and not case.findings:
        if any(term in incident_l for term in ["acceso", "intrusion", "intrusión"]):
            core = "un acceso ilegítimo o intrusión sobre cuenta, sistema, servicio o entorno digital, cuya materialidad exige corroborar logs, sesiones, permisos, titulares, IPs, dispositivos y trazabilidad temporal"
        elif any(term in incident_l for term in ["daño", "dano", "dos", "disponibilidad", "ransomware"]):
            core = "una afectación de disponibilidad, integridad o funcionamiento de sistemas o datos, cuya materialidad exige preservar estado previo/posterior, logs, hash, configuración, impacto operativo y nexo causal"
        elif any(term in incident_l for term in ["blockchain", "cripto", "wallet"]):
            core = "una ruta económica digital o transferencia cripto vinculada al hecho investigado, cuya relevancia exige corroborar wallet, hash de transacción, titularidad, plataforma, comunicaciones y trazabilidad de fondos"
        elif any(term in incident_l for term in ["deepfake", "medio", "audio", "video", "imagen"]):
            core = "una posible manipulación o autenticidad controvertida de medios digitales, cuya valoración exige fuente original, metadatos, hash, análisis de edición, contexto de publicación y corroboración independiente"
        else:
            core = f"un incidente digital de tipo {incident}, cuya explicación exige preservar evidencia, verificar integridad, identificar fuente, reconstruir cronología y precisar nexo causal"
        return normalize_spanish(
            f"- Hipótesis principal: el hecho investigado resulta compatible con {core}. Con el estado actual de la evidencia no corresponde formular hipótesis alternativas autónomas."
        )
    return normalize_spanish(
        "\n".join(
            [
                f"- Hipotesis principal: el relato y la evidencia cargada son compatibles con un {incident}; soporte actual: {evidence_count} evidencia(s) y {custody_count} accion(es) de custodia. Requiere validar origen, integridad, titularidad y nexo causal.",
                "- Hipotesis alternativa 1: el evento puede responder a error operativo, compromiso de credenciales, suplantacion o intermediacion de una plataforma; requiere contrastar logs, titulares, sesiones, dispositivos y comunicaciones.",
                "- Hipotesis alternativa 2: si hay perjuicio economico, la trazabilidad financiera puede demostrar recorrido o compatibilidad temporal, pero no identifica por si sola al autor.",
                "- Riesgo de error: no formular atribucion personal ni calificacion penal definitiva sin evidencia externa, oficios, pericia complementaria y revision profesional.",
            ]
        )
    )


def _legal_recommendation_markdown(recommendations: list[Any]) -> str:
    if not recommendations:
        return ""
    lines = []
    for item in recommendations:
        if isinstance(item, dict):
            reference = item.get("reference", "Norma pendiente")
            title = item.get("title", "")
            why = item.get("why", "")
            evidence_needed = item.get("evidence_needed", "")
            source_url = item.get("source_url", "")
            text = item.get("text", "")
            subjective = item.get("subjective_elements", "")
        else:
            reference = f"{item.code} art. {item.article_number}{' inc. ' + item.subsection if item.subsection else ''}"
            title = item.title
            why = item.objective_elements
            evidence_needed = item.evidentiary_requirements
            source_url = item.official_url
            text = item.text
            subjective = item.subjective_elements
        lines.extend(
            [
                f"- **{reference} - {title}.**",
                f"  - Texto legal resumido registrado: {text or 'pendiente de carga textual completa'}.",
                f"  - Elementos objetivos a verificar: {why or 'pendiente'}.",
                f"  - Elementos subjetivos o recaudos: {subjective or 'pendiente'}.",
                f"  - Evidencia necesaria: {evidence_needed or 'pendiente'}.",
                f"  - Fuente oficial registrada: {source_url or 'pendiente de verificacion'}.",
                "  - Aplicacion prudente al caso: posible relevancia preliminar, sujeta a verificacion de hechos, evidencia preservada y revision humana.",
            ]
        )
    return normalize_spanish("\n".join(lines))


def _legal_mapping_evidence_suffix(mapping: Any) -> str:
    links = [link for link in _mapping_links_for_case(mapping) if getattr(link, "evidence", None)]
    if not links:
        return ""
    pieces = []
    for link in links:
        evidence = link.evidence
        pieces.append(
            f"Evidencia #{evidence.id}: {evidence.description} "
            f"(elemento: {link.legal_element or 'no especificado'}, estado: {getattr(link, 'element_status', 'pendiente')}, "
            f"fuerza: {link.probatory_strength})."
        )
    return " Evidencia vinculada: " + " ".join(pieces)


def legal_probatory_assessment(case: Case) -> dict[str, Any]:
    case = isolated_case_snapshot(case)
    approved_mappings = [
        mapping for mapping in case.legal_mappings if getattr(mapping, "decision_status", "sugerido") != "descartado"
    ]
    rows: list[dict[str, Any]] = []
    missing = weak = proved = contested = high_risk = 0
    for mapping in approved_mappings:
        links = _mapping_links_for_case(mapping, case)
        if not links:
            missing += 1
            rows.append(
                {
                    "norm_reference": mapping.norm_reference,
                    "legal_element": mapping.legal_role or "Elemento legal no vinculado",
                    "evidence": "",
                    "evidence_hash": "",
                    "element_status": "faltante",
                    "probatory_strength": "sin evidencia",
                    "contradiction_risk": "medio",
                    "recommended_measure": "Vincular evidencia concreta antes de sostener esta norma en la conclusion.",
                }
            )
            continue
        for link in links:
            evidence = getattr(link, "evidence", None)
            status = getattr(link, "element_status", "") or "pendiente"
            strength = getattr(link, "probatory_strength", "") or "medio"
            risk = getattr(link, "contradiction_risk", "") or "bajo"
            if status == "probado":
                proved += 1
            elif status in {"debil", "pendiente"} or strength == "bajo":
                weak += 1
            elif status == "controvertido":
                contested += 1
            elif status == "faltante":
                missing += 1
            if risk in {"alto", "critico"}:
                high_risk += 1
            rows.append(
                {
                    "norm_reference": mapping.norm_reference,
                    "legal_element": getattr(link, "legal_element", "") or mapping.legal_role or "Elemento legal",
                    "evidence": f"#{evidence.id} {evidence.description}" if evidence else "",
                    "evidence_hash": getattr(evidence, "sha256_hash", "") if evidence else "",
                    "element_status": status,
                    "probatory_strength": strength,
                    "contradiction_risk": risk,
                    "recommended_measure": getattr(link, "recommended_measure", "") or getattr(link, "missing_evidence", "") or "Mantener trazabilidad y corroboracion.",
                }
            )
    score = max(0, 100 - missing * 18 - weak * 9 - contested * 14 - high_risk * 18)
    level = "bajo" if score >= 80 else "medio" if score >= 55 else "alto"
    conclusion_mode = "fortalecida" if score >= 80 else "prudente" if score >= 55 else "insuficiente"
    return {
        "rows": rows,
        "summary": {
            "approved_mappings": len(approved_mappings),
            "proved": proved,
            "weak": weak,
            "missing": missing,
            "contested": contested,
            "high_risk": high_risk,
            "score": score,
            "risk_level": level,
            "conclusion_mode": conclusion_mode,
        },
    }


def report_exportability_assessment(
    case: Case,
    legal_probatory: dict[str, Any] | None = None,
    report: Report | None = None,
) -> dict[str, Any]:
    legal_probatory = legal_probatory or legal_probatory_assessment(case)
    legal_summary = legal_probatory["summary"]
    evidence_count = len(case.evidence)
    custody_count = len(case.actions)
    hashed_evidence_count = sum(1 for item in case.evidence if item.sha256_hash)
    approved_legal_count = legal_summary["approved_mappings"]
    proved_or_supported = legal_summary["proved"] + legal_summary["weak"]
    review_score = report.review_score or 0 if report else 0

    checklist = {
        "analyst_present": bool(report and normalize_spanish(report.author or "").strip()),
        "case_narrative": bool(normalize_spanish(case.description or "").strip()),
        "evidence_present": evidence_count > 0,
        "hashes_present": evidence_count > 0 and hashed_evidence_count == evidence_count,
        "custody_present": custody_count > 0,
        "approved_legal_mapping": approved_legal_count > 0,
        "matrix_has_support": proved_or_supported > 0,
        "critical_gaps_absent": legal_summary["missing"] == 0 and legal_summary["high_risk"] == 0,
        "human_review_score": review_score >= 80,
    }
    weights = {
        "analyst_present": 8,
        "case_narrative": 8,
        "evidence_present": 14,
        "hashes_present": 12,
        "custody_present": 12,
        "approved_legal_mapping": 16,
        "matrix_has_support": 14,
        "critical_gaps_absent": 10,
        "human_review_score": 6,
    }
    score = sum(weights[key] for key, value in checklist.items() if value)
    if score >= 86 and checklist["critical_gaps_absent"] and checklist["human_review_score"]:
        level = "Apto para presentación"
    elif score >= 68 and checklist["approved_legal_mapping"] and checklist["evidence_present"]:
        level = "Listo para revisión"
    elif score >= 38 and checklist["evidence_present"]:
        level = "Informe preliminar"
    else:
        level = "Borrador técnico"

    missing_items = [
        label
        for key, label in {
            "analyst_present": "Informar analista interviniente",
            "case_narrative": "Completar narrativa del caso",
            "evidence_present": "Cargar evidencia digital",
            "hashes_present": "Completar hash SHA-256 de la evidencia",
            "custody_present": "Registrar cadena de custodia",
            "approved_legal_mapping": "Aprobar encuadre legal por analista",
            "matrix_has_support": "Vincular normas con evidencia concreta",
            "critical_gaps_absent": "Cerrar elementos legales faltantes o riesgos altos",
            "human_review_score": "Completar revisión humana con puntaje suficiente",
        }.items()
        if not checklist[key]
    ]
    return {
        "level": level,
        "score": score,
        "checklist": checklist,
        "missing_items": missing_items,
        "evidence_count": evidence_count,
        "hashed_evidence_count": hashed_evidence_count,
        "custody_count": custody_count,
        "approved_legal_count": approved_legal_count,
        "legal_score": legal_summary["score"],
        "legal_risk_level": legal_summary["risk_level"],
    }


def exportability_markdown(exportability: dict[str, Any]) -> str:
    checklist = exportability["checklist"]
    labels = {
        "analyst_present": "Analista identificado",
        "case_narrative": "Narrativa del caso",
        "evidence_present": "Evidencia cargada",
        "hashes_present": "Hashes completos",
        "custody_present": "Cadena de custodia",
        "approved_legal_mapping": "Encuadre legal aprobado",
        "matrix_has_support": "Normas vinculadas a evidencia",
        "critical_gaps_absent": "Sin brechas legales críticas",
        "human_review_score": "Revisión humana suficiente",
    }
    lines = [
        f"- Nivel: **{exportability['level']}**.",
        f"- Score de exportabilidad: **{exportability['score']} / 100**.",
        f"- Evidencias con hash: {exportability['hashed_evidence_count']} de {exportability['evidence_count']}.",
        f"- Acciones de custodia: {exportability['custody_count']}.",
        f"- Normas aprobadas: {exportability['approved_legal_count']}.",
        f"- Score legal-probatorio: {exportability['legal_score']} / 100 ({exportability['legal_risk_level']}).",
    ]
    lines.extend(f"- {label}: {'cumplido' if checklist[key] else 'pendiente'}." for key, label in labels.items())
    if exportability["missing_items"]:
        lines.append("- Pendientes principales: " + "; ".join(exportability["missing_items"][:6]) + ".")
    return normalize_spanish("\n".join(lines))


def build_smart_executive_summary(
    case: Case,
    legal_probatory: dict[str, Any] | None = None,
    exportability: dict[str, Any] | None = None,
) -> str:
    legal_probatory = legal_probatory or legal_probatory_assessment(case)
    exportability = exportability or report_exportability_assessment(case, legal_probatory)
    legal_summary = legal_probatory["summary"]
    total_damage = sum(item.amount for item in case.damage_items)
    incident = normalize_spanish(case.incident_type or "incidente digital")
    description = normalize_spanish(case.description or "").strip()
    facts = description or f"se investiga un posible {incident}"
    supported_elements = [
        f"{row['norm_reference']} - {row['legal_element']}"
        for row in legal_probatory["rows"]
        if row["element_status"] in {"probado", "pendiente", "debil"} and row.get("evidence")
    ]
    approved_norms = list(
        dict.fromkeys(
            mapping.norm_reference
            for mapping in case.legal_mappings
            if getattr(mapping, "decision_status", "sugerido") != "descartado"
        )
    )
    accredited = [
        f"{len(case.evidence)} evidencia(s) digital(es) incorporada(s)",
        f"{len(case.actions)} accion(es) de custodia registrada(s)",
    ]
    if supported_elements:
        accredited.append(f"elementos legal-probatorios vinculados: {', '.join(supported_elements[:3])}")
    if total_damage:
        accredited.append(f"daño económico estimado preliminar de {total_damage:.2f} ARS")
    missing = exportability["missing_items"][:5]
    norms_text = ", ".join(approved_norms[:5]) if approved_norms else "sin normas aprobadas por analista"
    missing_text = "; ".join(missing) if missing else "no se registran brechas críticas según la matriz actual"
    attribution_text = (
        "no se advierten elementos suficientes para atribución personal concluyente"
        if not attribution_assessment(case)["sufficient"]
        else "existen indicadores de atribución técnica preliminar que requieren valoración profesional"
    )
    return normalize_spanish(
        "\n".join(
            [
                f"- Hecho investigado: {facts}.",
                f"- Lectura ejecutiva: el caso se analiza como {incident}; la matriz actual lo ubica en nivel **{exportability['level']}** con score {exportability['score']} / 100.",
                f"- Qué se pudo acreditar: {'; '.join(accredited)}.",
                f"- Encuadre legal de trabajo: {norms_text}.",
                f"- Qué no se pudo acreditar todavía: {missing_text}.",
                f"- Atribución: {attribution_text}.",
                f"- Estado legal-probatorio: score {legal_summary['score']} / 100, riesgo {legal_summary['risk_level']}, conclusión {legal_summary['conclusion_mode']}.",
            ]
        )
    )


def report_preview_payload(report: Report) -> dict[str, Any]:
    case = report.case
    legal_probatory = legal_probatory_assessment(case)
    exportability = report_exportability_assessment(case, legal_probatory, report=report)
    contradictions = legal_contradiction_assessment(case)
    checklist = final_pericial_checklist(report, legal_probatory, exportability, contradictions)
    annexes = report_annexes_payload(report, legal_probatory)
    sections = _report_preview_sections(report.markdown_content or "")
    return {
        "report_id": report.id,
        "case_id": report.case_id,
        "title": report.title,
        "author": report.author,
        "status": report.status,
        "review_score": report.review_score,
        "executive_summary": extract_markdown_section(report.markdown_content or "", "Resumen ejecutivo"),
        "exportability": exportability,
        "contradictions": contradictions,
        "final_checklist": checklist,
        "annexes": annexes,
        "final_seal": report_final_seal_payload(report),
        "sections": sections,
        "warnings": _preview_warnings(exportability, contradictions, sections),
        "can_export_final": checklist["ready"],
    }


def build_final_pericial_seal(report: Report, checklist: dict[str, Any], analyst_name: str = "", declaration: str = "") -> dict[str, Any]:
    sealed_at = utcnow().isoformat()
    sealed_by = normalize_spanish(analyst_name or report.author or "").strip() or "Analista no informado"
    declaration_text = normalize_spanish(declaration or "").strip() or (
        "El analista interviniente deja constancia de que verifico el checklist pericial final, "
        "la coherencia del informe, los anexos incorporados y las condiciones de exportacion final."
    )
    fingerprint = sha256(
        "|".join(
            [
                str(report.id),
                str(report.case_id),
                report.version or "",
                sealed_by,
                sealed_at,
                str(checklist.get("score", 0)),
                declaration_text,
            ]
        ).encode("utf-8")
    ).hexdigest()
    return {
        "seal_id": f"OPERIA-SEAL-{fingerprint[:16].upper()}",
        "sealed_at": sealed_at,
        "sealed_by": sealed_by,
        "declaration": declaration_text,
        "checklist_score": checklist.get("score", 0),
        "report_id": report.id,
        "case_id": report.case_id,
        "report_version": report.version,
    }


def report_final_seal_payload(report: Report) -> dict[str, Any] | None:
    observations = normalize_spanish(report.observations or "")
    if "OPERIA-SEAL-" not in observations:
        return None
    seal_line = next((line for line in observations.splitlines() if "OPERIA-SEAL-" in line), "")
    seal_id = seal_line.split(":", 1)[-1].strip() if ":" in seal_line else seal_line.strip()
    return {
        "sealed": report.status == "final",
        "seal_id": seal_id,
        "observations": observations,
        "report_version": report.version,
    }


def extract_markdown_section(markdown: str, title: str) -> str:
    normalized_title = normalize_spanish(title).strip().lower()
    current = ""
    lines: list[str] = []
    collecting = False
    for line in normalize_spanish(markdown).splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            if collecting:
                break
            collecting = current.lower() == normalized_title
            continue
        if collecting:
            lines.append(line)
    return "\n".join(lines).strip()


def replace_executive_summary(report: Report, summary: str) -> str:
    markdown = normalize_spanish(report.markdown_content or "")
    new_block = f"## Resumen ejecutivo\n\n{normalize_spanish(summary).strip()}\n"
    lines = markdown.splitlines()
    start = end = None
    for index, line in enumerate(lines):
        if line.strip() == "## Resumen ejecutivo":
            start = index
            end = len(lines)
            for next_index in range(index + 1, len(lines)):
                if lines[next_index].startswith("## "):
                    end = next_index
                    break
            break
    if start is None:
        return markdown.rstrip() + "\n\n" + new_block
    updated = lines[:start] + new_block.rstrip().splitlines() + [""] + lines[end:]
    return "\n".join(updated).strip() + "\n"


def legal_contradiction_assessment(case: Case) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    by_mapping_element: dict[tuple[int, str], list[Any]] = {}
    for mapping in case.legal_mappings:
        if getattr(mapping, "decision_status", "sugerido") == "descartado":
            continue
        for link in getattr(mapping, "evidence_links", []) or []:
            element = normalize_spanish(link.legal_element or mapping.legal_role or "elemento").strip().lower()
            by_mapping_element.setdefault((mapping.id, element), []).append(link)
            risk = normalize_spanish(getattr(link, "contradiction_risk", "") or "").lower()
            status = normalize_spanish(getattr(link, "element_status", "") or "").lower()
            if risk in {"alto", "critico"} or status == "controvertido":
                issues.append(
                    {
                        "severity": "bloqueante" if risk == "critico" else "alta",
                        "norm_reference": mapping.norm_reference,
                        "legal_element": link.legal_element or mapping.legal_role or "Elemento legal",
                        "evidence_id": link.evidence_id,
                        "message": "La evidencia vinculada registra contradicción o estado controvertido.",
                        "recommended_action": link.recommended_measure
                        or "Resolver contradicción, incorporar corroboración externa o degradar la conclusión.",
                    }
                )
    for (mapping_id, element), links in by_mapping_element.items():
        statuses = {normalize_spanish(link.element_status or "").lower() for link in links}
        if "probado" in statuses and ({"faltante", "controvertido"} & statuses):
            mapping = next((item for item in case.legal_mappings if item.id == mapping_id), None)
            issues.append(
                {
                    "severity": "alta",
                    "norm_reference": mapping.norm_reference if mapping else "",
                    "legal_element": element,
                    "evidence_id": None,
                    "message": "El mismo elemento legal aparece simultáneamente como probado y faltante/controvertido.",
                    "recommended_action": "Unificar criterio probatorio antes de exportar una versión final.",
                }
            )
    blocking = any(item["severity"] == "bloqueante" for item in issues)
    return {
        "blocking": blocking,
        "count": len(issues),
        "risk_level": "crítico" if blocking else "alto" if issues else "bajo",
        "issues": issues,
    }


def final_pericial_checklist(
    report: Report,
    legal_probatory: dict[str, Any] | None = None,
    exportability: dict[str, Any] | None = None,
    contradictions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    case = report.case
    legal_probatory = legal_probatory or legal_probatory_assessment(case)
    exportability = exportability or report_exportability_assessment(case, legal_probatory, report=report)
    contradictions = contradictions or legal_contradiction_assessment(case)
    markdown = normalize_spanish(report.markdown_content or "").lower()
    annexes = report_annexes_payload(report, legal_probatory)
    checks = {
        "evidencia_preservada": bool(case.evidence) and all(not item.was_altered for item in case.evidence),
        "hash": bool(case.evidence) and all(item.sha256_hash for item in case.evidence),
        "custodia": bool(case.actions),
        "fuente_legal": legal_probatory["summary"]["approved_mappings"] > 0,
        "analista": bool(normalize_spanish(report.author or "").strip()),
        "revision": report.review_score >= 80,
        "metadatos": bool(report.id and report.case_id and report.version and report.created_at),
        "conclusion": "conclusi" in markdown and len(extract_markdown_section(report.markdown_content or "", "Conclusión jurídicamente defendible").split()) >= 20,
        "anexos": annexes["count"] > 0,
        "sin_contradicciones_bloqueantes": not contradictions["blocking"],
        "exportabilidad_suficiente": exportability["level"] in {"Listo para revisión", "Apto para presentación"},
    }
    labels = {
        "evidencia_preservada": "Evidencia preservada",
        "hash": "Hash SHA-256 de evidencia",
        "custodia": "Cadena de custodia",
        "fuente_legal": "Fuente legal aprobada",
        "analista": "Analista identificado",
        "revision": "Revisión humana suficiente",
        "metadatos": "Metadatos del informe",
        "conclusion": "Conclusión técnico-jurídica",
        "anexos": "Anexos reales",
        "sin_contradicciones_bloqueantes": "Sin contradicciones bloqueantes",
        "exportabilidad_suficiente": "Exportabilidad suficiente",
    }
    items = [
        {
            "key": key,
            "label": label,
            "ok": checks[key],
            "required": True,
            "message": "Cumplido" if checks[key] else _checklist_recommendation(key),
        }
        for key, label in labels.items()
    ]
    missing = [item["label"] for item in items if item["required"] and not item["ok"]]
    return {
        "ready": not missing,
        "score": round(100 * sum(1 for item in items if item["ok"]) / len(items)),
        "missing": missing,
        "items": items,
    }


def report_annexes_payload(report: Report, legal_probatory: dict[str, Any] | None = None) -> dict[str, Any]:
    case = report.case
    legal_probatory = legal_probatory or legal_probatory_assessment(case)
    evidence_annexes = [
        {
            "type": "evidencia",
            "title": f"Evidencia #{item.id}: {item.description}",
            "sha256": item.sha256_hash or "",
            "md5": item.md5_hash or "",
            "file_location": item.file_location or "",
            "source": item.source or "",
            "integrity_status": item.integrity_status,
        }
        for item in case.evidence
    ]
    custody_annexes = [
        {
            "type": "custodia",
            "title": f"Custodia #{item.id}: {item.action_type}",
            "detail": item.detailed_description,
            "evidence_id": item.evidence_id,
            "hash_after": item.hash_after or item.hash_before or "",
        }
        for item in case.actions
    ]
    legal_matrix_annex = {
        "type": "matriz_legal_probatoria",
        "title": "Matriz legal-probatoria",
        "rows": len(legal_probatory["rows"]),
        "score": legal_probatory["summary"]["score"],
        "risk_level": legal_probatory["summary"]["risk_level"],
    }
    manifest_annex = {
        "type": "manifiesto_exportacion",
        "title": "Manifiesto de exportación",
        "report_id": report.id,
        "case_id": report.case_id,
        "version": report.version,
    }
    annexes = evidence_annexes + custody_annexes
    if legal_probatory["rows"]:
        annexes.append(legal_matrix_annex)
    annexes.append(manifest_annex)
    return {"count": len(annexes), "items": annexes}


def report_annexes_markdown(report: Report) -> str:
    annexes = report_annexes_payload(report)
    lines = ["## Anexos reales", ""]
    for index, item in enumerate(annexes["items"], start=1):
        lines.append(f"### Anexo {index}: {item['title']}")
        for key, value in item.items():
            if key in {"title"} or value is None or value == "" or value == []:
                continue
            lines.append(f"- {key.replace('_', ' ').title()}: {value}")
        lines.append("")
    return normalize_spanish("\n".join(lines).strip())


def _checklist_recommendation(key: str) -> str:
    return {
        "evidencia_preservada": "Cargar evidencia y registrar que no fue alterada.",
        "hash": "Completar hash SHA-256 para cada evidencia.",
        "custodia": "Registrar al menos una acción de cadena de custodia.",
        "fuente_legal": "Aprobar al menos una norma desde la biblioteca legal.",
        "analista": "Informar el analista/operador interviniente.",
        "revision": "Ejecutar revisión y obtener puntaje mínimo de 80.",
        "metadatos": "Regenerar o guardar el informe para completar metadatos.",
        "conclusion": "Completar conclusión técnico-jurídica sustancial.",
        "anexos": "Incorporar anexos de evidencia, custodia, matriz o manifiesto.",
        "sin_contradicciones_bloqueantes": "Resolver contradicciones críticas antes de exportar final.",
        "exportabilidad_suficiente": "Completar pendientes hasta alcanzar nivel listo para revisión.",
    }.get(key, "Completar requisito pendiente.")


def _report_preview_sections(markdown: str) -> list[dict[str, Any]]:
    sections = []
    for title, content in _markdown_sections_for_preview(markdown):
        clean = normalize_spanish(content).strip()
        if not clean or _section_is_empty_for_preview(clean):
            continue
        sections.append(
            {
                "title": title,
                "word_count": len(clean.split()),
                "excerpt": clean[:700],
                "has_tables": "|" in clean,
            }
        )
    return sections


def _markdown_sections_for_preview(markdown: str) -> list[tuple[str, str]]:
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


def _section_is_empty_for_preview(content: str) -> bool:
    empty_markers = [
        "sin evidencia cargada",
        "sin acciones registradas",
        "sin hallazgos cargados",
        "anexos pendientes",
        "evaluación pendiente",
    ]
    lowered = content.lower()
    return any(marker in lowered for marker in empty_markers) and len(content.split()) < 18


def _preview_warnings(exportability: dict[str, Any], contradictions: dict[str, Any], sections: list[dict[str, Any]]) -> list[str]:
    warnings = []
    if exportability["level"] in {"Borrador técnico", "Informe preliminar"}:
        warnings.append(f"El informe se encuentra en nivel {exportability['level']}; no corresponde tratarlo como versión final.")
    if contradictions["count"]:
        warnings.append("Existen contradicciones legal-probatorias que deben resolverse antes de presentación final.")
    if not any(section["title"].lower() == "resumen ejecutivo" for section in sections):
        warnings.append("Falta resumen ejecutivo visible.")
    if not any("conclus" in section["title"].lower() for section in sections):
        warnings.append("Falta conclusión técnico-jurídica visible.")
    return warnings


def _legal_probatory_matrix_markdown(assessment: dict[str, Any]) -> str:
    rows = assessment["rows"]
    if not rows:
        return "| - | - | - | faltante | sin evidencia | medio | Aprobar normas y vincular evidencia concreta. |"
    return "\n".join(
        "| {norm_reference} | {legal_element} | {evidence} {hash_text} | {element_status} | {probatory_strength} | {contradiction_risk} | {recommended_measure} |".format(
            hash_text=f"SHA-256 {row['evidence_hash']}" if row.get("evidence_hash") else "",
            **row,
        )
        for row in rows
    )


def _legal_sufficiency_markdown(assessment: dict[str, Any]) -> str:
    summary = assessment["summary"]
    return normalize_spanish(
        "\n".join(
            [
                f"- Semaforo de suficiencia legal: **{summary['risk_level']}**.",
                f"- Score de control: **{summary['score']} / 100**.",
                f"- Elementos probados: {summary['proved']}.",
                f"- Elementos debiles o pendientes: {summary['weak']}.",
                f"- Elementos faltantes: {summary['missing']}.",
                f"- Elementos controvertidos: {summary['contested']}.",
                f"- Riesgos altos de contradiccion: {summary['high_risk']}.",
                f"- Impacto en conclusion: {summary['conclusion_mode']}.",
            ]
        )
    )


def _normative_application_method(assessment: dict[str, Any]) -> str:
    summary = assessment["summary"]
    if summary["approved_mappings"] == 0:
        return "No existe encuadre legal aprobado por analista. El informe no debe formular una calificacion juridica cerrada."
    if summary["missing"] or summary["high_risk"]:
        return "La aplicacion normativa debe formularse en modo prudente: existen normas aprobadas, pero hay elementos faltantes, debiles o riesgos de contradiccion que impiden sostener una atribucion o calificacion definitiva."
    if summary["weak"] or summary["contested"]:
        return "La aplicacion normativa cuenta con soporte inicial, aunque requiere corroboracion externa antes de elevar el grado conclusivo."
    return "La aplicacion normativa cuenta con soporte legal-probatorio consistente para una conclusion tecnica fortalecida, siempre sujeta a revision profesional y control jurisdiccional."


def _incident_conclusion_frame(case: Case, assessment: dict[str, Any]) -> str:
    incident = normalize_spanish(case.incident_type or "").lower()
    summary = assessment["summary"]
    mode = summary["conclusion_mode"]
    if "phishing" in incident or "fraude" in incident:
        if mode == "fortalecida":
            return "Conclusión específica por phishing/fraude digital: la evidencia vinculada permite sostener una maniobra compatible con captación engañosa, inducción a error y posible desplazamiento patrimonial, sin confundir esa compatibilidad con atribución penal individual."
        if mode == "insuficiente":
            return "Conclusión específica por phishing/fraude digital: el caso conserva una hipótesis compatible con ardid o engaño, pero faltan elementos para afirmar error, perjuicio, nexo causal o titularidad de cuentas receptoras con suficiencia técnico-jurídica."
        return "Conclusión específica por phishing/fraude digital: la matriz permite sostener una teoría prudente de captación engañosa, sujeta a corroboración de comunicaciones, URL, cuenta receptora, pago, identidad digital y nexo causal."
    if "ransomware" in incident or "extors" in incident:
        return "Conclusión específica por ransomware/extorsión: el análisis debe priorizar prueba de cifrado o bloqueo, nota extorsiva, trazabilidad de wallet o cuenta destino, impacto operativo y preservación de artefactos, sin atribuir autoría por la sola infraestructura utilizada."
    if "acceso" in incident:
        return "Conclusión específica por acceso ilegítimo: el eje probatorio se concentra en logs, permisos, autenticaciones, timestamps, IPs, sesiones y ausencia de autorización; la atribución personal exige corroboración externa adicional."
    if "filtr" in incident or "datos" in incident:
        return "Conclusión específica por filtración de datos: la suficiencia depende de acreditar datos personales o confidenciales afectados, origen de exposición, alcance, titulares involucrados, medidas de seguridad y cadena de custodia de las muestras."
    if "daño" in incident or "dano" in incident:
        return "Conclusión específica por daño informático: la matriz debe demostrar alteración, destrucción, inutilización o afectación de datos, programas o sistemas mediante hashes, imágenes forenses, logs, backups e impacto operativo verificable."
    return "Conclusión específica por incidente digital: la matriz legal-probatoria define el alcance defendible de la conclusión según evidencia preservada, normas aprobadas, elementos faltantes y riesgos de contradicción."


def _procedural_recommendations_markdown(case: Case, assessment: dict[str, Any]) -> str:
    incident = normalize_spanish(case.incident_type or "").lower()
    recommendations: list[str] = []
    rows = assessment["rows"]
    if any(row["element_status"] in {"faltante", "pendiente", "debil"} for row in rows):
        recommendations.append("Incorporar evidencia directa o corroborante para los elementos legales marcados como faltantes, débiles o pendientes.")
    if any(row["contradiction_risk"] in {"alto", "critico"} for row in rows):
        recommendations.append("Resolver contradicciones probatorias antes de cerrar el informe o sostener una atribución.")
    if "phishing" in incident or "fraude" in incident:
        recommendations.extend(
            [
                "Preservar capturas completas del anuncio, perfil, enlace, chat, correo o comunicación engañosa con fecha, hora, URL e identificadores visibles.",
                "Requerir a plataforma, marketplace, red social o proveedor la preservación de cuenta, logs, IPs, cambios de perfil y datos de registración.",
                "Oficiar a entidad financiera, billetera virtual, exchange o procesador de pago para titularidad, movimientos, trazabilidad y cuenta receptora.",
                "Correlacionar comprobantes de pago, conversaciones, timestamps, URLs y respuestas de proveedores para sostener ardid, error, perjuicio y nexo causal.",
            ]
        )
    elif "ransomware" in incident or "extors" in incident:
        recommendations.extend(
            [
                "Preservar nota extorsiva, wallets, direcciones de pago, muestras, hashes, extensiones cifradas y evidencia de indisponibilidad.",
                "Generar imagen forense de sistemas afectados antes de restaurar o ejecutar herramientas de limpieza.",
                "Requerir logs de firewall, EDR, VPN, correo y autenticación para reconstruir vector de ingreso y propagación.",
            ]
        )
    elif "acceso" in incident:
        recommendations.extend(
            [
                "Preservar logs originales de autenticación, sesiones, cambios de contraseña, 2FA, IPs, user agents y permisos.",
                "Solicitar datos de abonado o preservación a proveedores solo cuando exista IP, cuenta o identificador temporalmente correlacionable.",
                "Contrastar actividad del usuario legítimo, dispositivos autorizados y políticas de acceso para descartar falsos positivos.",
            ]
        )
    elif "filtr" in incident or "datos" in incident:
        recommendations.extend(
            [
                "Determinar alcance de datos afectados, categorías, titulares involucrados y fuente exacta de exposición.",
                "Preservar muestras mínimas con hash, evitando reproducir datos sensibles innecesarios.",
                "Relevar medidas de seguridad, permisos, responsables de tratamiento y registros de acceso.",
            ]
        )
    elif "daño" in incident or "dano" in incident:
        recommendations.extend(
            [
                "Comparar hashes, respaldos, imágenes forenses y estado previo/posterior del sistema afectado.",
                "Documentar impacto operativo, indisponibilidad, archivos alterados y trazabilidad de restauración.",
                "Identificar artefactos, scripts, malware o comandos vinculados a la alteración o inutilización.",
            ]
        )
    if not recommendations:
        recommendations.append("Mantener preservación integral, cadena de custodia, hash de evidencia y solicitudes de información a proveedores pertinentes.")
    unique = list(dict.fromkeys(recommendations))
    return normalize_spanish("\n".join(f"- {item}" for item in unique))


def build_matrix_based_conclusion(case: Case) -> str:
    assessment = legal_probatory_assessment(case)
    summary = assessment["summary"]
    attribution = attribution_assessment(case)
    incident_frame = _incident_conclusion_frame(case, assessment)
    if summary["approved_mappings"] == 0:
        return normalize_spanish(
            "No se incorporó un encuadre legal aprobado por analista. En consecuencia, el informe solo puede sostener una descripción técnico-forense preliminar y no una conclusión jurídico-penal estructurada."
        )
    if summary["conclusion_mode"] == "insuficiente":
        return normalize_spanish(
            f"La matriz legal-probatoria registra {summary['missing']} elemento(s) faltante(s), {summary['weak']} elemento(s) débiles o pendientes y {summary['high_risk']} riesgo(s) alto(s) de contradicción. Por ello, la conclusión jurídicamente defendible debe limitarse a afirmar compatibilidad preliminar entre los hechos investigados y las normas aprobadas, sin atribución personal ni calificación definitiva."
        )
    if attribution["sufficient"] and summary["conclusion_mode"] == "fortalecida":
        return normalize_spanish(
            "La matriz legal-probatoria muestra un soporte consistente entre normas aprobadas, evidencia vinculada y elementos legales relevantes. Sumado a los indicadores de atribución técnica disponibles, el caso admite una conclusión técnico-jurídica fortalecida, sin perjuicio de la valoración judicial, la contradicción de partes y la revisión profesional."
        )
    return normalize_spanish(
        f"La matriz legal-probatoria permite sostener una conclusión prudente: existen normas aprobadas y evidencia vinculada, pero el score de suficiencia es {summary['score']} / 100 y todavía deben corroborarse elementos faltantes, débiles o externos antes de avanzar hacia atribución personal o calificación definitiva."
    )


def build_ai_enrichment_markdown(case: Case, legal_recommendations: list[Any], ai_response: str = "") -> str:
    legal_block = _legal_recommendation_markdown(legal_recommendations)
    hypotheses = _default_hypotheses_markdown(case)
    legal_probatory = legal_probatory_assessment(case)
    procedural_recommendations = _procedural_recommendations_markdown(case, legal_probatory)
    evidence_summary = "\n".join(
        f"- Evidencia #{item.id}: {item.description}. Hash: {item.sha256_hash or 'pendiente'}. Integridad: {item.integrity_status}."
        for item in case.evidence[:8]
    ) or "- No hay evidencia suficiente cargada para sostener una conclusion fuerte."
    return normalize_spanish(
        f"""
## Hipótesis y análisis del caso

{hypotheses}

## Evidencia que sostiene o limita la teoría del caso

{evidence_summary}

## Encuadre legal argentino

{legal_block}

## Matriz legal-probatoria aplicada

| Norma | Elemento legal | Evidencia | Estado | Fuerza | Riesgo | Medida recomendada |
| --- | --- | --- | --- | --- | --- | --- |
{_legal_probatory_matrix_markdown(legal_probatory)}

## Semáforo de suficiencia legal

{_legal_sufficiency_markdown(legal_probatory)}

## Conclusión técnico-jurídica

{build_matrix_based_conclusion(case)}

{_incident_conclusion_frame(case, legal_probatory)}

{build_attribution_conclusion(case)}

## Recomendaciones procesales automáticas

{procedural_recommendations}
"""
    )


def _attribution_subject(case: Case) -> str | None:
    for participant in case.participants:
        role = normalize_spanish(participant.participant_type).lower()
        if role in {"sospechoso", "imputado", "atacante", "grupo_atribucion", "grupo organizado"}:
            return participant.display_name
    return None


def attribution_assessment(case: Case) -> dict[str, object]:
    subject = _attribution_subject(case)
    evidence_text = " ".join(
        [
            " ".join(item.description for item in case.evidence),
            " ".join(item.detailed_description for item in case.actions),
            " ".join(item.technical_finding for item in case.findings),
        ]
    ).lower()
    signals = {
        "persona_o_grupo_identificado": bool(subject),
        "ip_vinculada": "ip" in evidence_text or any("ip" in item.evidence_type.lower() for item in case.evidence),
        "logs": "log" in evidence_text or any("log" in item.evidence_type.lower() for item in case.evidence),
        "metadatos_sesion": "sesion" in evidence_text or "session" in evidence_text or "metadato" in evidence_text,
        "artefactos_maliciosos": any(term in evidence_text for term in ["malware", "hash", "exe", "script", "artefacto"]),
        "correlacion_temporal": any(term in evidence_text for term in ["correlacion", "timestamp", "horario", "fecha", "temporal"]),
        "registros_proveedor": any(term in evidence_text for term in ["proveedor", "oficio", "abonado", "telecom", "plataforma"]),
        "trazabilidad_pagos": any(term in evidence_text for term in ["pago", "transferencia", "wallet", "cbu", "alias", "mercado pago", "billetera"]),
        "evidencia_externa": any(term in evidence_text for term in ["secuestro", "dispositivo", "notebook", "pericia", "domicilio"]),
    }
    score = sum(1 for value in signals.values() if value)
    sufficient = bool(subject) and score >= 5 and len(case.evidence) >= 2 and len(case.actions) >= 1
    return {"sufficient": sufficient, "subject": subject, "score": score, "signals": signals}


def _incident_specific_conclusion(case: Case) -> str:
    incident = normalize_spanish(case.incident_type or "").lower()
    description = normalize_spanish(case.description or "")
    if "phishing" in incident or "fraude" in incident:
        return normalize_spanish(
            f"El caso se analiza como una hipotesis preliminar de phishing/fraude digital. El relato disponible ({description or 'sin descripcion ampliada'}) permite orientar la investigacion hacia una posible maniobra de captacion mediante anuncio, ardid o suplantacion. En terminos juridicos argentinos, la figura base a evaluar es el art. 172 del Codigo Penal, porque exige verificar ardid o engano, error de la victima, disposicion patrimonial, perjuicio y nexo causal. Si la maniobra incluyo alteracion, manipulacion o uso de sistemas informaticos para producir el desplazamiento patrimonial, tambien corresponde revisar el art. 173 inc. 16 del Codigo Penal. Si hubo ingreso a cuentas, casillas, perfiles o sistemas sin autorizacion, debe evaluarse el art. 153 bis. Si se captaron, usaron o expusieron datos personales, la Ley 25.326 aporta un plano adicional de proteccion de datos. Si intervino una plataforma, marketplace, banco, fintech o proveedor digital, la Ley 24.240 puede ser relevante para deberes de informacion, seguridad y responsabilidad de consumo. La conclusion defendible no es afirmar autoria personal, sino sostener que la teoria del caso es compatible con una maniobra defraudatoria digital que requiere preservar comunicaciones, anuncios, URLs, identificadores de cuenta, trazabilidad de pagos, logs, titulares de cuentas receptoras y respuestas de proveedores."
        )
    return normalize_spanish(
        "La conclusion debe formularse como teoria preliminar: hechos, evidencia, hallazgos, normas aplicables y evidencia faltante. No corresponde cerrar autoria o responsabilidad definitiva sin preservacion, trazabilidad y revision profesional."
    )


def build_attribution_conclusion(case: Case) -> str:
    assessment = attribution_assessment(case)
    if assessment["sufficient"]:
        subject = assessment["subject"] or "sujeto identificado"
        return normalize_spanish(
            f"""CONCLUSIÓN TÉCNICO-JURÍDICA SOBRE ATRIBUCIÓN DEL CIBERATAQUE

De conformidad con el análisis técnico-forense efectuado sobre la evidencia incorporada al caso, corresponde concluir que existen elementos técnicos suficientes, concordantes y convergentes para atribuir prima facie la ejecución del ataque informático investigado a {subject}.

La atribución no se funda en un único indicador aislado, sino en una pluralidad de evidencias digitales recíprocamente corroboradas, cuya valoración debe considerar registros de acceso, trazabilidad temporal, artefactos técnicos, hashes, indicadores de infraestructura, eventuales registros de proveedor y demás elementos externos disponibles.

Desde el punto de vista jurídico penal argentino, los hechos analizados resultan prima facie compatibles con figuras de acceso ilegítimo, fraude digital, defraudación mediante manipulación informática, daño informático o afectación de datos personales, según el alcance final de la prueba. La calificación definitiva corresponde a la autoridad competente.

En consecuencia, este informe concluye que sí existen elementos técnicos, indiciarios y jurídicamente relevantes que permiten formular una atribución técnica preliminar, sin perjuicio de que dicha atribución conserva naturaleza técnico-pericial y deberá ser valorada jurisdiccionalmente conforme las reglas de la sana crítica racional, la contradicción de partes, la cadena de custodia y el estándar probatorio propio del proceso penal argentino.

{ATTRIBUTION_METHOD_NOTE}"""
        )
    return normalize_spanish(
        f"""CONCLUSIÓN TÉCNICO-JURÍDICA SOBRE IMPOSIBILIDAD DE ATRIBUCIÓN DEL CIBERATAQUE

Del análisis técnico-forense efectuado sobre los registros de acceso, logs del servidor, metadatos de conexión, indicadores de compromiso, direcciones IP, huellas de malware, trazas de red, artefactos de sistema y repositorios de eventos disponibles, corresponde concluir que no se han reunido elementos técnicos suficientes para atribuir de manera concluyente el ciberataque investigado a una persona física, grupo organizado, entidad u organización determinada.

La investigación permitió confirmar la existencia material de un incidente de seguridad. Sin embargo, la información disponible no permite establecer con certeza quién ejecutó la intrusión, quién la ordenó ni qué persona física controlaba efectivamente la infraestructura utilizada.

La sola existencia de una dirección IP, alias no verificado, URL, anuncio, perfil, cuenta digital o infraestructura técnica, sin correlación suficiente con identidad civil, dispositivo físico, credenciales personales, registros de pago, geolocalización, artefactos locales u otros elementos externos, no resulta bastante para sostener una atribución penal individual.

Desde el punto de vista jurídico penal, la materialidad del hecho podría resultar compatible, en abstracto, con figuras tales como estafa, defraudación mediante manipulación informática, acceso ilegítimo, violación de datos personales o infracciones conexas, según la prueba que eventualmente se incorpore. No obstante, una cosa es acreditar la existencia de un incidente informático y otra distinta es atribuirlo penalmente a una persona determinada.

En consecuencia, la evidencia actualmente disponible permite sostener la ocurrencia de un incidente compatible con phishing/fraude digital, pero no permite afirmar con grado suficiente de certeza técnico-jurídica la autoría material o intelectual de una persona física determinada.

Desde la perspectiva procesal, corresponde mantener abierta la línea investigativa, preservar la totalidad de la evidencia digital recolectada, requerir informes ampliatorios a proveedores de conectividad, plataformas, servicios de correo, registradores de dominio, entidades financieras, billeteras virtuales, exchanges o servicios de alojamiento, así como realizar nuevas pericias sobre dispositivos, cuentas o sistemas vinculados que pudieran incorporarse en el futuro.

Por todo lo expuesto, este informe concluye que no se logró determinar la atribución del ciberataque a una persona física, grupo u organización específica, sin perjuicio de la existencia del hecho investigado y de la posibilidad de que futuras medidas probatorias permitan fortalecer, descartar o redireccionar las hipótesis de autoría actualmente consideradas.

{ATTRIBUTION_METHOD_NOTE}"""
    )


def populate_report_sections(report: Report, markdown: str) -> list[ReportSection]:
    sections: list[ReportSection] = []
    for index, title in enumerate(REPORT_SECTIONS, start=1):
        marker = f"## {title}"
        next_content = markdown.split(marker, 1)[1] if marker in markdown else ""
        if "## " in next_content:
            next_content = next_content.split("\n## ", 1)[0]
        sections.append(ReportSection(report=report, order_index=index, title=title, content=next_content.strip()))
    return sections


def snapshot_report(report: Report, user: str, summary: str) -> ReportVersion:
    return ReportVersion(
        report=report,
        version_number=report.version,
        user=user,
        change_summary=summary,
        review_score=report.review_score,
        markdown_snapshot=report.markdown_content,
    )


def _incident_legal_basis(incident_type: str) -> list[str]:
    incident = incident_type.lower()
    basis = [
        "Código Penal argentino: posible relevancia penal preliminar según conducta, dolo, perjuicio y medios empleados. Fuente pendiente de verificación.",
        "Ley 26.388: marco argentino de delitos informáticos incorporado al Código Penal. Fuente pendiente de verificación.",
        "Reglas procesales sobre prueba digital y cadena de custodia aplicables según jurisdicción. Fuente pendiente de verificación.",
    ]
    if any(term in incident for term in ["phishing", "fraude", "cripto", "transferencia", "suplantación"]):
        basis.append("Fraude informático o maniobra defraudatoria digital: corresponde analizar ardid, error, disposición patrimonial y perjuicio económico. Fuente pendiente de verificación.")
    if any(term in incident for term in ["acceso", "ransomware", "daño informático", "filtración"]):
        basis.append("Acceso no autorizado, afectación de sistemas, datos o disponibilidad: requiere vincular logs, hashes, trazabilidad y preservación de evidencia. Fuente pendiente de verificación.")
    if any(term in incident for term in ["datos", "filtración", "identidad"]):
        basis.append("Ley 25.326 de Protección de Datos Personales: analizar tratamiento, exposición, deberes de seguridad y potencial afectación de titulares. Fuente pendiente de verificación.")
    if any(term in incident for term in ["consumidor", "banco", "fintech", "exchange", "plataforma", "cripto"]):
        basis.append("Ley 24.240 de Defensa del Consumidor: revisar relación de consumo, deber de seguridad, información y trato digno si intervienen proveedores digitales. Fuente pendiente de verificación.")
    if any(term in incident for term in ["cripto", "blockchain", "wallet", "transferencia"]):
        basis.append("Blockchain y criptoactivos: la trazabilidad técnica puede aportar compatibilidad económica, pero no acredita por sí sola identidad personal del autor. Fuente pendiente de verificación.")
    if any(term in incident for term in ["deepfake", "ia"]):
        basis.append("Engaño habilitado por IA/deepfake: analizar autenticidad, manipulación, inducción a error, daño y límites técnicos de detección. Fuente pendiente de verificación.")
    return basis


def polish_report_markdown(report: Report) -> str:
    case = report.case
    markdown = report.markdown_content or ""
    replacements = {
        "queda probado": "la evidencia disponible permite sostener preliminarmente",
        "sin dudas": "con el alcance y limitaciones indicadas",
        "el atacante fue": "el acceso o conducta analizada resulta compatible con",
        "demuestra que": "resulta compatible con",
        "fue culpable": "podría tener relevancia jurídica, sujeto a validación profesional",
    }
    polished = markdown
    for source, target in replacements.items():
        polished = polished.replace(source, target).replace(source.capitalize(), target.capitalize())

    evidence_count = len(case.evidence)
    finding_count = len(case.findings)
    damage_total = sum(item.amount for item in case.damage_items)
    legal_basis = "\n".join(f"- {item}" for item in _incident_legal_basis(case.incident_type))
    legal_loaded = "\n".join(
        f"- {mapping.legal_area}: {mapping.norm_reference}. {mapping.analysis}. Estado: {mapping.verification_status}."
        for mapping in case.legal_mappings
    ) or "- No hay fuentes legales manuales cargadas. Toda cita queda como fuente pendiente de verificación."

    automatic_block = f"""
## Encuadre automático IA para revisión humana

### Tipo de cibercrimen analizado

El caso se encuadra preliminarmente como **{case.incident_type}**. Esta clasificación se justifica por la descripción del caso, los datos técnicos cargados, la evidencia preservada y los hallazgos registrados. Al momento de esta revisión existen {evidence_count} evidencias y {finding_count} hallazgos vinculados al caso.

### Justificación técnico-jurídica

La línea argumental defendible no salta de dato técnico a conclusión jurídica. Primero identifica datos técnicos, luego evidencia preservada, después hallazgos verificables, hipótesis investigativas y finalmente conclusiones preliminares. Con ese alcance, la evidencia resulta compatible con un incidente digital que podría tener relevancia penal, civil, probatoria, económica y, según el caso, de consumo o protección de datos personales.

### Normativa argentina orientativa

{legal_basis}

### Fuentes legales cargadas manualmente

{legal_loaded}

### Enfoque para competencia o exposición académica

Para una competencia, jurado o audiencia simulada, la teoría del caso debe presentarse así: el incidente se describe de forma cronológica; la evidencia clave se muestra con su hash o estado de integridad; los hallazgos se expresan en lenguaje probabilístico; las hipótesis alternativas se reconocen; el daño económico estimado se informa como **{damage_total:.2f} ARS** sujeto a fórmula, fuente y validación; y la conclusión se formula como jurídicamente defendible, no como atribución penal definitiva.

### Advertencia de no invención

Este encuadre automático no inventa jurisprudencia, doctrina ni citas. Cuando no hay fuente cargada o verificada, se conserva la leyenda **Fuente pendiente de verificación**.
"""

    marker = "## Encuadre automático IA para revisión humana"
    if marker in polished:
        polished = polished.split(marker)[0].rstrip() + "\n\n" + automatic_block.strip() + "\n"
    else:
        polished = polished.rstrip() + "\n\n" + automatic_block.strip() + "\n"

    return normalize_spanish(polished)
