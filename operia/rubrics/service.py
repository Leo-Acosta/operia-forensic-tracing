import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from operia.cases.models import Case
from operia.legal_report.services.report_service import legal_probatory_assessment, report_annexes_payload
from operia.reports.models import Report
from operia.rubrics.models import RubricEvaluation

RUBRIC_KEY = "written_legal_evidence_report_2026"
RUBRIC_TITLE = "Written Legal Evidence Report 2026"


@dataclass(frozen=True)
class SectionDefinition:
    key: str
    label: str
    weight: int
    criteria: tuple[str, ...]
    expected_components: tuple[str, ...]
    minimum_fields: tuple[str, ...]


RUBRIC_SECTIONS = (
    SectionDefinition(
        "A",
        "Technical Approach & Investigative Techniques Used",
        3,
        (
            "Describe técnicas investigativas concretas.",
            "Identify tools, commands, procedures or analysis methods used.",
            "Connect techniques to observed technical findings.",
        ),
        ("técnicas", "herramientas", "hallazgos técnicos", "limitaciones"),
        ("finding.tools_used", "evidence.tool_used", "custody.command_or_procedure"),
    ),
    SectionDefinition(
        "B",
        "Evidence Identification, Categorization & Handling",
        3,
        (
            "Identify and categorize evidence.",
            "Show hash/integrity controls.",
            "Document chain of custody and handling.",
        ),
        ("evidencia identificada", "categoría", "hash", "custodia", "integridad"),
        ("evidence.evidence_type", "evidence.sha256_hash", "custody.action_type"),
    ),
    SectionDefinition(
        "C",
        "Legal Authority & Investigative Requests",
        4,
        (
            "Use only registered legal authorities.",
            "Document legal mappings and probatory limits.",
            "Identify investigative requests, authorizations or legal next steps.",
        ),
        ("normas registradas", "mapeo legal", "matriz legal-probatoria", "solicitudes/autorizaciones"),
        ("legal_mapping.norm_reference", "legal_mapping.decision_status", "custody.legal_observations"),
    ),
    SectionDefinition(
        "D",
        "Summary Analysis of Evidence & Investigative Findings",
        10,
        (
            "Summarize evidence and investigative findings.",
            "Connect findings, hypotheses, conclusion and limitations.",
            "Include final investigative summary and annexes where available.",
        ),
        ("hallazgos", "análisis", "conclusión", "resumen investigativo final", "anexos", "revisión"),
        ("finding.technical_finding", "report.markdown_content", "report.review_score"),
    ),
)


def rubric_definition() -> dict[str, Any]:
    return {
        "key": RUBRIC_KEY,
        "title": RUBRIC_TITLE,
        "max_score": sum(section.weight for section in RUBRIC_SECTIONS),
        "sections": [
            {
                "key": section.key,
                "label": section.label,
                "weight": section.weight,
                "criteria": list(section.criteria),
                "expected_components": list(section.expected_components),
                "minimum_fields": list(section.minimum_fields),
                "status": "incompleto",
                "estimated_score": 0,
                "max_score": section.weight,
                "completion_ratio": 0,
                "missing": list(section.expected_components),
                "recommendations": [],
                "evidence": {},
            }
            for section in RUBRIC_SECTIONS
        ],
    }


def list_rubrics() -> list[dict[str, Any]]:
    definition = rubric_definition()
    return [
        {
            "key": definition["key"],
            "title": definition["title"],
            "max_score": definition["max_score"],
            "sections": [
                {"key": item["key"], "label": item["label"], "weight": item["weight"]}
                for item in definition["sections"]
            ],
        }
    ]


def _status_from_ratio(ratio: float) -> str:
    if ratio >= 0.9:
        return "completo"
    if ratio >= 0.45:
        return "parcial"
    return "incompleto"


def _section_result(section: SectionDefinition, checks: list[tuple[str, bool]], recommendations: list[str], evidence: dict[str, Any]) -> dict[str, Any]:
    passed = [label for label, ok in checks if ok]
    missing = [label for label, ok in checks if not ok]
    ratio = len(passed) / len(checks) if checks else 0
    return {
        "key": section.key,
        "label": section.label,
        "weight": section.weight,
        "criteria": list(section.criteria),
        "expected_components": list(section.expected_components),
        "minimum_fields": list(section.minimum_fields),
        "status": _status_from_ratio(ratio),
        "estimated_score": round(section.weight * ratio),
        "max_score": section.weight,
        "completion_ratio": round(ratio, 2),
        "missing": missing,
        "recommendations": recommendations if missing else ["Mantener consistencia entre evidencia, análisis y conclusiones."],
        "evidence": evidence | {"passed": passed},
    }


