from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from operia.audit.service import write_audit
from operia.cases.models import Case
from operia.core.database import get_db
from operia.identity.dependencies import CurrentUser, get_optional_user
from operia.reports.schemas import ReportRead, ReportUpdate, ReviewResult
from operia.exports.service import export_docx, export_html, export_markdown, export_pdf
from operia.legal_report.services.report_service import build_integral_markdown, populate_report_sections, snapshot_report
from operia.legal_report.services.review_service import review_report
from operia.reports.models import Report, ReportReview, ReportSection, ReportVersion
from operia.shared.crud import get_or_404

router = APIRouter()


@router.get("/")
def status() -> dict[str, object]:
    return {
        "module": "Reports",
        "status": "canonical",
        "description": "Canonical reports, sections, versions, reviews, and presentation source material.",
    }


@router.post("/case/{case_id}/generate", response_model=ReportRead)
def generate_report(
    case_id: int,
    author: str = "",
    db: Session = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_optional_user),
):
    case = get_or_404(db, Case, case_id)
    markdown = build_integral_markdown(case)
    report = Report(case=case, title=f"Informe integral - {case.title}", author=author, markdown_content=markdown)
    report.organization_id = current_user.organization_id if current_user and current_user.organization_id else case.organization_id
    db.add(report)
    db.flush()
    report.sections = populate_report_sections(report, markdown)
    report.versions.append(snapshot_report(report, author, "Generacion inicial automatica"))
    write_audit(db, "generate_report", "reports", current_user, case_id=case_id, entity_type="report", entity_id=str(report.id), details=report.title)
    db.commit()
    db.refresh(report)
    return report


@router.get("/case/{case_id}", response_model=list[ReportRead])
def list_case_reports(case_id: int, db: Session = Depends(get_db)):
    return db.query(Report).filter_by(case_id=case_id).order_by(desc(Report.updated_at)).all()


@router.get("/{report_id}", response_model=ReportRead)
def read_report(report_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Report, report_id)


@router.put("/{report_id}", response_model=ReportRead)
def update_report(
    report_id: int,
    payload: ReportUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_optional_user),
):
    report = get_or_404(db, Report, report_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(report, key, value)
    db.add(snapshot_report(report, payload.author or report.author, "Edicion manual del informe"))
    write_audit(db, "update_report", "reports", current_user, case_id=report.case_id, entity_type="report", entity_id=str(report.id), details=report.title)
    db.commit()
    db.refresh(report)
    return report


@router.get("/{report_id}/versions")
def list_report_versions(report_id: int, db: Session = Depends(get_db)):
    return db.query(ReportVersion).filter_by(report_id=report_id).order_by(desc(ReportVersion.created_at)).all()


@router.get("/{report_id}/sections")
def list_report_sections(report_id: int, db: Session = Depends(get_db)):
    get_or_404(db, Report, report_id)
    return db.query(ReportSection).filter_by(report_id=report_id).order_by(ReportSection.order_index).all()


@router.post("/{report_id}/review", response_model=ReviewResult)
def review_report_endpoint(report_id: int, db: Session = Depends(get_db)):
    report = get_or_404(db, Report, report_id)
    result = review_report(report, report.case)
    report.review_score = result["score"]
    db.add(
        ReportReview(
            report_id=report.id,
            score=result["score"],
            status=result["status"],
            critical_errors="\n".join(result["critical_errors"]),
            warnings="\n".join(result["warnings"]),
            suggestions="\n".join(result["suggestions"]),
            incomplete_sections="\n".join(result["incomplete_sections"]),
            unsupported_conclusions="\n".join(result["unsupported_conclusions"]),
        )
    )
    db.commit()
    return result


@router.get("/{report_id}/export/{fmt}")
def export_report(report_id: int, fmt: str, db: Session = Depends(get_db)):
    report = get_or_404(db, Report, report_id)
    exporters = {"markdown": export_markdown, "html": export_html, "docx": export_docx, "pdf": export_pdf}
    if fmt not in exporters:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Formato no soportado")
    path = exporters[fmt](report)
    return FileResponse(path, filename=path.name)
