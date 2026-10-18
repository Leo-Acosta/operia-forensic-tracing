"""Scoped persistent provider jobs and append-only professional review."""
from fastapi import Depends, HTTPException
from pydantic import ConfigDict, Field
from typing import Literal
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from operia.static_lab.router import router
from operia.static_lab.models import StaticJob, StaticReview, StaticJobEvent
from operia.static_lab.contracts import digest, parse_report, StrictModel
from operia.static_lab import runtime
from operia.core.database import get_db
from operia.identity.case_access import require_case
from operia.identity.dependencies import require_permission
from operia.forensic_jobs.storage_limits import begin_write
from operia.evidence.models import Evidence
from operia.audit.service import write_audit

class JobCreate(StrictModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    request_key: str=Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    provider: Literal['cpython-ast']='cpython-ast'

class ReviewCreate(StrictModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    expected_version: int=Field(ge=0)
    decision: Literal['accepted','rejected','needs_corroboration']
    rationale: str=Field(min_length=10,max_length=4000)

def scoped_job(db,user,case_id,job_id):
    require_case(db,user,case_id)
    job=db.query(StaticJob).filter_by(id=job_id,case_id=case_id,organization_id=user.organization_id).first()
    if not job: raise HTTPException(404,'Trabajo no disponible')
    return job

def summary(job):
    return {'id':job.id,'case_id':job.case_id,'evidence_id':job.evidence_id,'state':job.state,'error_code':job.error_code,
        'origin':'local-static-provider','provider':'cpython-ast','runtime_identity':job.runtime_identity,'source_sha256':job.source_sha256,
        'result_sha256':job.result_sha256,'provider_execution_verified':job.state=='completed'}

@router.post('/cases/{case_id}/evidence/{evidence_id}/jobs')
def enqueue(case_id:int,evidence_id:int,payload:JobCreate,db:Session=Depends(get_db),user=Depends(require_permission('evidence:write'))):
    require_case(db,user,case_id,'analysis'); require_case(db,user,case_id,'evidence')
    begin_write(db)
    require_case(db,user,case_id,'analysis'); require_case(db,user,case_id,'evidence')
    old=db.query(StaticJob).filter_by(case_id=case_id,evidence_id=evidence_id,request_key=payload.request_key).first()
    if old: return summary(old)
    evidence=db.query(Evidence).filter_by(id=evidence_id,case_id=case_id).first()
    if not evidence: raise HTTPException(404,'Evidencia no disponible')
    from operia.evidence.router import preserved_source,safe_path
    raw=preserved_source(db,evidence)
    if raw is None:
        if not evidence.file_location: raise HTTPException(409,'Muestra preservada requerida')
        path=safe_path(evidence.file_location,case_id)
        try:
            with path.open('rb') as stream: raw=stream.read(131073)
        except OSError: raise HTTPException(409,'No se pudo leer la muestra')
    if len(raw)>131072: raise HTTPException(413,'Muestra excede 128 KiB')
    if digest(raw)!=evidence.sha256_hash: raise HTTPException(409,'Integridad de muestra alterada')
    table=StaticJob.__table__
    count=db.execute(select(func.count()).select_from(table).where(table.c.organization_id==user.organization_id)).scalar_one()
    if count>=1000: raise HTTPException(409,'Cuota de trabajos alcanzada')
    job=StaticJob(organization_id=user.organization_id,case_id=case_id,evidence_id=evidence_id,actor_id=user.id,
        request_key=payload.request_key,source_bytes=raw,source_sha256=digest(raw),runtime_identity=runtime.identity())
    db.add(job); db.flush(); db.add(StaticJobEvent(job_id=job.id,state='queued'))
    write_audit(db,'static_job_queued','static-lab',user,case_id=case_id,entity_type='static_job',entity_id=str(job.id))
    db.commit(); return summary(job)

@router.get('/cases/{case_id}/jobs/{job_id}')
def read_job(case_id:int,job_id:int,db:Session=Depends(get_db),user=Depends(require_permission('evidence:read'))):
    job=scoped_job(db,user,case_id,job_id)
    report=None
    if job.result_bytes is not None:
        if digest(job.result_bytes)!=job.result_sha256: raise HTTPException(409,'Integridad del resultado alterada')
        report=parse_report(job.result_bytes).model_dump()
    reviews=db.query(StaticReview).filter_by(job_id=job.id).order_by(StaticReview.version).all()
    events=db.query(StaticJobEvent).filter_by(job_id=job.id).order_by(StaticJobEvent.id).all()
    return {**summary(job),'report':report,'reviews':[{'version':r.version,'actor_id':r.actor_id,'decision':r.decision,'rationale':r.rationale,'result_sha256':r.result_sha256,'recorded_at':r.recorded_at} for r in reviews],
        'events':[{'state':e.state,'reason':e.reason,'recorded_at':e.recorded_at} for e in events]}

@router.post('/cases/{case_id}/jobs/{job_id}/cancel')
def cancel(case_id:int,job_id:int,db:Session=Depends(get_db),user=Depends(require_permission('evidence:write'))):
    require_case(db,user,case_id,'analysis'); begin_write(db); job=scoped_job(db,user,case_id,job_id)
    if job.state not in ('queued','preparing','running'): return summary(job)
    job.cancel_requested=1
    if job.state=='queued':
        job.state='cancelled'; db.add(StaticJobEvent(job_id=job.id,state='cancelled',reason='operator_cancelled'))
    write_audit(db,'static_job_cancel_requested','static-lab',user,case_id=case_id,entity_id=str(job.id)); db.commit(); return summary(job)

@router.post('/cases/{case_id}/jobs/{job_id}/reviews')
def review(case_id:int,job_id:int,payload:ReviewCreate,db:Session=Depends(get_db),user=Depends(require_permission('evidence:write'))):
    require_case(db,user,case_id,'review'); begin_write(db); job=scoped_job(db,user,case_id,job_id)
    if job.state!='completed' or not job.result_bytes or digest(job.result_bytes)!=job.result_sha256:
        raise HTTPException(409,'Resultado completo e íntegro requerido')
    latest=db.query(func.max(StaticReview.version)).filter_by(job_id=job_id).scalar() or 0
    if latest!=payload.expected_version: raise HTTPException(409,'Revisión concurrente; actualizar versión')
    if latest>=100: raise HTTPException(409,'Cuota de revisiones alcanzada')
    item=StaticReview(organization_id=user.organization_id,case_id=case_id,job_id=job_id,actor_id=user.id,
        version=latest+1,result_sha256=job.result_sha256,decision=payload.decision,rationale=payload.rationale)
    db.add(item); write_audit(db,'static_review_recorded','static-lab',user,case_id=case_id,entity_type='static_job',entity_id=str(job.id)); db.commit()
    return {'version':item.version,'decision':item.decision,'result_sha256':item.result_sha256}

@router.get('/cases/{case_id}/jobs')
def list_jobs(case_id:int,db:Session=Depends(get_db),user=Depends(require_permission('evidence:read'))):
    require_case(db,user,case_id)
    return [summary(job) for job in db.query(StaticJob).filter_by(case_id=case_id,organization_id=user.organization_id).order_by(StaticJob.id.desc()).limit(100).all()]
