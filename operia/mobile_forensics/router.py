
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from operia.audit.service import write_audit
from operia.core.database import get_db
from operia.identity.dependencies import CurrentUser, require_permission
from operia.mobile_forensics.models import MobileDevice, MobileExam, MobileExport, MobileReview
from operia.mobile_forensics.schemas import DeviceCreate
from operia.mobile_forensics.service import (
    digest, parse_result, public_exam, scoped_case, scoped_exam, verify_original,
)

router = APIRouter()
read = require_permission("evidence:read")
write = require_permission("evidence:write")


def audit(db, action, user, case_id, entity_id):
    write_audit(db, action, "mobile_forensics", user, case_id=case_id,
                entity_type="mobile_exam", entity_id=str(entity_id))


@router.get("/engine")
def engine(user: CurrentUser = Depends(read)):
    from operia.forensic_engine.analysis import capabilities
    return capabilities() | {"legacy_imports_enabled": False, "worker_required": True}


@router.get("/cases/{case_id}/devices")
def devices(case_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(read)):
    scoped_case(db, case_id, user)
    return db.query(MobileDevice).filter_by(case_id=case_id, organization_id=user.organization_id).all()


@router.post("/cases/{case_id}/devices")
def create_device(case_id: int, payload: DeviceCreate, db: Session = Depends(get_db), user: CurrentUser = Depends(write)):
    scoped_case(db, case_id, user)
    item = MobileDevice(**payload.model_dump(), case_id=case_id, organization_id=user.organization_id, created_by=user.id)
    db.add(item)
    db.flush()
    audit(db, "mobile_device_created", user, case_id, item.id)
    db.commit()
    db.refresh(item)
    return item


@router.get("/cases/{case_id}/exams")
def exams(case_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(read)):
    scoped_case(db, case_id, user)
    return [public_exam(exam) for exam in db.query(MobileExam).filter_by(
        case_id=case_id, organization_id=user.organization_id).order_by(MobileExam.id.desc()).all()]


@router.post("/cases/{case_id}/devices/{device_id}/imports")
def retired_import(case_id: int, device_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(write)):
    scoped_case(db, case_id, user)
    raise HTTPException(410, "Importador externo retirado. Usá adquisiciones del motor propio; los históricos se conservan.")


@router.get("/cases/{case_id}/exams/{exam_id}")
def detail(case_id: int, exam_id: int, offset: int = 0, db: Session = Depends(get_db), user: CurrentUser = Depends(read)):
    exam = scoped_exam(db, case_id, exam_id, user)
    verify_original(exam)
    if offset < 0 or offset > exam.record_count:
        raise HTTPException(422, "Offset fuera de rango")
    records, _ = parse_result(exam.original_bytes, exam.filename, db.get(MobileDevice, exam.device_id).platform)
    reviews = db.query(MobileReview).filter_by(exam_id=exam_id).order_by(MobileReview.id).all()
    return {"exam": public_exam(exam), "records": [
        {"index": index, "pointer": f"/{index}", "record": records[index],
         "assessment": "pendiente_de_corroboracion" if exam.candidate_count else "registro_observado"}
        for index in range(offset, min(offset + 100, len(records)))],
        "offset": offset, "reviews": reviews, "exports": [
            {"id": item.id, "sha256": item.sha256, "review_id": item.review_id}
            for item in db.query(MobileExport).filter_by(exam_id=exam_id).order_by(MobileExport.id).all()]}


@router.get("/cases/{case_id}/exams/{exam_id}/original")
def original(case_id: int, exam_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(read)):
    exam = scoped_exam(db, case_id, exam_id, user)
    verify_original(exam)
    audit(db, "mobile_original_downloaded", user, case_id, exam_id)
    db.commit()
    return Response(exam.original_bytes, media_type="application/octet-stream", headers={
        "Content-Disposition": f'attachment; filename="{exam.filename}"',
        "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"})


@router.post("/cases/{case_id}/exams/{exam_id}/reviews")
@router.post("/cases/{case_id}/exams/{exam_id}/exports")
def retired_writes(case_id: int, exam_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(write)):
    scoped_exam(db, case_id, exam_id, user)
    raise HTTPException(410, "Histórico externo de solo lectura; no se convierte en resultado del motor propio.")


@router.get("/cases/{case_id}/exams/{exam_id}/exports/{export_id}")
def download_export(case_id: int, exam_id: int, export_id: int,
                    db: Session = Depends(get_db), user: CurrentUser = Depends(read)):
    scoped_exam(db, case_id, exam_id, user)
    item = db.get(MobileExport, export_id)
    if not item or item.exam_id != exam_id:
        raise HTTPException(404, "Exportación no encontrada")
    if digest(item.content) != item.sha256:
        raise HTTPException(409, "Exportación alterada")
    audit(db, "mobile_export_downloaded", user, case_id, exam_id)
    db.commit()
    return Response(item.content, media_type="application/json", headers={
        "Content-Disposition": f'attachment; filename="mobile-{exam_id}-export-{export_id}.json"',
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
