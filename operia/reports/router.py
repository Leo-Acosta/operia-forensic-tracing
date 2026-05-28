from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from operia.audit.service import write_audit
from operia.cases.models import Case
from operia.core.database import get_db
from operia.identity.dependencies import CurrentUser, get_optional_user
from operia.reports.schemas import ExecutiveSummaryUpdate, ReportRead, ReportUpdate, ReportVersionTransition, ReviewResult
from operia.exports.service import export_docx, export_html, export_markdown, export_pdf
from operia.ai_assistant.ollama_client import OllamaUnavailable, generate_with_ollama
from operia.ai_assistant.prompts import build_forensic_prompt
from operia.ai_assistant.service import case_context_for_prompt, legal_context_for_prompt
from operia.legal_knowledge.service import ensure_legal_articles, recommend_articles_for_incident
from operia.legal_report.services.report_service import (
    build_ai_enrichment_markdown,
    build_integral_markdown,
    legal_contradiction_assessment,
    populate_report_sections,
    replace_executive_summary,
    final_pericial_checklist,
    report_annexes_markdown,
    report_annexes_payload,
    report_preview_payload,
    report_exportability_assessment,
    legal_probatory_assessment,
    snapshot_report,
)
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
    ensure_legal_articles(db)
    incident_text = " ".join([case.incident_type or "", case.description or "", case.general_observations or ""])
    legal_recommendations = recommend_articles_for_incident(db, incident_text, limit=8)
    markdown = build_integral_markdown(case, legal_recommendations=legal_recommendations)
    report = Report(
        case=case,
        title=f"Informe integral - {case.title}",
        author=author,
        markdown_content=markdown,
        status="caso_en_proceso_de_inicio_de_investigacion",
    )
    report.organization_id = current_user.organization_id if current_user and current_user.organization_id else case.organization_id
    db.add(report)
    db.flush()
    report.sections = populate_report_sections(report, markdown)
    report.versions.append(snapshot_report(report, author, "Generacion inicial automatica"))
    write_audit(db, "generate_report", "reports", current_user, case_id=case_id, entity_type="report", entity_id=str(report.id), details=report.title)
    db.commit()
    db.refresh(report)
    return report


@router.post("/{report_id}/ai-enrich", response_model=ReportRead)
def enrich_report_with_ai(
    report_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_optional_user),
):
    report = get_or_404(db, Report, report_id)
    case = report.case
    model_name = str(payload.get("model_name") or "mistral")
    user_prompt = str(payload.get("prompt") or "Enriquecer informe con hipotesis, conclusiones prudentes y fundamentacion legal argentina.")
    ensure_legal_articles(db)
    incident_text = " ".join(
        [
            case.incident_type or "",
            case.description or "",
            case.general_observations or "",
            " ".join(item.description for item in case.evidence[:8]),
            " ".join(item.title for item in case.findings[:8]),
        ]
    )
    legal_recommendations = recommend_articles_for_incident(db, incident_text, limit=8)
    legal_context = legal_context_for_prompt(db, incident_text)
    case_context = case_context_for_prompt(case)
    guarded_prompt = build_forensic_prompt(
        f"{user_prompt}\n\nObjetivo: devolver hipotesis reales, conclusiones profundas pero prudentes, y fundamentacion legal argentina citando solo fuentes registradas.",
        legal_context=legal_context,
        case_context=case_context,
    )
    status = "completed"
    try:
        ai_response = generate_with_ollama(guarded_prompt, model=model_name)
    except OllamaUnavailable as exc:
        ai_response = str(exc)
        status = "ollama_unavailable_fallback"

    enrichment = build_ai_enrichment_markdown(case, legal_recommendations, ai_response)
    marker = "## Hipótesis y análisis del caso"
    current_markdown = report.markdown_content or ""
    if marker in current_markdown:
        report.markdown_content = current_markdown.split(marker, 1)[0].rstrip() + "\n\n" + enrichment.strip() + "\n"
    else:
        report.markdown_content = (report.markdown_content or "").rstrip() + "\n\n" + enrichment.strip() + "\n"
    report.status = "en_proceso_investigativo"
    report.observations = "Informe ampliado con análisis técnico-jurídico y motor de atribución."
    report.sections = populate_report_sections(report, report.markdown_content)
    report.versions.append(snapshot_report(report, current_user.email if current_user else "Analista", f"Ampliación técnico-jurídica: {status}"))
    write_audit(db, "enrich_report", "reports", current_user, case_id=case.id, entity_type="report", entity_id=str(report.id), details=status)
    db.commit()
    db.refresh(report)
    return report


