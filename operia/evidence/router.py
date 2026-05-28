from pathlib import Path
from shutil import copyfileobj

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from operia.audit.service import write_audit
from operia.cases.models import Case
from operia.core.config import settings
from operia.core.database import get_db
from operia.evidence.models import ChainOfCustodyAction, Evidence
from operia.identity.dependencies import CurrentUser, get_optional_user
from operia.evidence.schemas import CustodyActionCreate, CustodyActionRead, EvidenceCreate, EvidenceRead
from operia.shared.crud import get_or_404, update_from_payload
from operia.shared.hashing import file_md5, file_sha256

router = APIRouter()


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
    current_user: CurrentUser | None = Depends(get_optional_user),
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
    path = Path(item.file_location or "")
    exists = path.exists() if item.file_location else False
    return {
        "id": item.id,
        "case_id": item.case_id,
        "description": item.description,
        "type": item.evidence_type,
        "source": item.source,
        "file_location": item.file_location,
        "file_exists": exists,
        "file_size": path.stat().st_size if exists else None,
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
    if not item.file_location:
        return {"ok": False, "message": "La evidencia no posee archivo asociado.", "stored_sha256": item.sha256_hash}
    path = Path(item.file_location)
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
    if not item.file_location:
        raise HTTPException(status_code=404, detail="La evidencia no posee archivo asociado")
    path = Path(item.file_location)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo de evidencia no encontrado")
    return FileResponse(path, filename=path.name)


@router.put("/{evidence_id}", response_model=EvidenceRead)
def update_evidence(evidence_id: int, payload: EvidenceCreate, db: Session = Depends(get_db)):
    item = update_from_payload(get_or_404(db, Evidence, evidence_id), payload)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{evidence_id}")
def delete_evidence(evidence_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Evidence, evidence_id))
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
    current_user: CurrentUser | None = Depends(get_optional_user),
):
    case = get_or_404(db, Case, case_id)
    case_dir = settings.uploads_dir / str(case_id)
    case_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "evidence.bin").name
    destination = case_dir / safe_name
    with destination.open("wb") as buffer:
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
    current_user: CurrentUser | None = Depends(get_optional_user),
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
    current_user: CurrentUser | None = Depends(get_optional_user),
):
    item = update_from_payload(get_or_404(db, ChainOfCustodyAction, action_id), payload)
    write_audit(db, "update_custody_action", "evidence", current_user, case_id=item.case_id, entity_type="custody_action", entity_id=str(item.id), details=item.action_type)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/custody-actions/{action_id}")
def delete_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_optional_user),
):
    item = get_or_404(db, ChainOfCustodyAction, action_id)
    case_id = item.case_id
    write_audit(db, "delete_custody_action", "evidence", current_user, case_id=case_id, entity_type="custody_action", entity_id=str(item.id), severity="warning", details=item.action_type)
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.get("/case/{case_id}/custody-actions", response_model=list[CustodyActionRead])
def list_actions(case_id: int, evidence_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(ChainOfCustodyAction).filter_by(case_id=case_id)
    if evidence_id:
        query = query.filter_by(evidence_id=evidence_id)
    return query.order_by(ChainOfCustodyAction.action_at).all()