def _latest_report(case: Case) -> Report | None:
    return sorted(case.reports, key=lambda item: item.updated_at, reverse=True)[0] if case.reports else None


def evaluate_case_rubric(case: Case) -> dict[str, Any]:
    report = _latest_report(case)
    report_text = (report.markdown_content or "").lower() if report else ""
    approved_mappings = [item for item in case.legal_mappings if getattr(item, "decision_status", "") == "aprobado"]
    legal_probatory = legal_probatory_assessment(case)
    annexes = report_annexes_payload(report, legal_probatory) if report else {"count": 0, "items": []}

    hashed_evidence = [item for item in case.evidence if item.sha256_hash]
    evidence_with_tools = [item for item in case.evidence if item.tool_used or item.preservation_method]
    custody_with_tools = [item for item in case.actions if item.tool_used or item.command_or_procedure]
    findings_with_tools = [item for item in case.findings if item.tools_used or item.technical_finding]
    legal_requests = [
        item
        for item in case.actions
        if any(token in " ".join([item.legal_observations or "", item.detailed_description or "", item.command_or_procedure or ""]).lower() for token in ("oficio", "solicitud", "autoriz", "requer", "orden"))
    ]

    sections = [
        _section_result(
            RUBRIC_SECTIONS[0],
            [
                ("Técnica o procedimiento documentado", bool(custody_with_tools or findings_with_tools or evidence_with_tools)),
                ("Herramienta utilizada registrada", bool(evidence_with_tools or custody_with_tools or any(item.tools_used for item in case.findings))),
                ("Hallazgos técnicos vinculados", bool(case.findings or "hallazgo" in report_text or "análisis técnico" in report_text)),
            ],
            [
                "Registrar herramienta, comando o procedimiento usado en evidencia, custodia o hallazgo.",
                "Agregar hallazgos técnicos con limitaciones y soporte.",
            ],
            {
                "tools_on_evidence": len(evidence_with_tools),
                "tools_on_custody": len(custody_with_tools),
                "technical_findings": len(case.findings),
            },
        ),
        _section_result(
            RUBRIC_SECTIONS[1],
            [
                ("Evidencia cargada", bool(case.evidence)),
                ("Hash SHA-256 calculado", bool(hashed_evidence)),
                ("Custodia registrada", bool(case.actions)),
                ("Categoría e integridad de evidencia", bool(case.evidence and all(item.evidence_type for item in case.evidence))),
            ],
            [
                "Cargar evidencia con descripción y categoría.",
                "Calcular o registrar SHA-256 por evidencia.",
                "Registrar acciones de cadena de custodia.",
            ],
            {"evidence_count": len(case.evidence), "hashed_evidence": len(hashed_evidence), "custody_actions": len(case.actions)},
        ),
        _section_result(
            RUBRIC_SECTIONS[2],
            [
                ("Justificación legal registrada", bool(approved_mappings)),
                ("Matriz legal-probatoria disponible", bool(legal_probatory["rows"])),
                ("Evidencia vinculada a norma", any(row.get("evidence_id") for row in legal_probatory["rows"])),
                ("Solicitudes legales o autorizaciones documentadas", bool(legal_requests or "oficio" in report_text or "autoriz" in report_text or "solicitud" in report_text)),
            ],
            [
                "Aprobar al menos un mapeo legal desde la biblioteca registrada.",
                "Vincular evidencia concreta a los elementos legales.",
                "Documentar solicitudes, autorizaciones u oficios necesarios.",
            ],
            {
                "approved_mappings": len(approved_mappings),
                "legal_matrix_rows": len(legal_probatory["rows"]),
                "legal_requests": len(legal_requests),
            },
        ),
        _section_result(
            RUBRIC_SECTIONS[3],
            [
                ("Hallazgos técnicos analizados", bool(case.findings or "hallazgo" in report_text)),
                ("Conclusión incluida", bool("conclusión" in report_text or "conclusion" in report_text)),
                ("Informe generado", bool(report)),
                ("Informe revisado", bool(report and report.review_score > 0)),
                ("Anexos incorporados o identificados", bool(annexes.get("count", 0) or "anexo" in report_text)),
                ("Final Investigative Summary incluido", bool("resumen ejecutivo" in report_text or "síntesis aplicada" in report_text or "sintesis aplicada" in report_text)),
            ],
            [
                "Agregar hallazgos y análisis resumido.",
                "Generar o actualizar informe con conclusión técnica-jurídica.",
                "Ejecutar revisión del informe y refrescar anexos.",
                "Incluir Final Investigative Summary en el resumen/conclusión.",
            ],
            {
                "findings": len(case.findings),
                "reports": len(case.reports),
                "review_score": report.review_score if report else 0,
                "annexes": annexes.get("count", 0),
            },
        ),
    ]
    total = sum(section["estimated_score"] for section in sections)
    max_score = sum(section.weight for section in RUBRIC_SECTIONS)
    percentage = round((total / max_score) * 100) if max_score else 0
    status = "completo" if percentage >= 85 else "parcial" if percentage >= 45 else "incompleto"
    missing = [f"{section['key']}. {item}" for section in sections for item in section["missing"]]
    recommendations = list(dict.fromkeys([item for section in sections for item in section["recommendations"]]))
    summary = (
        f"Evaluación {RUBRIC_TITLE}: {total}/{max_score} puntos ({percentage}%). "
        f"Estado {status}. La lectura es operativa y no reemplaza revisión profesional."
    )
    return {
        "rubric_key": RUBRIC_KEY,
        "rubric_title": RUBRIC_TITLE,
        "total_score": total,
        "max_score": max_score,
        "percentage": percentage,
        "status": status,
        "sections": sections,
        "missing": missing,
        "recommendations": recommendations,
        "summary": summary,
    }