@router.get("/case/{case_id}", response_model=list[ReportRead])
def list_case_reports(case_id: int, db: Session = Depends(get_db)):
    return db.query(Report).filter_by(case_id=case_id).order_by(desc(Report.updated_at)).all()


@router.get("/{report_id}", response_model=ReportRead)
def read_report(report_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Report, report_id)


@router.get("/{report_id}/preview")
def preview_report(report_id: int, db: Session = Depends(get_db)):
    report = get_or_404(db, Report, report_id)
    return report_preview_payload(report)


@router.get("/{report_id}/contradictions")
def report_contradictions(report_id: int, db: Session = Depends(get_db)):
    report = get_or_404(db, Report, report_id)
    return legal_contradiction_assessment(report.case)


@router.get("/{report_id}/exportability")
def report_exportability(report_id: int, db: Session = Depends(get_db)):
    report = get_or_404(db, Report, report_id)
    legal_probatory = legal_probatory_assessment(report.case)
    exportability = report_exportability_assessment(report.case, legal_probatory, report=report)
    contradictions = legal_contradiction_assessment(report.case)
    return {
        "report_id": report.id,
        "exportability": exportability,
        "contradictions": contradictions,
        "can_export_final": exportability["level"] in {"Listo para revisión", "Apto para presentación"}
        and not contradictions["blocking"],
    }


@router.get("/{report_id}/final-checklist")
def report_final_checklist(report_id: int, db: Session = Depends(get_db)):
    report = get_or_404(db, Report, report_id)
    return final_pericial_checklist(report)


@router.get("/{report_id}/annexes")
def report_annexes(report_id: int, db: Session = Depends(get_db)):
    report = get_or_404(db, Report, report_id)
    return report_annexes_payload(report)


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


@router.post("/{report_id}/annexes/refresh", response_model=ReportRead)
def refresh_report_annexes(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_optional_user),
):
    report = get_or_404(db, Report, report_id)
    annex_block = report_annexes_markdown(report)
    marker = "## Anexos reales"
    current = report.markdown_content or ""
    if marker in current:
        report.markdown_content = current.split(marker, 1)[0].rstrip() + "\n\n" + annex_block + "\n"
    else:
        report.markdown_content = current.rstrip() + "\n\n" + annex_block + "\n"
    report.sections = populate_report_sections(report, report.markdown_content)
    report.versions.append(snapshot_report(report, current_user.email if current_user else report.author, "Actualización de anexos reales"))
    write_audit(db, "refresh_report_annexes", "reports", current_user, case_id=report.case_id, entity_type="report", entity_id=str(report.id), details=report.title)
    db.commit()
    db.refresh(report)
    return report


@router.post("/{report_id}/versions/transition", response_model=ReportRead)
def transition_report_version(
    report_id: int,
    payload: ReportVersionTransition,
    db: Session = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_optional_user),
):
    report = get_or_404(db, Report, report_id)
    allowed = {"borrador", "preliminar", "revisado", "final", "corregido", "reabierto"}
    next_status = payload.status.lower().strip()
    if next_status not in allowed:
        raise HTTPException(status_code=400, detail="Estado de versión no soportado")
    if next_status == "final":
        checklist = final_pericial_checklist(report)
        if not checklist["ready"]:
            raise HTTPException(status_code=409, detail={"message": "Checklist pericial final incompleto", "checklist": checklist})
    report.status = next_status
    if next_status in {"preliminar", "revisado", "final", "corregido", "reabierto"}:
        base = len(report.versions) + 1
        report.version = f"1.{base}"
    report.versions.append(
        snapshot_report(
            report,
            payload.user or (current_user.email if current_user else report.author),
            payload.note or f"Cambio de estado a {next_status}",
        )
    )
    write_audit(db, "transition_report_version", "reports", current_user, case_id=report.case_id, entity_type="report", entity_id=str(report.id), details=f"{report.title}: {next_status}")
    db.commit()
    db.refresh(report)
    return report


@router.put("/{report_id}/executive-summary", response_model=ReportRead)
def update_executive_summary(
    report_id: int,
    payload: ExecutiveSummaryUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_optional_user),
):
    report = get_or_404(db, Report, report_id)
    if not payload.executive_summary.strip():
        raise HTTPException(status_code=400, detail="El resumen ejecutivo no puede quedar vacío")
    report.markdown_content = replace_executive_summary(report, payload.executive_summary)
    report.sections = populate_report_sections(report, report.markdown_content)
    report.versions.append(snapshot_report(report, payload.author or report.author, "Edición manual del resumen ejecutivo"))
    write_audit(
        db,
        "update_executive_summary",
        "reports",
        current_user,
        case_id=report.case_id,
        entity_type="report",
        entity_id=str(report.id),
        details=report.title,
    )
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
