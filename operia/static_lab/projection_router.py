"""Explicit transfer of reviewed static observations. Never overwrites an earlier report."""
import json
from fastapi import Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import Field
from sqlalchemy import func
from sqlalchemy.orm import Session
from operia.static_lab.router import router
from operia.static_lab.jobs_router import scoped_job
from operia.static_lab.models import StaticReview, StaticProjection
from operia.static_lab.contracts import StrictModel, digest, parse_report
from operia.core.database import get_db
from operia.identity.dependencies import require_permission
from operia.identity.case_access import require_case
from operia.forensic_jobs.storage_limits import begin_write
from operia.cases.models import Finding
from operia.reports.models import Report, ReportSection, ReportVersion
from operia.evidence.models import ChainOfCustodyAction
from operia.audit.service import write_audit

class ProjectionCreate(StrictModel):
    review_version: int = Field(gt=0)
    observation_ids: list[str] = Field(min_length=1,max_length=200)

def canonical(value):
    return json.dumps(jsonable_encoder(value),ensure_ascii=True,sort_keys=True,separators=(',',':')).encode()

def view(item):
    if digest(item.snapshot_bytes)!=item.snapshot_sha256:
        raise HTTPException(409,'Integridad de incorporación alterada')
    return {key:getattr(item,key) for key in ('id','job_id','review_id','finding_id','report_id','snapshot_sha256','recorded_at')}

@router.post('/cases/{case_id}/jobs/{job_id}/projections')
def project(case_id:int,job_id:int,payload:ProjectionCreate,db:Session=Depends(get_db),
        user=Depends(require_permission('evidence:write')),writer=Depends(require_permission('cases:write')),
        reporter=Depends(require_permission('reports:write'))):
    begin_write(db)
    for capability in ('analysis','evidence','reports'): require_case(db,user,case_id,capability)
    job=scoped_job(db,user,case_id,job_id)
    if job.state!='completed' or not job.result_bytes or digest(job.result_bytes)!=job.result_sha256:
        raise HTTPException(409,'Resultado íntegro y completo requerido')
    review=db.query(StaticReview).filter_by(job_id=job.id).order_by(StaticReview.version.desc()).first()
    if not review or review.version!=payload.review_version or review.decision!='accepted' or review.result_sha256!=job.result_sha256:
        raise HTTPException(409,'Se requiere la última revisión aceptada del resultado')
    result=parse_report(job.result_bytes)
    ids=sorted(set(payload.observation_ids)); available={o.id:o.model_dump() for o in result.observations}
    if len(ids)!=len(payload.observation_ids) or not set(ids)<=available.keys():
        raise HTTPException(422,'Selección duplicada o ajena al resultado revisado')
    selection_hash=digest(canonical(ids))
    old=db.query(StaticProjection).filter_by(job_id=job_id,review_id=review.id,selection_sha256=selection_hash).first()
    if old: return view(old)
    if db.query(StaticProjection).filter_by(case_id=case_id).count()>=1000:
        raise HTTPException(409,'Cuota de incorporaciones alcanzada')
    observations=[available[key] for key in ids]
    snapshot=canonical({'schema':'operia.static-projection/1','case_id':case_id,'organization_id':user.organization_id,
        'job_id':job.id,'evidence_id':job.evidence_id,'source_sha256':job.source_sha256,'result_sha256':job.result_sha256,
        'runtime_identity':job.runtime_identity,'review':{'id':review.id,'version':review.version,'actor_id':review.actor_id,
        'decision':review.decision,'rationale':review.rationale,'recorded_at':review.recorded_at},
        'observations':observations,'limitations':result.limitations,'provider':result.provider,'provider_version':result.provider_version,
        'provider_revision':result.provider_revision,'actor_id':user.id})
    finding=Finding(organization_id=user.organization_id,case_id=case_id,evidence_id=job.evidence_id,
        title=f'Observaciones estáticas del trabajo {job.id}, revisión {review.version}',technical_finding=canonical(observations).decode(),
        explanation=review.rationale,confidence_level='bajo',weaknesses_or_limitations=result.limitations,
        tools_used=f'{result.provider} {result.provider_version}; {result.provider_revision}',
        supporting_evidence=f'Evidencia #{job.evidence_id}; fuente {job.source_sha256}; resultado {job.result_sha256}',
        status='requiere corroboracion')
    # JSON is displayed as data, never rendered as executable HTML or fetched links.
    def literal(value):
        return json.dumps(value,ensure_ascii=False).replace('`','\\u0060').replace('<','\\u003c').replace('>','\\u003e')
    readable = "\n".join(f"{index}. {literal(o['text'])} | {o['member']} | offset {o['offset']} bytes | {o['id']}" for index,o in enumerate(observations,1))
    markdown = (f"# Análisis estático revisado\n\nBorrador: no constituye aprobación de informe ni atribución.\n\n"
        f"Expediente #{case_id} · Evidencia #{job.evidence_id} · Trabajo #{job.id}\n\n"
        f"Proveedor: {result.provider} {result.provider_version} · {result.provider_revision}\n\n"
        f"SHA-256 fuente: {job.source_sha256}\n\nSHA-256 resultado: {job.result_sha256}\n\n"
        f"## Observaciones seleccionadas\n\n```text\n{readable}\n```\n\n"
        f"## Revisión profesional preservada\n\nVersión {review.version} · Actor #{review.actor_id}\n\n```text\n{literal(review.rationale)}\n```\n\n"
        f"## Alcance y límites\n\n```text\n{literal(result.limitations)}\n```\n\n"
        "## Instantánea de procedencia\n\n```json\n" + snapshot.decode().replace('`','\\u0060').replace('<','\\u003c').replace('>','\\u003e') + "\n```\n")

    report=Report(organization_id=user.organization_id,case_id=case_id,title=f'Laboratorio estático {job.id} / revisión {review.version}',
        author=user.name,status='borrador',template_used='CPython AST revisado',markdown_content=markdown)
    db.add_all([finding,report]); db.flush()
    db.add_all([ReportSection(organization_id=user.organization_id,report_id=report.id,order_index=1,title='Observaciones y revisión preservadas',content=markdown),
        ReportVersion(organization_id=user.organization_id,report_id=report.id,version_number='1.0',user=user.name,
            change_summary='Incorporación inmutable de observaciones estáticas revisadas',markdown_snapshot=markdown)])
    item=StaticProjection(organization_id=user.organization_id,case_id=case_id,job_id=job.id,review_id=review.id,
        finding_id=finding.id,report_id=report.id,actor_id=user.id,selection_sha256=selection_hash,
        snapshot_sha256=digest(snapshot),snapshot_bytes=snapshot)
    db.add(item)
    db.add(ChainOfCustodyAction(case_id=case_id,evidence_id=job.evidence_id,action_type='incorporacion_estatica_revisada',
        detailed_description=f'Observaciones revisadas del trabajo #{job.id}; hallazgo #{finding.id}; informe #{report.id}',
        hash_before=job.source_sha256,hash_after=job.source_sha256,tool_used='OPERIA static projection/1'))
    write_audit(db,'static_observations_projected','static-lab',user,case_id=case_id,entity_type='static_job',entity_id=str(job.id))
    db.commit(); return view(item)

@router.get('/cases/{case_id}/jobs/{job_id}/projections')
def list_projections(case_id:int,job_id:int,db:Session=Depends(get_db),user=Depends(require_permission('evidence:read'))):
    scoped_job(db,user,case_id,job_id)
    return [view(item) for item in db.query(StaticProjection).filter_by(job_id=job_id,case_id=case_id).order_by(StaticProjection.id).all()]
