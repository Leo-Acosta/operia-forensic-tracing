from hashlib import sha256
from typing import Any

from operia.cases.models import Case
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
    "Hallazgos principales",
    "Hipótesis investigativas",
    "Evaluación de hipótesis alternativas",
    "Conclusiones técnicas",
    "Encuadre jurídico argentino",
    "Matriz legal-probatoria aplicada",
    "SemÃ¡foro de suficiencia legal",
    "Responsabilidad penal preliminar",
    "Responsabilidad civil preliminar",
    "Protección de datos personales",
    "Defensa del consumidor",
    "Cuantificación económica del daño",
    "Conclusión jurídicamente defendible",
    "Recomendaciones",
    "Recomendaciones procesales automÃ¡ticas",
    "Anexos",
    "Glosario técnico",
    "Preguntas y respuestas para testimonio experto",
]


def build_integral_markdown(case: Case, legal_recommendations: list[Any] | None = None) -> str:
    total_damage = sum(item.amount for item in case.damage_items)
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
    procedural_recommendations = _procedural_recommendations_markdown(case, legal_probatory)
    exportability = report_exportability_assessment(case, legal_probatory)
    executive_summary = build_smart_executive_summary(case, legal_probatory, exportability)
    exportability_lines = exportability_markdown(exportability)
    rubric_lines = ""
    if getattr(case, "rubric_evaluations", None):
        from operia.rubrics.service import rubric_markdown

        latest_rubric = sorted(case.rubric_evaluations, key=lambda item: item.created_at, reverse=True)[0]
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

## Resumen ejecutivo

{executive_summary}

### Nivel de exportabilidad del informe

{exportability_lines}

## Descripción del incidente

{description_text}

## Evidencia recibida

{evidence_lines}

## Registro de cadena de custodia

{custody_lines}

## Línea de tiempo de eventos

{custody_lines}

## Análisis técnico-forense

### Deepfake / IA
Evaluación pendiente según datos cargados.

### IoT / dispositivos conectados
Evaluación pendiente según datos cargados.

### Blockchain / criptomonedas
Evaluación pendiente según datos cargados.

### Logs, IPs, dominios y red
Evaluación pendiente según datos cargados.

### OSINT y fuentes abiertas
Evaluación pendiente según datos cargados.

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

## Matriz legal-probatoria aplicada

| Norma | Elemento legal | Evidencia | Estado | Fuerza | Riesgo | Medida recomendada |
| --- | --- | --- | --- | --- | --- | --- |
{legal_probatory_lines}

## SemÃ¡foro de suficiencia legal

{legal_sufficiency_lines}

### MÃ©todo de aplicaciÃ³n normativa

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

## Recomendaciones procesales automÃ¡ticas

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


def _default_hypotheses_markdown(case: Case) -> str:
    evidence_count = len(case.evidence)
    custody_count = len(case.actions)
    incident = normalize_spanish(case.incident_type or "incidente digital")
    if evidence_count <= 1 and not case.findings:
        return normalize_spanish(
            f"- Hipótesis principal: el hecho investigado resulta compatible con una maniobra de {incident} mediante captación engañosa de la víctima a través de anuncio, enlace, perfil o comunicación falsa, orientada a obtener datos, credenciales o desplazamiento patrimonial. Con el estado actual de la evidencia no corresponde formular hipótesis alternativas autónomas."
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
    links = [link for link in getattr(mapping, "evidence_links", []) if getattr(link, "evidence", None)]
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
    approved_mappings = [
        mapping for mapping in case.legal_mappings if getattr(mapping, "decision_status", "sugerido") != "descartado"
    ]
    rows: list[dict[str, Any]] = []
    missing = weak = proved = contested = high_risk = 0
    for mapping in approved_mappings:
        links = list(getattr(mapping, "evidence_links", []) or [])
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

## SemÃ¡foro de suficiencia legal

{_legal_sufficiency_markdown(legal_probatory)}

## Conclusión técnico-jurídica

{build_matrix_based_conclusion(case)}

{_incident_conclusion_frame(case, legal_probatory)}

{build_attribution_conclusion(case)}

## Recomendaciones procesales automÃ¡ticas

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

