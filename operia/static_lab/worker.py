"""Durable closed-provider queue. Only the worker process runs the provider."""
import base64
import json
import threading
import time
import uuid
from sqlalchemy import update
from operia.core import database
from operia.core.config import settings
from operia.forensic_jobs.worker import worker_lock, terminate_tree
from operia.static_lab.models import StaticJob, StaticJobEvent
from operia.static_lab.contracts import digest, parse_report, MAX_REPORT_BYTES
from operia.static_lab import runtime
from operia.identity.models import User, Organization
from operia.identity.case_access import permitted
from operia.identity.permissions import has_permission
from operia.evidence.models import Evidence, ChainOfCustodyAction
from operia.evidence import custody as custody_listeners  # register ledger hooks in fresh CLI processes
from operia.audit.service import write_audit
from operia.identity.dependencies import CurrentUser

ACTIVE = ('preparing','running')

def event(db, job, state, reason=''):
    job.state = state
    db.add(StaticJobEvent(job_id=job.id,state=state,reason=reason))

def valid(db, job):
    user=db.get(User,job.actor_id); org=db.get(Organization,job.organization_id); evidence=db.get(Evidence,job.evidence_id)
    return bool(user and user.status=='active' and org and org.status=='active' and evidence
        and user.organization_id==job.organization_id and evidence.organization_id==job.organization_id
        and evidence.case_id==job.case_id and evidence.sha256_hash==job.source_sha256
        and has_permission(user.role,'evidence:write')
        and all(permitted(db,user,job.case_id,p) for p in ('read','analysis','evidence')))

def recover(db):
    for job in db.query(StaticJob).filter(StaticJob.state.in_(ACTIVE)).all():
        event(db,job,'interrupted','worker_restarted'); job.claim=''; job.error_code='worker_restarted'
    db.commit()

def run_once(factory=None, timeout=10):
    factory=factory or database.SessionLocal
    # Exclusive across API-independent worker processes, including recovery.
    with worker_lock(settings.temp_dir/'static-lab-worker.lock'):
        with factory() as db:
            recover(db)
            row=db.query(StaticJob.id).filter_by(state='queued').order_by(StaticJob.id).first()
            if not row: return False
            token=uuid.uuid4().hex
            changed=db.execute(update(StaticJob).where(StaticJob.id==row.id,StaticJob.state=='queued').values(state='preparing',claim=token)).rowcount
            db.commit()
            if not changed: return True
            job=db.get(StaticJob,row.id); event(db,job,'preparing'); db.commit()
            job_id=job.id
            source=bytes(job.source_bytes)
        process=None; reason=''; output=bytearray(); overflow=threading.Event()
        try:
            with factory() as db:
                job=db.get(StaticJob,job_id)
                if not valid(db,job): raise RuntimeError('access_revoked')
                if job.cancel_requested: raise RuntimeError('cancelled')
                if digest(source)!=job.source_sha256: raise RuntimeError('input_integrity')
                if job.runtime_identity!=runtime.identity(): raise RuntimeError('provider_revision_changed')
            process=runtime.spawn()
            with factory() as db:
                job=db.get(StaticJob,job_id); event(db,job,'running'); db.commit()
            def drain():
                while chunk:=process.stdout.read(65536):
                    if len(output)+len(chunk)>MAX_REPORT_BYTES:
                        overflow.set(); break
                    output.extend(chunk)
            def feed():
                try:
                    process.stdin.write(json.dumps({'source':base64.b64encode(source).decode('ascii')}).encode()); process.stdin.close()
                except (OSError,BrokenPipeError): pass
            reader=threading.Thread(target=drain,daemon=True); writer=threading.Thread(target=feed,daemon=True)
            reader.start(); writer.start(); started=time.monotonic()
            while process.poll() is None:
                with factory() as db:
                    job=db.get(StaticJob,job_id)
                    if not valid(db,job): reason='access_revoked'
                    elif job.cancel_requested: reason='cancelled'
                if overflow.is_set(): reason='output_limit'
                if time.monotonic()-started>=timeout: reason='timeout'
                if reason: terminate_tree(process); break
                time.sleep(.05)
            reader.join(3); writer.join(3)
            if reader.is_alive() or writer.is_alive(): reason='pipe_timeout'
            if overflow.is_set(): reason='output_limit'
            if reason: raise RuntimeError(reason)
            if process.returncode!=0: raise RuntimeError('provider_rejected')
            report=parse_report(bytes(output))
            if report.provider!='cpython-ast' or report.provider_revision!='operia-ast-adapter/1' or report.provider_version!=__import__('sys').version.split()[0] or report.sample_sha256!=digest(source):
                raise RuntimeError('invalid_result')
            process.close(); process=None
            with factory() as db:
                from operia.forensic_jobs.storage_limits import begin_write
                begin_write(db); job=db.get(StaticJob,job_id)
                if not valid(db,job): raise RuntimeError('access_revoked')
                if job.cancel_requested: raise RuntimeError('cancelled')
                if job.claim!=token or digest(job.source_bytes)!=job.source_sha256: raise RuntimeError('claim_or_input_changed')
                job.result_bytes=bytes(output); job.result_sha256=digest(bytes(output)); job.claim=''
                event(db,job,'completed')
                user=db.get(User,job.actor_id)
                actor=CurrentUser(user.id,user.organization_id,user.name,user.email,user.role)
                db.info['authenticated_actor']=actor
                db.add(ChainOfCustodyAction(case_id=job.case_id,evidence_id=job.evidence_id,
                    action_type='analisis_estatico',detailed_description=f'CPython AST, trabajo #{job.id}; pendiente de revisión',
                    tool_used='cpython-ast/1',hash_before=job.source_sha256,hash_after=job.source_sha256))
                write_audit(db,'static_job_completed','static-lab',actor,case_id=job.case_id,entity_type='static_job',entity_id=str(job.id))
                db.commit()
        except Exception as error:
            reason=str(error) if isinstance(error,RuntimeError) and str(error) in {'access_revoked','cancelled','input_integrity','provider_revision_changed','output_limit','timeout','pipe_timeout','provider_rejected','invalid_result','claim_or_input_changed'} else 'sandbox_or_provider_failed'
            with factory() as db:
                job=db.get(StaticJob,job_id)
                if job.claim==token:
                    event(db,job,'cancelled' if reason=='cancelled' else 'failed',reason); job.error_code=reason; job.claim=''; db.commit()
        finally:
            if process:
                terminate_tree(process); process.close()
        return True

if __name__=='__main__':
    from operia.security.production import enforce_production
    enforce_production(settings)
    from operia.core import bootstrap as registry
    run_once()
