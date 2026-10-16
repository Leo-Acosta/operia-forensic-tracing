"""Explicit, passive projections of professionally selected artifacts."""
import ipaddress
import json
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.encoders import jsonable_encoder
from pydantic import Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from operia.core.database import get_db
from operia.cases.models import Finding, Hypothesis
from operia.geo_trace.models import GeoTraceAnalysis, GeoTarget
from operia.forensic_jobs.models import ExaminationJob, EvidenceIntegration, AnalysisProjection
from operia.forensic_engine.canonical import canonical_bytes, sha256
from operia.identity.dependencies import CurrentUser, require_permission
from operia.mobile_forensics.schemas import StrictModel
from operia.mobile_forensics.native_router import scoped, result_of, capacity, audit, private
from operia.shared.time import utcnow

router = APIRouter(prefix="/native", dependencies=[Depends(private)])

class ProjectionCreate(StrictModel):
    integration_id: int = Field(gt=0)
    artifact_ids: list[str] = Field(min_length=1, max_length=100)
    hypothesis_text: str = Field(min_length=20, max_length=4000)
    facts_to_prove: str = Field(min_length=20, max_length=4000)
    create_geo: bool = False


def passive_targets(artifacts):
    targets = {}
    for artifact in artifacts:
        normalized = artifact.get("normalized")
        urls = normalized.get("urls", []) if isinstance(normalized, dict) else []
        for url in urls:
            try:
                parsed = urlsplit(url)
                if len(url) > 2048 or parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or any(ord(c) < 32 for c in url):
                    continue
                host = parsed.hostname.encode("idna").decode("ascii").lower()
                port = parsed.port  # Reject malformed ports without resolving DNS.
                ip = str(ipaddress.ip_address(host)) if ":" in host or host.replace(".", "").isdigit() else None
            except (ValueError, UnicodeError):
                continue
            item = targets.setdefault(url, {"url": url, "host": host, "ip": ip, "artifact_ids": []})
            item["artifact_ids"].append(artifact["id"])
    return list(targets.values())


def view(item):
    return {key: getattr(item, key) for key in ("id", "integration_id", "finding_id", "hypothesis_id", "geo_analysis_id", "snapshot_sha256", "created_at")}


