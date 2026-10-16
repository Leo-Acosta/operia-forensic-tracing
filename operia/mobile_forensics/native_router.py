import base64
import json
import platform
import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from operia.audit.service import write_audit
from operia.core.database import get_db
from operia.forensic_engine import ENGINE_VERSION
from operia.forensic_engine.analysis import capabilities, timeline_csv
from operia.forensic_engine.canonical import MAX_SOURCE_BYTES, canonical_bytes, read_json, sha256
from operia.forensic_engine.contracts import EngineInputError
from operia.forensic_engine.detection import validate_indicators
from operia.forensic_jobs.models import Acquisition, ExaminationJob, ExportRecord, IndicatorSet, JobEvent, ReviewRevision
from operia.forensic_jobs.worker import DONE, event
from operia.forensic_jobs.storage_limits import begin_write, ensure_capacity
from operia.identity.dependencies import CurrentUser, require_permission
from operia.mobile_forensics.models import MobileDevice
from operia.mobile_forensics.native_schemas import AcquisitionMetadata, ExportCreate, JobCreate, NativeReviewCreate
from operia.mobile_forensics.service import scoped_case
from operia.shared.time import utcnow


def private(response: Response):
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(prefix="/native", dependencies=[Depends(private)])
read = require_permission("evidence:read")
write = require_permission("evidence:write")


def audit(db, action, user, case_id, entity_id):
    write_audit(db, action, "native_mobile", user, case_id=case_id,
                entity_type="native_mobile", entity_id=str(entity_id))


def scoped(db, model, item_id, case_id, user):
    scoped_case(db, case_id, user)
    item = db.get(model, item_id)
    if not item or item.case_id != case_id or item.organization_id != user.organization_id:
        raise HTTPException(404, "Recurso no encontrado en el caso y organización")
    return item


async def body_limited(request, maximum):
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > maximum:
            raise HTTPException(413, "Contenido supera la cuota admitida")
        body.extend(chunk)
    return bytes(body)


def result_of(job, db):
    if job.state not in DONE or not job.result_bytes:
        raise HTTPException(409, "El trabajo todavía no tiene un resultado completado")
    if sha256(job.result_bytes) != job.result_sha256:
        raise HTTPException(409, "Integridad del resultado alterada")
    acquisition = db.get(Acquisition, job.acquisition_id)
    if not acquisition or acquisition.case_id != job.case_id or acquisition.organization_id != job.organization_id or sha256(acquisition.original_bytes) != acquisition.sha256:
        raise HTTPException(409, "Integridad o ámbito de la adquisición alterados")
    if sha256(job.configuration_json.encode("utf-8")) != job.configuration_sha256:
        raise HTTPException(409, "Configuración alterada")
    configuration = json.loads(job.configuration_json)
    indicators = db.get(IndicatorSet, job.indicator_set_id) if job.indicator_set_id else None
    if job.indicator_set_id and (not indicators or indicators.case_id != job.case_id or
        indicators.organization_id != job.organization_id or sha256(indicators.original_bytes) != configuration["indicator_set_sha256"]):
        raise HTTPException(409, "Indicadores usados alterados o fuera del ámbito")
    try:
        value = read_json(job.result_bytes, limit=16 * 1024 * 1024)
        if value["source_manifest"][0]["sha256"] != acquisition.sha256:
            raise HTTPException(409, "El resultado ya no corresponde al original registrado")
        return value
    except (EngineInputError, KeyError, TypeError, IndexError):
        raise HTTPException(409, "Resultado incompatible o alterado")


def acquisition_view(item):
    return {"id": item.id, "device_id": item.device_id, "case_id": item.case_id,
        "organization_id": item.organization_id, "operator_id": item.operator_id,
        "filename": item.filename, "format": item.format, "platform": item.platform,
        "sha256": item.sha256, "size_bytes": len(item.original_bytes), "created_at": item.created_at,
        "metadata": json.loads(item.metadata_json), "origin": "authorized_input_declared",
        "hash_scope": "Identidad de bytes recibidos; no acredita autenticidad anterior ni imagen física completa."}


def job_view(item):
    return {key: getattr(item, key) for key in ("id", "case_id", "organization_id", "acquisition_id",
        "indicator_set_id", "state", "created_at", "started_at", "finished_at", "heartbeat_at",
        "cancel_requested", "error_code", "configuration_sha256", "result_sha256")} | {
        "origin": "operia_native", "configuration": json.loads(item.configuration_json)}


