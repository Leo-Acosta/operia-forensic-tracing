from pathlib import Path
from shutil import copyfileobj

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from uuid import uuid4
from sqlalchemy import desc
from sqlalchemy.orm import Session

from operia.audit.service import write_audit
from operia.cases.models import Case
from operia.core.config import settings
from operia.core.database import get_db
from operia.evidence.models import ChainOfCustodyAction, Evidence
from operia.identity.dependencies import CurrentUser, get_optional_user, require_permission
from operia.evidence.schemas import CustodyActionCreate, CustodyActionRead, CustodyRectification, EvidenceCreate, EvidenceRead
from operia.shared.crud import get_or_404, update_from_payload
from operia.shared.hashing import file_md5, file_sha256

router = APIRouter()


def preserved_source(db, item):
    from operia.forensic_jobs.models import EvidenceIntegration, Acquisition, ExaminationJob
    from operia.forensic_engine.canonical import sha256
    link = db.query(EvidenceIntegration).filter_by(evidence_id=item.id).first()
    if not link:
        return None
    job = db.get(ExaminationJob, link.job_id)
    acquisition = db.get(Acquisition, job.acquisition_id) if job else None
    if not acquisition or acquisition.case_id != item.case_id or acquisition.organization_id != item.organization_id or sha256(acquisition.original_bytes) != item.sha256_hash:
        raise HTTPException(409, "Integridad del original alterada")
    return acquisition.original_bytes


def safe_path(location, case_id=None):
    path = Path(location).resolve()
    if not path.is_relative_to(settings.uploads_dir.resolve()) or Path(location).is_symlink():
        raise HTTPException(403, "Archivo fuera del depósito de evidencias")
    if case_id is not None and not path.is_relative_to((settings.uploads_dir / str(case_id)).resolve()):
        raise HTTPException(403, "Archivo ajeno al deposito del caso")
    return path



@router.get("/")
def status() -> dict[str, object]:
    return {
        "module": "Evidence",
        "status": "canonical",
        "description": "Evidence vault, uploads, hashes, attachments, and chain-of-custody actions.",
    }


@router.post("", response_model=EvidenceRead)
def create_evidence(
    payload: EvidenceCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("evidence:write")),
):
    case = get_or_404(db, Case, payload.case_id)
    item = Evidence(**payload.model_dump())
    item.organization_id = current_user.organization_id if current_user and current_user.organization_id else case.organization_id
    db.add(item)
    db.flush()
    db.add(
        ChainOfCustodyAction(
            case_id=item.case_id,
            evidence_id=item.id,
            action_type="carga",
            detailed_description=f"Evidencia cargada: {item.description}",
            hash_after=item.sha256_hash,
        )
    )
    write_audit(db, "create_evidence", "evidence", current_user, case_id=item.case_id, entity_type="evidence", entity_id=str(item.id), details=item.description)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{evidence_id}", response_model=EvidenceRead)
def read_evidence(evidence_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Evidence, evidence_id)


@router.get("/{evidence_id}/metadata")
def evidence_metadata(evidence_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, Evidence, evidence_id)
    raw = preserved_source(db, item)
    path = safe_path(item.file_location, item.case_id) if item.file_location else Path()
    exists = path.exists() if item.file_location else False
    return {
        "id": item.id,
        "case_id": item.case_id,
        "description": item.description,
        "type": item.evidence_type,
        "source": item.source,
        "file_location": item.file_location,
        "file_exists": raw is not None or exists,
        "file_size": len(raw) if raw is not None else (path.stat().st_size if exists else None),
        "sha256_hash": item.sha256_hash,
        "md5_hash": item.md5_hash,
        "integrity_status": item.integrity_status,
        "preservation_method": item.preservation_method,
        "tool_used": item.tool_used,
        "custodian": item.custodian,
        "responsible": item.responsible,
    }


@router.get("/{evidence_id}/integrity")
def verify_evidence_integrity(evidence_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, Evidence, evidence_id)
    raw = preserved_source(db, item)
    if raw is not None:
        return {"ok": True, "stored_sha256": item.sha256_hash, "integrity_status": "integra"}
    if not item.file_location:
        return {"ok": False, "message": "La evidencia no posee archivo asociado.", "stored_sha256": item.sha256_hash}
    path = safe_path(item.file_location, item.case_id)
    if not path.exists():
        return {"ok": False, "message": "Archivo no encontrado en storage.", "stored_sha256": item.sha256_hash}
    actual_sha = file_sha256(path)
    actual_md5 = file_md5(path)
    ok = actual_sha == item.sha256_hash if item.sha256_hash else True
    item.integrity_status = "integra" if ok else "hash_no_coincidente"
    db.commit()
    return {
        "ok": ok,
        "stored_sha256": item.sha256_hash,
        "actual_sha256": actual_sha,
        "stored_md5": item.md5_hash,
        "actual_md5": actual_md5,
        "integrity_status": item.integrity_status,
    }