@router.post("/cases/{case_id}/jobs/{job_id}/projections")
def project(case_id: int, job_id: int, payload: ProjectionCreate, db: Session = Depends(get_db),
            user: CurrentUser = Depends(require_permission("evidence:write")),
            case_writer: CurrentUser = Depends(require_permission("cases:write"))):
    job = scoped(db, ExaminationJob, job_id, case_id, user)
    result = result_of(job, db)
    link = scoped(db, EvidenceIntegration, payload.integration_id, case_id, user)
    if link.job_id != job_id:
        raise HTTPException(404, "Incorporacion ajena al examen")
    if sha256(link.snapshot_bytes) != link.snapshot_sha256:
        raise HTTPException(409, "Instantanea de evidencia alterada")
    source = json.loads(link.snapshot_bytes)
    if source["result_sha256"] != job.result_sha256:
        raise HTTPException(409, "Resultado distinto del incorporado")
    review = json.loads(source["review"]["content_json"])
    selected = set(payload.artifact_ids)
    available = {a["id"]: a for a in source["result"]["artifacts"]}
    if len(selected) != len(payload.artifact_ids) or not selected <= set(review["artifact_ids"]) or not selected <= available.keys():
        raise HTTPException(422, "Seleccion duplicada o no respaldada por la revision incorporada")
    artifacts = [available[key] for key in sorted(selected)]
    targets = passive_targets(artifacts) if payload.create_geo else []
    if payload.create_geo and not targets:
        raise HTTPException(422, "La seleccion no contiene URLs utilizables para Geo Trace pasivo")
    request = payload.model_dump() | {"artifact_ids": sorted(selected)}
    request_hash = sha256(canonical_bytes(request))
    existing = db.query(AnalysisProjection).filter_by(integration_id=link.id, request_sha256=request_hash).first()
    if existing:
        if sha256(existing.snapshot_bytes) != existing.snapshot_sha256:
            raise HTTPException(409, "Proyeccion alterada")
        return view(existing)
    snapshot = canonical_bytes(jsonable_encoder({"schema": "operia.analysis-projection/1", "case_id": case_id,
        "organization_id": user.organization_id, "job_id": job_id, "integration_id": link.id,
        "integration_sha256": link.snapshot_sha256, "result_sha256": job.result_sha256,
        "review_id": link.review_id, "actor_id": user.id, "created_at": utcnow(), "request": request,
        "artifacts": artifacts, "geo_targets": targets, "limitations": "Observaciones e hipotesis por corroborar. URLs mencionadas no acreditan conexion, ubicacion ni identidad. Sin consultas externas."}))
    capacity(db, user, len(snapshot))
    finding = Finding(organization_id=user.organization_id, case_id=case_id, evidence_id=link.evidence_id,
        title=f"Observaciones del examen {job_id}, revision {link.review_id}",
        technical_finding=canonical_bytes(artifacts).decode(), explanation=review["rationale"],
        weaknesses_or_limitations=review["limitations"], confidence_level="bajo", tools_used="Motor propio OPERIA",
        supporting_evidence=f"Evidencia {link.evidence_id}; resultado {job.result_sha256}; incorporacion {link.snapshot_sha256}",
        status="requiere corroboracion")
    db.add(finding)
    db.flush()
    hypothesis = Hypothesis(organization_id=user.organization_id, case_id=case_id,
        title=f"Hipotesis profesional del examen {job_id}", description=payload.hypothesis_text,
        finding_ids=str(finding.id), evidence_ids=str(link.evidence_id), support_degree="bajo",
        alternative_hypotheses=review["alternatives"], error_risks=review["limitations"],
        facts_to_prove=payload.facts_to_prove, provisional_conclusion="No confirmada; requiere corroboracion independiente", status="abierta")
    db.add(hypothesis)
    geo = None
    if payload.create_geo:
        geo = GeoTraceAnalysis(case_id=case_id, title=f"Referencias pasivas del examen {job_id}",
            input_text=canonical_bytes(targets).decode(), summary="URLs mencionadas en artefactos seleccionados. Sin DNS, consultas, geolocalizacion ni atribucion.",
            evidence_hash=sha256(snapshot), status="observado_no_enriquecido")
        db.add(geo)
        db.flush()
        for item in targets:
            db.add(GeoTarget(analysis_id=geo.id, case_id=case_id, origin="motor_propio", url=item["url"],
                host=item["host"], ip=item["ip"], target_type="observado_no_enriquecido", risk="no_evaluado",
                confidence="no_evaluada", geo_source="sin_consulta", message=canonical_bytes({"artifact_ids": item["artifact_ids"], "result_sha256": job.result_sha256}).decode()))
    db.flush()
    item = AnalysisProjection(organization_id=user.organization_id, case_id=case_id, job_id=job_id,
        integration_id=link.id, finding_id=finding.id, hypothesis_id=hypothesis.id,
        geo_analysis_id=geo.id if geo else None, created_by=user.id, request_sha256=request_hash,
        snapshot_bytes=snapshot, snapshot_sha256=sha256(snapshot))
    db.add(item)
    audit(db, "native_analysis_projected", user, case_id, job_id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Proyeccion ya incorporada; recargar")
    return view(item)


@router.get("/cases/{case_id}/jobs/{job_id}/projections/{projection_id}")
def download_projection(case_id: int, job_id: int, projection_id: int, db: Session = Depends(get_db),
                        user: CurrentUser = Depends(require_permission("evidence:read"))):
    scoped(db, ExaminationJob, job_id, case_id, user)
    item = scoped(db, AnalysisProjection, projection_id, case_id, user)
    if item.job_id != job_id:
        raise HTTPException(404, "Proyeccion ajena al examen")
    if sha256(item.snapshot_bytes) != item.snapshot_sha256:
        raise HTTPException(409, "Integridad de proyeccion alterada")
    return Response(item.snapshot_bytes, media_type="application/json", headers={"Cache-Control": "no-store",
        "Content-Disposition": f'attachment; filename="operia-projection-{item.id}.json"'})