def commit_unique(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Registro duplicado o referencia inconsistente; recargá la lista")


def capacity(db, user, added_bytes, lock=True):
    try:
        if lock:
            begin_write(db)
        ensure_capacity(db, user.organization_id, added_bytes)
    except RuntimeError as error:
        db.rollback()
        raise HTTPException(409, str(error))


@router.get("/capabilities")
def engine_capabilities(user: CurrentUser = Depends(read)):
    return capabilities() | {"worker_required": True, "os_sandbox": False}


@router.get("/cases/{case_id}/acquisitions")
def acquisitions(case_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(read)):
    scoped_case(db, case_id, user)
    return [acquisition_view(item) for item in db.query(Acquisition).filter_by(
        case_id=case_id, organization_id=user.organization_id).order_by(Acquisition.id.desc()).all()]


@router.post("/cases/{case_id}/acquisitions")
async def preserve(case_id: int, request: Request, db: Session = Depends(get_db), user: CurrentUser = Depends(write)):
    scoped_case(db, case_id, user)
    try:
        envelope = read_json(await body_limited(request, 7 * 1024 * 1024), limit=7 * 1024 * 1024)
        if not isinstance(envelope, dict) or set(envelope) != {"device_id", "metadata", "filename", "format", "content_base64"}:
            raise EngineInputError("Contrato de adquisición incompatible")
        metadata = AcquisitionMetadata.model_validate(envelope["metadata"])
        if type(envelope["device_id"]) is not int:
            raise EngineInputError("Identificador de dispositivo inválido")
        device = scoped(db, MobileDevice, envelope["device_id"], case_id, user)
        if not isinstance(envelope["filename"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}", envelope["filename"]):
            raise EngineInputError("Nombre inseguro: usá hasta 120 caracteres simples, sin rutas")
        if not any(reader["format"] == envelope["format"] and reader["platform"] == device.platform for reader in capabilities()["readers"]):
            raise EngineInputError("Formato no soportado para esta plataforma")
        raw = base64.b64decode(envelope["content_base64"], validate=True)
    except (ValueError, TypeError, ValidationError) as error:
        raise HTTPException(422, str(error) if isinstance(error, EngineInputError) else "Metadatos o base64 inválidos")
    if len(raw) > MAX_SOURCE_BYTES:
        raise HTTPException(413, "La adquisición supera 5 MiB")
    capacity(db, user, len(raw))
    item = Acquisition(case_id=case_id, organization_id=user.organization_id, device_id=device.id,
        operator_id=user.id, filename=envelope["filename"], format=envelope["format"], platform=device.platform,
        metadata_json=canonical_bytes(metadata.model_dump()).decode("utf-8"), sha256=sha256(raw), original_bytes=raw)
    db.add(item)
    # Unique violation can occur at flush too, so transaction includes audit below.
    try:
        db.flush()
        audit(db, "native_acquisition_preserved", user, case_id, item.id)
        commit_unique(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Adquisición ya preservada para ese dispositivo y formato")
    db.refresh(item)
    return acquisition_view(item)


@router.get("/cases/{case_id}/acquisitions/{acquisition_id}/original")
def original(case_id: int, acquisition_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(read)):
    item = scoped(db, Acquisition, acquisition_id, case_id, user)
    if sha256(item.original_bytes) != item.sha256:
        raise HTTPException(409, "Integridad original alterada")
    audit(db, "native_original_downloaded", user, case_id, item.id)
    db.commit()
    return Response(item.original_bytes, media_type="application/octet-stream", headers={"Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff", "Content-Disposition": f'attachment; filename="{item.filename}"'})


@router.post("/cases/{case_id}/indicator-sets")
async def indicator_set(case_id: int, request: Request, db: Session = Depends(get_db), user: CurrentUser = Depends(write)):
    scoped_case(db, case_id, user)
    raw = await body_limited(request, 256 * 1024)
    try:
        value = validate_indicators(raw)
    except EngineInputError as error:
        raise HTTPException(422, str(error))
    capacity(db, user, len(raw))
    item = IndicatorSet(organization_id=user.organization_id, case_id=case_id, created_by=user.id,
        original_bytes=raw, sha256=sha256(raw), version=value["version"], source=value["source"], terms=value["terms"])
    db.add(item)
    audit(db, "native_indicator_set_preserved", user, case_id, "new")
    commit_unique(db)
    return {"id": item.id, "sha256": item.sha256, "validation": "estructura_validada_fuente_declarada"}


@router.get("/cases/{case_id}/indicator-sets")
def indicator_sets(case_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(read)):
    scoped_case(db, case_id, user)
    return [{"id": item.id, "sha256": item.sha256, "version": item.version, "source": item.source,
        "terms": item.terms, "created_at": item.created_at, "validation": "estructura_validada_fuente_declarada"}
        for item in db.query(IndicatorSet).filter_by(case_id=case_id, organization_id=user.organization_id).all()]


@router.post("/cases/{case_id}/jobs")
def enqueue(case_id: int, payload: JobCreate, db: Session = Depends(get_db), user: CurrentUser = Depends(write)):
    scoped_case(db, case_id, user)
    capacity(db, user, 0)
    acquisition = scoped(db, Acquisition, payload.acquisition_id, case_id, user)
    indicators = scoped(db, IndicatorSet, payload.indicator_set_id, case_id, user) if payload.indicator_set_id else None
    if sha256(acquisition.original_bytes) != acquisition.sha256 or (indicators and sha256(indicators.original_bytes) != indicators.sha256):
        raise HTTPException(409, "Integridad de entrada alterada")
    configuration = {"engine_version": ENGINE_VERSION, "python_version": platform.python_version(),
        "source_sha256": acquisition.sha256, "indicator_set_sha256": indicators.sha256 if indicators else None,
        "demo_rules": payload.demo_rules, "format": acquisition.format}
    raw_config = canonical_bytes(configuration)
    configuration_hash = sha256(raw_config)
    existing = db.query(ExaminationJob).filter_by(acquisition_id=acquisition.id, configuration_sha256=configuration_hash).first()
    if existing:
        return job_view(existing)
    if db.query(ExaminationJob).filter_by(organization_id=user.organization_id).filter(
            ExaminationJob.state.in_(("pendiente", "preparando", "ejecutando"))).count() >= 25:
        raise HTTPException(409, "La organización alcanzó el máximo de 25 trabajos activos")
    job = ExaminationJob(organization_id=user.organization_id, case_id=case_id, acquisition_id=acquisition.id,
        indicator_set_id=payload.indicator_set_id, created_by=user.id, configuration_json=raw_config.decode(),
        configuration_sha256=configuration_hash, state="pendiente")
    db.add(job)
    try:
        db.flush()
        event(db, job, "pendiente")
        audit(db, "native_job_queued", user, case_id, job.id)
        commit_unique(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "El trabajo ya fue solicitado; recargá la lista")
    return job_view(job)


@router.get("/cases/{case_id}/jobs")
def jobs(case_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(read)):
    scoped_case(db, case_id, user)
    return [job_view(item) for item in db.query(ExaminationJob).filter_by(case_id=case_id,
        organization_id=user.organization_id).order_by(ExaminationJob.id.desc()).all()]


@router.get("/cases/{case_id}/jobs/{job_id}")
def detail(case_id: int, job_id: int, offset: int = 0, db: Session = Depends(get_db), user: CurrentUser = Depends(read)):
    job = scoped(db, ExaminationJob, job_id, case_id, user)
    if offset < 0:
        raise HTTPException(422, "Offset negativo")
    result = result_of(job, db) if job.state in DONE else None
    if result:
        result["counts"] = {key: len(result[key]) for key in ("artifacts", "alerts", "timeline")}
        for key in ("artifacts", "observations", "alerts", "timeline"):
            result[key] = result[key][offset:offset + 100]
    return {"job": job_view(job), "result": result, "offset": offset,
        "reviews": db.query(ReviewRevision).filter_by(job_id=job_id).order_by(ReviewRevision.id).all(),
        "events": db.query(JobEvent).filter_by(job_id=job_id).order_by(JobEvent.id).all(),
        "exports": [{"id": item.id, "format": item.format, "sha256": item.sha256, "review_id": item.review_id}
            for item in db.query(ExportRecord).filter_by(job_id=job_id).order_by(ExportRecord.id).all()]}


@router.post("/cases/{case_id}/jobs/{job_id}/cancel")
def cancel(case_id: int, job_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(write)):
    job = scoped(db, ExaminationJob, job_id, case_id, user)
    if job.state not in ("pendiente", "preparando", "ejecutando"):
        raise HTTPException(409, "El trabajo ya está en un estado terminal")
    job.cancel_requested = True
    if job.state == "pendiente":
        event(db, job, "cancelado", "operator_cancelled")
        job.finished_at = utcnow()
    audit(db, "native_job_cancel_requested", user, case_id, job.id)
    db.commit()
    return job_view(job)


@router.post("/cases/{case_id}/jobs/{job_id}/retry")
def retry(case_id: int, job_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(write)):
    job = scoped(db, ExaminationJob, job_id, case_id, user)
    if job.state not in ("interrumpido", "fallido", "cancelado"):
        raise HTTPException(409, "Solo se reintentan trabajos sin resultado completado")
    job.cancel_requested, job.error_code, job.claim_token = False, "", ""
    job.started_at = job.finished_at = job.heartbeat_at = None
    event(db, job, "pendiente", "retry_requested")
    audit(db, "native_job_retried", user, case_id, job.id)
    db.commit()
    return job_view(job)


@router.post("/cases/{case_id}/jobs/{job_id}/reviews")
def review(case_id: int, job_id: int, payload: NativeReviewCreate,
           db: Session = Depends(get_db), user: CurrentUser = Depends(write)):
    job = scoped(db, ExaminationJob, job_id, case_id, user)
    result = result_of(job, db)
    available = {artifact["id"] for artifact in result["artifacts"]}
    if len(set(payload.artifact_ids)) != len(payload.artifact_ids) or not set(payload.artifact_ids) <= available:
        raise HTTPException(422, "Referencias duplicadas o ajenas al resultado")
    if payload.conclusion != "inconcluso" and not payload.artifact_ids:
        raise HTTPException(422, "La conclusión requiere artefactos identificados")
    if payload.conclusion == "compromiso_confirmado_por_revision_profesional":
        raise HTTPException(422, "Este MVP de una fuente no admite confirmación: falta corroboración técnica independiente")
    if payload.conclusion == "sin_indicios_en_el_alcance_examinado" and (
        not job.indicator_set_id or result["alerts"] or result["detection_status"] != "sin_coincidencias_en_reglas_aplicadas" or
        any(source["status"] != "analizado" or source["excluded"] for source in result["coverage"]["sources"])):
        raise HTTPException(422, "Cobertura, datos o reglas insuficientes para esa conclusión")
    item = ReviewRevision(job_id=job_id, reviewer_id=user.id, reviewer_name=user.name,
        result_sha256=job.result_sha256, content_json=canonical_bytes(payload.model_dump()).decode())
    db.add(item)
    audit(db, "native_review_appended", user, case_id, job_id)
    db.commit()
    db.refresh(item)
    return item


@router.post("/cases/{case_id}/jobs/{job_id}/exports")
def export(case_id: int, job_id: int, payload: ExportCreate, db: Session = Depends(get_db), user: CurrentUser = Depends(write)):
    job = scoped(db, ExaminationJob, job_id, case_id, user)
    result = result_of(job, db)
    acquisition = scoped(db, Acquisition, job.acquisition_id, case_id, user)
    if sha256(acquisition.original_bytes) != acquisition.sha256:
        raise HTTPException(409, "Integridad del original alterada")
    reviews = db.query(ReviewRevision).filter_by(job_id=job_id).order_by(ReviewRevision.id).all()
    indicators = scoped(db, IndicatorSet, job.indicator_set_id, case_id, user) if job.indicator_set_id else None
    if indicators and sha256(indicators.original_bytes) != indicators.sha256:
        raise HTTPException(409, "Integridad de indicadores alterada")
    item = ExportRecord(job_id=job_id, review_id=reviews[-1].id if reviews else None,
        created_by=user.id, format=payload.format, content=b"", sha256="")
    db.add(item)
    db.flush()
    snapshot = {"schema": "operia.mobile-report/1", "report_id": item.id, "generated_at_utc": item.created_at,
        "case_id": case_id, "organization_id": user.organization_id, "job": job_view(job),
        "acquisition": acquisition_view(acquisition), "device": scoped(db, MobileDevice, acquisition.device_id, case_id, user),
        "result_sha256": job.result_sha256, "result": result, "review_id": item.review_id,
        "reviews": reviews, "indicator_original_base64": base64.b64encode(indicators.original_bytes).decode() if indicators else None,
        "summary": {"artifacts": len(result["artifacts"]), "alerts": len(result["alerts"]), "coverage": result["coverage"]["state"]},
        "recommendations": "Revisión profesional y corroboración; contención y recuperación son un flujo separado.",
        "limitations": "Validación sintética. No garantiza limpieza, atribución ni admisibilidad judicial."}
    content = canonical_bytes(jsonable_encoder(snapshot)) if payload.format == "json" else timeline_csv(result)
    capacity(db, user, len(content), lock=False)
    item.content = content
    item.sha256 = sha256(item.content)
    audit(db, "native_export_created", user, case_id, job_id)
    db.commit()
    return {"id": item.id, "sha256": item.sha256, "review_id": item.review_id, "format": item.format}


@router.get("/cases/{case_id}/jobs/{job_id}/exports/{export_id}")
def download(case_id: int, job_id: int, export_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(read)):
    scoped(db, ExaminationJob, job_id, case_id, user)
    item = db.get(ExportRecord, export_id)
    if not item or item.job_id != job_id:
        raise HTTPException(404, "Exportación no encontrada")
    if sha256(item.content) != item.sha256:
        raise HTTPException(409, "Integridad de la exportación alterada")
    audit(db, "native_export_downloaded", user, case_id, job_id)
    db.commit()
    return Response(item.content, media_type="application/json" if item.format == "json" else "text/csv",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f'attachment; filename="operia-native-{job_id}-{item.id}.{item.format}"'})