@router.get("/{evidence_id}/download")
def download_evidence(evidence_id: int, db: Session = Depends(get_db)):
    item = get_or_404(db, Evidence, evidence_id)
    raw = preserved_source(db, item)
    if raw is not None:
        return Response(raw, media_type="application/octet-stream", headers={"Cache-Control": "no-store", "Content-Disposition": f'attachment; filename="evidence-{item.id}.bin"'})
    if not item.file_location:
        raise HTTPException(status_code=404, detail="La evidencia no posee archivo asociado")
    path = safe_path(item.file_location, item.case_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo de evidencia no encontrado")
    if item.sha256_hash and file_sha256(path) != item.sha256_hash:
        raise HTTPException(409, "Integridad del archivo alterada")
    return FileResponse(path, filename=path.name)


@router.put("/{evidence_id}", response_model=EvidenceRead)
def update_evidence(
    evidence_id: int,
    payload: EvidenceCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("evidence:write")),
):
    item = update_from_payload(get_or_404(db, Evidence, evidence_id), payload)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{evidence_id}")
def delete_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("evidence:write")),
):
    item = get_or_404(db, Evidence, evidence_id)
    if db.query(ChainOfCustodyAction.id).filter_by(evidence_id=evidence_id).first():
        raise HTTPException(409, "custody_parent_preserved")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.get("/case/{case_id}", response_model=list[EvidenceRead])
def list_case_evidence(case_id: int, db: Session = Depends(get_db)):
    return db.query(Evidence).filter_by(case_id=case_id).order_by(desc(Evidence.created_at)).all()


@router.post("/case/{case_id}/upload", response_model=EvidenceRead)
def upload_evidence(
    case_id: int,
    description: str,
    responsible: str = "",
    custodian: str = "",
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("evidence:write")),
):
    case = get_or_404(db, Case, case_id)
    case_dir = settings.uploads_dir / str(case_id)
    case_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "evidence.bin").name
    destination = safe_path(str(case_dir / (uuid4().hex + "-" + safe_name)), case_id)
    with destination.open("xb") as buffer:
        copyfileobj(file.file, buffer)
    sha = file_sha256(destination)
    evidence = Evidence(
        organization_id=current_user.organization_id if current_user and current_user.organization_id else case.organization_id,
        case_id=case_id,
        evidence_type="archivo",
        description=description,
        responsible=responsible,
        custodian=custodian,
        sha256_hash=sha,
        md5_hash=file_md5(destination),
        file_location=str(destination),
        preservation_method="Carga local con calculo automatico de SHA-256",
        tool_used="OPERIA Evidence",
        integrity_status="integra",
        confidence_level="alto",
    )
    db.add(evidence)
    db.flush()
    db.add(
        ChainOfCustodyAction(
            case_id=case_id,
            evidence_id=evidence.id,
            action_type="carga",
            detailed_description=f"Archivo preservado: {safe_name}",
            tool_used="OPERIA Evidence",
            hash_after=sha,
            user_responsible=responsible,
        )
    )
    write_audit(db, "upload_evidence", "evidence", current_user, case_id=case_id, entity_type="evidence", entity_id=str(evidence.id), details=safe_name)
    db.commit()
    db.refresh(evidence)
    return evidence


@router.post("/custody-actions", response_model=CustodyActionRead)
def create_action(
    payload: CustodyActionCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("evidence:write")),
):
    item = ChainOfCustodyAction(**payload.model_dump())
    if current_user and current_user.organization_id:
        item.organization_id = current_user.organization_id
    db.add(item)
    db.flush()
    write_audit(db, "create_custody_action", "evidence", current_user, case_id=item.case_id, entity_type="custody_action", entity_id=str(item.id), details=item.action_type)
    db.commit()
    db.refresh(item)
    return item


@router.put("/custody-actions/{action_id}", response_model=CustodyActionRead)
def update_action(
    action_id: int,
    payload: CustodyActionCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("evidence:write")),
):
    get_or_404(db, ChainOfCustodyAction, action_id)
    raise HTTPException(409, "custody_append_only: registrar una rectificación")


@router.delete("/custody-actions/{action_id}")
def delete_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("evidence:write")),
):
    get_or_404(db, ChainOfCustodyAction, action_id)
    raise HTTPException(409, "custody_append_only: registrar una rectificación")


@router.post("/custody-actions/{action_id}/rectifications", response_model=CustodyActionRead)
def rectify_action(action_id: int, payload: CustodyRectification, db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("evidence:write"))):
    from operia.evidence.custody import rectify
    target = get_or_404(db, ChainOfCustodyAction, action_id)
    item = rectify(db, target, payload)
    write_audit(db, "rectify_custody_action", "evidence", current_user, case_id=item.case_id,
        entity_type="custody_action", entity_id=str(item.id), details=f"previous_action_id={target.id}")
    db.commit()
    db.refresh(item)
    return item


@router.get("/custody-actions/{action_id}/history", response_model=list[CustodyActionRead])
def custody_history(action_id: int, db: Session = Depends(get_db)):
    from operia.evidence.models import CustodyLedgerEntry
    target = get_or_404(db, ChainOfCustodyAction, action_id)
    entry = db.query(CustodyLedgerEntry).filter_by(action_id=target.id).first()
    root = entry.root_action_id if entry else target.id
    revisions = db.query(CustodyLedgerEntry.action_id).filter_by(root_action_id=root)
    return db.query(ChainOfCustodyAction).filter(
        (ChainOfCustodyAction.id == root) | ChainOfCustodyAction.id.in_(revisions)
    ).order_by(ChainOfCustodyAction.id).all()


@router.get("/case/{case_id}/custody-actions", response_model=list[CustodyActionRead])
def list_actions(case_id: int, evidence_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(ChainOfCustodyAction).filter_by(case_id=case_id)
    if evidence_id:
        query = query.filter_by(evidence_id=evidence_id)
    return query.order_by(ChainOfCustodyAction.action_at).all()
