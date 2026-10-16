import base64
import binascii
import json
import shutil

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from operia.audit.service import write_audit
from operia.core.config import settings
from operia.core.database import get_db
from operia.identity.dependencies import CurrentUser, require_permission
from operia.mobile_forensics.models import MobileDevice, MobileExam, MobileExport, MobileReview
from operia.mobile_forensics.schemas import DeviceCreate, ImportMetadata, ReviewCreate
from operia.mobile_forensics.service import (
    bounded_json, digest, parse_result, public_exam, scoped_case, scoped_exam, verify_original,
)

router = APIRouter()
read = require_permission("evidence:read")
write = require_permission("evidence:write")


def audit(db, action, user, case_id, entity_id):
    write_audit(db, action, "mobile_forensics", user, case_id=case_id,
                entity_type="mobile_exam", entity_id=str(entity_id))


@router.get("/engine")
def engine(user: CurrentUser = Depends(read)):
    return {"execution_enabled": False, "validated": False,
            "ios_executable_found": bool(shutil.which("mvt-ios")),
            "android_executable_found": bool(shutil.which("mvt-android")),
            "message": "Ejecución deshabilitada: versión, opciones y adquisiciones sin validar. Importación experimental disponible.",
            "supported_imports": {"ios": ["sms.json", "sms_detected.json", "safari_history.json", "safari_history_detected.json"],
                                  "android": ["sms.json", "sms_detected.json"]}}


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
async def import_result(case_id: int, device_id: int, request: Request,
                        db: Session = Depends(get_db), user: CurrentUser = Depends(write)):
    scoped_case(db, case_id, user)
    device = db.get(MobileDevice, device_id)
    if not device or device.case_id != case_id or device.organization_id != user.organization_id:
        raise HTTPException(404, "Dispositivo no encontrado en este caso")
    # Bound the entire transport before JSON parsing or base64 decoding. No archive
    # extraction, user paths, subprocesses, URL resolution or network lookups.
    limit = settings.mobile_import_max_bytes
    transport_limit = limit * 4 // 3 + 65536
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > transport_limit:
            raise HTTPException(413, "Importación supera el límite de transporte")
        body.extend(chunk)
    envelope = bounded_json(bytes(body))
    if not isinstance(envelope, dict) or set(envelope) != {"metadata", "filename", "content_base64"}:
        raise HTTPException(422, "Se requiere metadata, filename y content_base64")
    try:
        metadata = ImportMetadata.model_validate(envelope["metadata"])
        filename = envelope["filename"]
        if not isinstance(filename, str) or len(filename) > 100:
            raise ValueError()
        raw = base64.b64decode(envelope["content_base64"], validate=True)
    except (ValidationError, ValueError, TypeError, binascii.Error):
        raise HTTPException(422, "Metadatos, consentimiento o contenido base64 inválidos")
    if len(raw) > limit:
        raise HTTPException(413, "Archivo supera el límite configurado")
    sha = digest(raw)  # Original bytes, before parsing/transformation.
    records, candidates = parse_result(raw, filename, device.platform)
    if db.query(MobileExam).filter_by(device_id=device_id, sha256=sha).first():
        raise HTTPException(409, "Bytes ya importados para este dispositivo")
    item = MobileExam(**metadata.model_dump(),
        organization_id=user.organization_id, case_id=case_id, device_id=device_id, operator_id=user.id,
        filename=filename, original_bytes=raw, sha256=sha, record_count=len(records), candidate_count=candidates,
        coverage="parcial_no_verificada" if records else "sin_datos_analizables",
        limitations="Un archivo aislado no verifica ejecución, módulos omitidos ni indicadores exactos. "
                     "Procedencia y versión declaradas. No permite confirmar compromiso, actividad actual ni ausencia de indicios.")
    db.add(item)
    try:
        db.flush()
        audit(db, "mobile_import_preserved", user, case_id, item.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Importación duplicada o referencia inconsistente")
    db.refresh(item)
    return public_exam(item)


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
        "offset": offset, "reviews": reviews}


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
def review(case_id: int, exam_id: int, payload: ReviewCreate,
           db: Session = Depends(get_db), user: CurrentUser = Depends(write)):
    exam = scoped_exam(db, case_id, exam_id, user)
    verify_original(exam)
    refs = payload.record_indexes
    if len(refs) != len(set(refs)) or any(i < 0 or i >= exam.record_count for i in refs):
        raise HTTPException(422, "Referencias fuera del archivo o duplicadas")
    if payload.conclusion != "inconcluso" and not refs:
        raise HTTPException(422, "La conclusión requiere registros de respaldo")
    item = MobileReview(**payload.model_dump(exclude={"record_indexes"}), exam_id=exam_id,
        reviewer_id=user.id, reviewer_name=user.name,
        references_json=json.dumps([{"sha256": exam.sha256, "pointer": f"/{i}"} for i in refs]))
    db.add(item)
    db.flush()
    audit(db, "mobile_review_appended", user, case_id, exam_id)
    db.commit()
    db.refresh(item)
    return item


@router.post("/cases/{case_id}/exams/{exam_id}/exports")
def export(case_id: int, exam_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(write)):
    exam = scoped_exam(db, case_id, exam_id, user)
    verify_original(exam)
    reviews = db.query(MobileReview).filter_by(exam_id=exam_id).order_by(MobileReview.id).all()
    item = MobileExport(exam_id=exam_id, review_id=reviews[-1].id if reviews else None,
                        created_by=user.id, content=b"", sha256="")
    db.add(item)
    db.flush()
    snapshot = {"schema": "operia-mobile-pilot/1", "exam": public_exam(exam),
        "report_id": item.id, "generated_at_utc": item.created_at, "generated_by": user.id,
        "device": db.get(MobileDevice, exam.device_id), "reviews": reviews,
        "review_id": reviews[-1].id if reviews else None,
        "report_status": "borrador_experimental", "manifest": [{"filename": exam.filename,
            "sha256": exam.sha256, "size_bytes": len(exam.original_bytes)}],
        "hash_scope": "SHA-256 acredita identidad de bytes recibidos, no autenticidad de origen ni integridad del dispositivo.",
        "warning": "No garantiza limpieza, atribución ni admisibilidad judicial. Sin validación real de MVT."}
    content = json.dumps(jsonable_encoder(snapshot), ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    item.content = content
    item.sha256 = digest(content)
    audit(db, "mobile_export_created", user, case_id, exam_id)
    db.commit()
    return {"id": item.id, "sha256": item.sha256, "review_id": item.review_id}


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