def persist_case_evaluation(db: Session, case: Case, evaluated_by: str = "OPERIA") -> RubricEvaluation:
    result = evaluate_case_rubric(case)
    item = RubricEvaluation(
        case_id=case.id,
        organization_id=case.organization_id,
        rubric_key=result["rubric_key"],
        rubric_title=result["rubric_title"],
        total_score=result["total_score"],
        max_score=result["max_score"],
        percentage=result["percentage"],
        status=result["status"],
        sections_json=json.dumps(result["sections"], ensure_ascii=False),
        missing_json=json.dumps(result["missing"], ensure_ascii=False),
        recommendations_json=json.dumps(result["recommendations"], ensure_ascii=False),
        summary=result["summary"],
        evaluated_by=evaluated_by,
    )
    db.add(item)
    db.flush()
    return item


def latest_case_evaluation(db: Session, case_id: int) -> RubricEvaluation | None:
    return (
        db.query(RubricEvaluation)
        .filter_by(case_id=case_id, rubric_key=RUBRIC_KEY)
        .order_by(desc(RubricEvaluation.created_at), desc(RubricEvaluation.id))
        .first()
    )


def evaluation_payload(item: RubricEvaluation) -> dict[str, Any]:
    return {
        "id": item.id,
        "case_id": item.case_id,
        "rubric_key": item.rubric_key,
        "rubric_title": item.rubric_title,
        "total_score": item.total_score,
        "max_score": item.max_score,
        "percentage": item.percentage,
        "status": item.status,
        "sections": json.loads(item.sections_json or "[]"),
        "missing": json.loads(item.missing_json or "[]"),
        "recommendations": json.loads(item.recommendations_json or "[]"),
        "summary": item.summary,
        "evaluated_by": item.evaluated_by,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def rubric_markdown(item: RubricEvaluation) -> str:
    payload = evaluation_payload(item)
    lines = [
        "## Cumplimiento de rúbrica del informe",
        "",
        f"- Rúbrica: {payload['rubric_title']}.",
        f"- Score: **{payload['total_score']} / {payload['max_score']}** ({payload['percentage']}%).",
        f"- Estado: **{payload['status']}**.",
        f"- Observación profesional: {payload['summary']}",
        "",
        "| Sección | Estado | Puntaje | Observaciones |",
        "| --- | --- | ---: | --- |",
    ]
    for section in payload["sections"]:
        observation = "; ".join(section.get("missing") or section.get("recommendations") or ["Sin observaciones críticas"])
        lines.append(f"| {section['key']}. {section['label']} | {section['status']} | {section['estimated_score']} / {section['max_score']} | {observation} |")
    return "\n".join(lines)
