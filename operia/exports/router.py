from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from operia.audit.service import write_audit
from operia.core.database import get_db
from operia.exports.models import ExportManifest
from operia.exports.service import (
    export_csv_rows,
    export_pdf,
    export_json_payload,
    export_markdown_text,
    export_text_pdf,
    register_export_manifest,
)
from operia.legal_report.services.report_service import (
    legal_contradiction_assessment,
    legal_probatory_assessment,
    report_exportability_assessment,
)
from operia.identity.dependencies import CurrentUser, get_optional_user
from operia.reports.models import Report
from operia.shared.crud import get_or_404

router = APIRouter()


def as_dict(obj) -> dict:
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}


def response_with_manifest(path: Path, manifest: ExportManifest) -> FileResponse:
    return FileResponse(
        path,
        filename=path.name,
        headers={
            "X-OPERIA-Export-Manifest-Id": str(manifest.id),
            "X-OPERIA-SHA256": manifest.sha256_hash,
            "X-OPERIA-Manifest-Path": manifest.manifest_path,
        },
    )


@router.get("/")
def status() -> dict[str, object]:
    return {
        "module": "Exports",
        "status": "canonical",
        "formats": ["pdf", "docx", "html", "markdown", "csv", "json"],
        "description": "Centralized export workflows with forensic metadata, hashes, manifests, and audit trail.",
    }


@router.get("/manifests")
def list_manifests(
    case_id: int | None = None,
    report_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_optional_user),
):
    query = db.query(ExportManifest)
    if current_user and current_user.organization_id:
        query = query.filter(ExportManifest.organization_id.in_([current_user.organization_id, None]))
    if case_id is not None:
        query = query.filter_by(case_id=case_id)
    if report_id is not None:
        query = query.filter_by(report_id=report_id)
    return [as_dict(row) for row in query.order_by(ExportManifest.created_at.desc()).limit(200).all()]


@router.get("/manifests/{manifest_id}")
def read_manifest(manifest_id: int, db: Session = Depends(get_db)):
    return as_dict(get_or_404(db, ExportManifest, manifest_id))


@router.get("/manifests/{manifest_id}/download")
def download_manifest(manifest_id: int, db: Session = Depends(get_db)):
    manifest = get_or_404(db, ExportManifest, manifest_id)
    path = Path(manifest.manifest_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo de manifiesto no encontrado")
    return FileResponse(path, filename=path.name)


@router.post("/json")
def export_json(payload: dict, db: Session = Depends(get_db), current_user: CurrentUser | None = Depends(get_optional_user)):
    filename = str(payload.get("filename") or "operia-export.json")
    content = payload.get("content")
    if not isinstance(content, dict):
        raise HTTPException(status_code=400, detail="content debe ser un objeto JSON")
    path = export_json_payload(content, filename)
    manifest = register_export_manifest(db, path, "json", current_user, payload.get("case_id"), payload.get("report_id"))
    write_audit(db, "export_json", "exports", current_user, payload.get("case_id"), "export", str(manifest.id), details=path.name)
    db.commit()
    return response_with_manifest(path, manifest)


@router.post("/csv")
def export_csv(payload: dict, db: Session = Depends(get_db), current_user: CurrentUser | None = Depends(get_optional_user)):
    filename = str(payload.get("filename") or "operia-export.csv")
    rows = payload.get("rows")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise HTTPException(status_code=400, detail="rows debe ser una lista de objetos")
    path = export_csv_rows(rows, filename)
    manifest = register_export_manifest(db, path, "csv", current_user, payload.get("case_id"), payload.get("report_id"))
    write_audit(db, "export_csv", "exports", current_user, payload.get("case_id"), "export", str(manifest.id), details=path.name)
    db.commit()
    return response_with_manifest(path, manifest)


@router.post("/markdown")
def export_markdown_payload(payload: dict, db: Session = Depends(get_db), current_user: CurrentUser | None = Depends(get_optional_user)):
    filename = str(payload.get("filename") or "operia-export.md")
    markdown = str(payload.get("markdown") or "")
    path = export_markdown_text(markdown, filename)
    manifest = register_export_manifest(db, path, "markdown", current_user, payload.get("case_id"), payload.get("report_id"))
    write_audit(db, "export_markdown", "exports", current_user, payload.get("case_id"), "export", str(manifest.id), details=path.name)
    db.commit()
    return response_with_manifest(path, manifest)


@router.post("/pdf")
def export_pdf_payload(payload: dict, db: Session = Depends(get_db), current_user: CurrentUser | None = Depends(get_optional_user)):
    filename = str(payload.get("filename") or "operia-export.pdf")
    title = str(payload.get("title") or "OPERIA Export")
    body = str(payload.get("body") or payload.get("markdown") or "")
    path = export_text_pdf(title, body, filename)
    manifest = register_export_manifest(db, path, "pdf", current_user, payload.get("case_id"), payload.get("report_id"))
    write_audit(db, "export_pdf", "exports", current_user, payload.get("case_id"), "export", str(manifest.id), details=path.name)
    db.commit()
    return response_with_manifest(path, manifest)


@router.get("/reports/{report_id}/{fmt}")
def export_report(
    report_id: int,
    fmt: str,
    final: bool = False,
    db: Session = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_optional_user),
):
    report = get_or_404(db, Report, report_id)
    legal_probatory = legal_probatory_assessment(report.case)
    exportability = report_exportability_assessment(report.case, legal_probatory, report=report)
    contradictions = legal_contradiction_assessment(report.case)
    can_export_final = exportability["level"] in {"Listo para revisión", "Apto para presentación"} and not contradictions["blocking"]
    if final and not can_export_final:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "El informe no cumple condiciones para exportación final.",
                "exportability": exportability,
                "contradictions": contradictions,
            },
        )
    if fmt == "json":
        path = export_json_payload(
            {
                "id": report.id,
                "case_id": report.case_id,
                "title": report.title,
                "version": report.version,
                "author": report.author,
                "status": report.status,
                "markdown_content": report.markdown_content,
            },
            f"report-{report.id}.json",
        )
    elif fmt == "csv":
        path = export_csv_rows(
            [
                {
                    "id": report.id,
                    "case_id": report.case_id,
                    "title": report.title,
                    "version": report.version,
                    "author": report.author,
                    "status": report.status,
                }
            ],
            f"report-{report.id}.csv",
        )
    elif fmt == "pdf":
        path = export_pdf(report)
    elif fmt == "markdown":
        path = export_markdown_text(report.markdown_content, f"report-{report.id}-canonical.md")
    else:
        raise HTTPException(status_code=400, detail="Formato no soportado en exports canonical")
    manifest = register_export_manifest(
        db,
        path,
        fmt,
        current_user,
        case_id=report.case_id,
        report_id=report.id,
        extra={
            "report_title": report.title,
            "report_status": report.status,
            "template": "forensic_professional",
            "human_review_required": True,
            "exportability_level": exportability["level"],
            "exportability_score": exportability["score"],
            "final_requested": final,
        },
    )
    write_audit(db, f"export_report_{fmt}", "exports", current_user, report.case_id, "export", str(manifest.id), details=path.name)
    db.commit()
    return response_with_manifest(path, manifest)
