from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from operia.cases.models import Case
from operia.core.database import get_db
from operia.evidence.models import ChainOfCustodyAction
from operia.legal_knowledge.models import LegalMapping
from operia.legal_knowledge.schemas import LegalMappingRead
from operia.reports.schemas import CaseEvaluationResult
from operia.legal_report.services.ai_case_evaluation_service import evaluate_report_case
from operia.legal_report.services.ai_legal_service import apply_automatic_legal_mappings, generate_automatic_legal_analysis
from operia.legal_report.services.consistency_service import enrich_case
from operia.reports.models import Report, ReportSection, ReportVersion
from operia.shared.crud import get_or_404

router = APIRouter()


@router.get("/")
def status() -> dict[str, object]:
    return {
        "module": "Legal Report",
        "status": "canonical",
        "description": "Legal analysis, legal review, normative mapping, and juridical report assistance.",
        "legacy_routes": "/api/legal-report",
    }


@router.post("/cases/{case_id}/analysis")
def automatic_legal_analysis(case_id: int, apply: bool = False, db: Session = Depends(get_db)):
    case = get_or_404(db, Case, case_id)
    if not apply:
        return generate_automatic_legal_analysis(case)
    created, analysis = apply_automatic_legal_mappings(case)
    for item in created:
        db.add(item)
    db.add(
        ChainOfCustodyAction(
            case_id=case.id,
            action_type="revision juridica",
            detailed_description=f"Analisis legal asistido genero {len(created)} encuadre(s) preliminar(es).",
            tool_used="OPERIA Legal",
            legal_observations=analysis["defensible_conclusion"],
            status="requiere revision humana",
        )
    )
    db.commit()
    analysis["created_mappings"] = len(created)
    return analysis


@router.get("/cases/{case_id}/mappings", response_model=list[LegalMappingRead])
def list_legal_mappings(case_id: int, db: Session = Depends(get_db)):
    return db.query(LegalMapping).filter_by(case_id=case_id).order_by(LegalMapping.created_at.desc()).all()


@router.post("/reports/{report_id}/evaluate-case", response_model=CaseEvaluationResult)
def evaluate_case_from_report(report_id: int, apply: bool = True, db: Session = Depends(get_db)):
    report = get_or_404(db, Report, report_id)
    evaluation = evaluate_report_case(report)
    if apply:
        marker = "## Evaluacion integral IA del caso"
        block = "\n".join(
            [
                marker,
                "",
                evaluation["defensible_conclusion"],
                "",
                "### Justificacion legal",
                evaluation["legal_justification"],
            ]
        )
        if marker in report.markdown_content:
            report.markdown_content = report.markdown_content.split(marker, 1)[0].rstrip() + "\n\n" + block.strip() + "\n"
        else:
            report.markdown_content = (report.markdown_content or "").rstrip() + "\n\n" + block.strip() + "\n"
        report.review_score = evaluation["overall_score"]
        report.status = "en revision"
        report.versions.append(
            ReportVersion(
                report=report,
                version_number=report.version,
                user="OPERIA Legal",
                change_summary="Evaluacion juridica asistida del caso desde informe",
                review_score=evaluation["overall_score"],
                markdown_snapshot=report.markdown_content,
            )
        )
        if not any(section.title == "Evaluacion integral IA del caso" for section in report.sections):
            last_order = max([section.order_index for section in report.sections] or [0])
            report.sections.append(
                ReportSection(
                    report=report,
                    order_index=last_order + 1,
                    title="Evaluacion integral IA del caso",
                    content=evaluation["defensible_conclusion"],
                    section_type="legal_ai",
                )
            )
        db.add(
            ChainOfCustodyAction(
                case_id=report.case_id,
                action_type="revision juridica",
                detailed_description=f"OPERIA Legal evaluo el informe #{report.id}. Score: {evaluation['overall_score']}/100.",
                tool_used="OPERIA Legal",
                result_obtained=evaluation["defensible_conclusion"],
                legal_observations=evaluation["legal_justification"],
                status="requiere revision humana",
            )
        )
        db.commit()
    return evaluation


@router.post("/cases/{case_id}/enrich-consistency")
def enrich_case_consistency(case_id: int, apply: bool = True, db: Session = Depends(get_db)):
    case = get_or_404(db, Case, case_id)
    result = enrich_case(case, apply=apply)
    if apply:
        db.commit()
    return result
