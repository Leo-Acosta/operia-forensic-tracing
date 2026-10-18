"""Import only. No shell, provider, network, archive extraction or sample execution."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from operia.core.database import get_db
from operia.identity.dependencies import require_permission
from operia.identity.case_access import require_case
from operia.identity.isolation import enforce_scope
from operia.evidence.models import Evidence, ChainOfCustodyAction
from operia.audit.service import write_audit
from operia.forensic_jobs.storage_limits import begin_write
from operia.static_lab.models import StaticImport
from operia.static_lab.contracts import MAX_REPORT_BYTES, MAX_IMPORTS_PER_ORGANIZATION, parse_report, digest, normalized

router = APIRouter(prefix='/static-lab', dependencies=[Depends(enforce_scope)])

@router.get('/cases/{case_id}/providers')
def providers(case_id: int, db: Session = Depends(get_db), user=Depends(require_permission('evidence:read'))):
    require_case(db, user, case_id)
    from operia.static_lab import runtime
    from operia.static_lab.models import StaticJob
    ready = False
    try:
        runtime.verify(runtime.DEFAULT_ROOT / runtime.identity())
        ready = True
    except RuntimeError:
        pass
    validated = db.query(StaticJob.id).filter_by(case_id=case_id, state='completed').first() is not None
    return {'stage':'static-python-source','execution_enabled':ready,'sample_execution_enabled':False,
        'providers':[{'id':'cpython-ast','scope':'Python source UTF-8 only','runtime_identity':runtime.identity(),'ready':ready}],
        'import_schema':'operia-static-report/1','import_enabled':db.bind.dialect.name=='sqlite','real_provider_validated':validated}


def lookup(db, user, case_id, import_id):
    require_case(db, user, case_id)
    item = db.query(StaticImport).filter_by(id=import_id, case_id=case_id, organization_id=user.organization_id).first()
    if item is None:
        raise HTTPException(404, 'Resultado no disponible')
    if digest(item.raw_bytes) != item.raw_sha256 or digest(item.normalized_bytes) != item.normalized_sha256:
        raise HTTPException(409, 'Integridad del resultado alterada')
    return item

def summary(item):
    return {'id': item.id, 'case_id': item.case_id, 'evidence_id': item.evidence_id,
        'sample_sha256': item.sample_sha256, 'raw_sha256': item.raw_sha256,
        'normalized_sha256': item.normalized_sha256, 'recorded_at': item.recorded_at,
        'actor_id': item.actor_id, 'review_status': 'pending', 'origin': 'external-import', 'provider_execution_verified': False}

@router.post('/cases/{case_id}/evidence/{evidence_id}/imports')
async def import_result(case_id: int, evidence_id: int, request: Request, response: Response,
        db: Session = Depends(get_db), user=Depends(require_permission('evidence:write'))):
    response.headers['Cache-Control'] = 'no-store'
    require_case(db, user, case_id, 'analysis')
    require_case(db, user, case_id, 'evidence')
    if request.headers.get('content-type', '').split(';')[0] != 'application/json':
        raise HTTPException(415, 'Se requiere application/json')
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > MAX_REPORT_BYTES:
            raise HTTPException(413, 'Informe excede el límite')
        raw.extend(chunk)
    try:
        report = parse_report(bytes(raw))
    except ValueError:
        raise HTTPException(422, 'Informe estático inválido')
    if db.bind.dialect.name != 'sqlite':
        raise HTTPException(503, 'Importación estática requiere SQLite validado')
    begin_write(db)
    evidence = db.query(Evidence).filter_by(id=evidence_id, case_id=case_id).first()
    if not evidence:
        raise HTTPException(404, 'Evidencia no disponible')
    if not evidence.sha256_hash or evidence.sha256_hash != report.sample_sha256:
        raise HTTPException(409, 'Hash de muestra incompatible con evidencia')
    from operia.evidence.router import preserved_source, safe_path
    import hashlib
    source = preserved_source(db, evidence)
    if source is not None:
        actual = digest(source)
    else:
        if not evidence.file_location:
            raise HTTPException(409, 'Se requiere muestra preservada con archivo verificable')
        try:
            path = safe_path(evidence.file_location, case_id)
            if not path.is_file() or path.stat().st_size > 33554432:
                raise HTTPException(409, 'Muestra ausente o fuera del límite de 32 MiB')
            hasher, size = hashlib.sha256(), 0
            with path.open('rb') as stream:
                while chunk := stream.read(65536):
                    size += len(chunk)
                    if size > 33554432:
                        raise HTTPException(409, 'Muestra fuera del límite')
                    hasher.update(chunk)
            actual = hasher.hexdigest()
        except OSError:
            raise HTTPException(409, 'No se pudo verificar la muestra preservada')
    if actual != report.sample_sha256:
        raise HTTPException(409, 'Integridad de muestra alterada')
    raw = bytes(raw)
    old = db.query(StaticImport).filter_by(case_id=case_id, evidence_id=evidence_id,
        organization_id=user.organization_id, raw_sha256=digest(raw)).first()
    if old:
        lookup(db, user, case_id, old.id)
        return summary(old)
    # Raw SQL deliberately counts the entire organization, including unreadable
    # cases, without returning counts to the caller; the writer lock serializes it.
    total = db.execute(select(func.count()).select_from(StaticImport.__table__).where(
        StaticImport.__table__.c.organization_id == user.organization_id)).scalar_one()
    if total >= MAX_IMPORTS_PER_ORGANIZATION:
        raise HTTPException(409, 'Cuota de importaciones alcanzada')
    canonical = normalized(report)
    if len(canonical) > MAX_REPORT_BYTES:
        raise HTTPException(413, 'Resultado normalizado excede el límite')
    item = StaticImport(organization_id=user.organization_id, case_id=case_id,
        evidence_id=evidence_id, actor_id=user.id, sample_sha256=report.sample_sha256,
        raw_sha256=digest(raw), normalized_sha256=digest(canonical), raw_bytes=raw, normalized_bytes=canonical)
    db.add(item)
    db.flush()
    db.add(ChainOfCustodyAction(case_id=case_id, evidence_id=evidence_id,
        action_type='importacion_resultado_estatico', detailed_description=f'Importación externa #{item.id}; pendiente de revisión humana',
        tool_used='OPERIA static-import/1', hash_before=evidence.sha256_hash, hash_after=evidence.sha256_hash))
    write_audit(db, 'static_result_imported', 'static-lab', user, case_id=case_id,
        entity_type='static_import', entity_id=str(item.id), details='Resultado externo pendiente de revisión; no se ejecutó muestra')
    db.commit()
    return summary(item)

@router.get('/cases/{case_id}/imports/{import_id}')
def read_result(case_id: int, import_id: int, response: Response, db: Session = Depends(get_db), user=Depends(require_permission('evidence:read'))):
    response.headers['Cache-Control'] = 'no-store'
    item = lookup(db, user, case_id, import_id)
    import json
    return {**summary(item), 'report': json.loads(item.normalized_bytes)}

@router.get('/cases/{case_id}/imports/{import_id}/original')
def original(case_id: int, import_id: int, db: Session = Depends(get_db), user=Depends(require_permission('evidence:read'))):
    require_case(db, user, case_id, 'export')
    item = lookup(db, user, case_id, import_id)
    return Response(item.raw_bytes, media_type='application/octet-stream', headers={
        'Cache-Control': 'no-store',
        'Content-Disposition': f'attachment; filename="static-import-{item.id}.json"'})

@router.get('/cases/{case_id}/imports')
def list_imports(case_id: int, limit: int = Query(20, ge=1, le=100), before: int | None = Query(None, gt=0),
        db: Session = Depends(get_db), user=Depends(require_permission('evidence:read'))):
    require_case(db, user, case_id)
    query = db.query(StaticImport).filter_by(case_id=case_id, organization_id=user.organization_id)
    if before is not None:
        query = query.filter(StaticImport.id < before)
    return [summary(lookup(db, user, case_id, item.id)) for item in query.order_by(StaticImport.id.desc()).limit(limit).all()]
