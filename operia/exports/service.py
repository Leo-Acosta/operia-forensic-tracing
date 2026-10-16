import csv
import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from operia.core.config import settings
from operia.exports.paths import new_export_path
from operia.exports.models import ExportManifest
from operia.identity.dependencies import CurrentUser
from operia.shared.hashing import file_md5, file_sha256
from operia.shared.time import utcnow

from operia.exports.report_exporters import (
    export_docx,
    export_html,
    export_markdown,
    export_pdf,
    export_presentation_pdf,
)


def export_json_payload(payload: dict[str, Any], filename: str) -> Path:
    path = new_export_path(filename)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def export_csv_rows(rows: list[dict[str, Any]], filename: str) -> Path:
    path = new_export_path(filename)
    fieldnames = sorted({key for row in rows for key in row.keys()}) if rows else ["empty"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def export_markdown_text(markdown: str, filename: str) -> Path:
    path = new_export_path(filename)
    path.write_text(markdown, encoding="utf-8")
    return path


def export_text_pdf(title: str, body: str, filename: str) -> Path:
    path = new_export_path(filename)
    doc = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    y = height - 72
    doc.setFont("Helvetica-Bold", 15)
    doc.drawString(72, y, title[:90])
    y -= 32
    doc.setFont("Helvetica", 10)
    for raw_line in body.splitlines() or ["Sin contenido."]:
        line = raw_line.strip() or " "
        while len(line) > 110:
            doc.drawString(72, y, line[:110])
            line = line[110:]
            y -= 14
            if y < 72:
                doc.showPage()
                doc.setFont("Helvetica", 10)
                y = height - 72
        doc.drawString(72, y, line)
        y -= 14
        if y < 72:
            doc.showPage()
            doc.setFont("Helvetica", 10)
            y = height - 72
    doc.save()
    return path


def build_export_metadata(
    path: Path,
    export_type: str,
    current_user: CurrentUser | None = None,
    case_id: int | None = None,
    report_id: int | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "product": "OPERIA Forensic Tracing",
        "export_type": export_type,
        "filename": path.name,
        "file_path": str(path),
        "generated_at": utcnow().isoformat(),
        "generated_by": current_user.email or current_user.name if current_user else "local",
        "organization_id": current_user.organization_id if current_user else None,
        "user_id": current_user.id if current_user else None,
        "case_id": case_id,
        "report_id": report_id,
        "sha256": file_sha256(path),
        "md5": file_md5(path),
        "human_review_required": True,
        "chain_of_custody_note": "Exportacion generada por OPERIA. Validar hash, contexto, version y autorizacion antes de presentacion externa.",
        "extra": extra or {},
    }


def write_manifest_file(path: Path, metadata: dict[str, Any]) -> Path:
    manifest_path = path.with_suffix(path.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest_path


def register_export_manifest(
    db: Session,
    path: Path,
    export_type: str,
    current_user: CurrentUser | None = None,
    case_id: int | None = None,
    report_id: int | None = None,
    extra: dict[str, Any] | None = None,
) -> ExportManifest:
    metadata = build_export_metadata(
        path=path,
        export_type=export_type,
        current_user=current_user,
        case_id=case_id,
        report_id=report_id,
        extra=extra,
    )
    manifest_path = write_manifest_file(path, metadata)
    row = ExportManifest(
        organization_id=metadata["organization_id"],
        user_id=metadata["user_id"],
        case_id=case_id,
        report_id=report_id,
        export_type=export_type,
        filename=path.name,
        file_path=str(path),
        sha256_hash=metadata["sha256"],
        md5_hash=metadata["md5"],
        manifest_path=str(manifest_path),
        status="generated",
        generated_by=str(metadata["generated_by"]),
        metadata_json=json.dumps(metadata, ensure_ascii=False),
    )
    db.add(row)
    db.flush()
    return row


__all__ = [
    "export_csv_rows",
    "export_docx",
    "export_html",
    "export_json_payload",
    "export_markdown",
    "export_markdown_text",
    "export_pdf",
    "export_presentation_pdf",
    "export_text_pdf",
    "register_export_manifest",
]
