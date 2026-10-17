"""One job per worker. Durable claim, global worker lock, timeout and cancellation.

Parsing runs in a disposable Windows AppContainer without network capabilities,
under a Job Object with memory/CPU/process limits. No unrestricted fallback.
"""
import argparse
import base64
import os
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager

from sqlalchemy import update

from operia.core import database
from operia.core.config import settings
from operia.forensic_engine import ENGINE_VERSION
from operia.forensic_engine.canonical import MAX_OUTPUT_BYTES, canonical_bytes, read_json, sha256
from operia.forensic_jobs.models import Acquisition, ExaminationJob, IndicatorSet, JobEvent
from operia.forensic_jobs.storage_limits import begin_write, ensure_capacity
from operia.identity.models import User
from operia.identity.permissions import has_permission
from operia.mobile_forensics.models import MobileDevice
from operia.cases.models import Case
from operia.shared.time import utcnow
from operia.security.sandbox_runtime import spawn_worker
from operia.security.windows_sandbox import SandboxUnavailable

ACTIVE = ("preparando", "ejecutando")
DONE = ("completado", "completado_con_limitaciones")


@contextmanager
def worker_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open("a+b")
    stream.seek(0)
    stream.write(b"0")
    stream.flush()
    stream.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, BlockingIOError):
        stream.close()
        raise RuntimeError("Ya hay un worker para este almacenamiento")
    try:
        yield
    finally:
        if os.name == "nt":
            import msvcrt
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_UN)
        stream.close()


def event(db, job, state, reason=""):
    job.state = state
    db.add(JobEvent(job_id=job.id, state=state, reason=reason))


def valid_scope(db, job, acquisition):
    from operia.identity.models import Organization
    case = db.get(Case, job.case_id)
    user = db.get(User, job.created_by)
    organization = db.get(Organization, job.organization_id)
    device = db.get(MobileDevice, acquisition.device_id) if acquisition else None
    from operia.identity.case_access import permitted
    return bool(case and user and organization and organization.status == "active" and permitted(db, user, job.case_id) and permitted(db, user, job.case_id, "analysis") and user.status == "active" and has_permission(user.role, "evidence:write")
        and job.organization_id and case.organization_id == job.organization_id == user.organization_id
        and acquisition and acquisition.organization_id == job.organization_id and acquisition.case_id == job.case_id
        and device and device.organization_id == job.organization_id and device.case_id == job.case_id)


def recover_interrupted(db):
    """Call only while holding the exclusive worker lock (previous owner is gone)."""
    jobs = db.query(ExaminationJob).filter(ExaminationJob.state.in_(ACTIVE)).all()
    for job in jobs:
        event(db, job, "interrumpido", "worker_restarted")
        job.finished_at = utcnow()
        job.error_code = "worker_interrupted"
        job.claim_token = ""
    db.commit()
    return len(jobs)


def terminate_tree(process):
    if process.poll() is not None:
        return
    process.kill()  # TerminateJobObject, including the complete job tree.
    process.wait(timeout=3)


def run_once(session_factory=None, timeout=None):
    factory = session_factory or database.SessionLocal
    timeout = timeout if timeout is not None else settings.mobile_job_timeout_seconds
    token = uuid.uuid4().hex
    with factory() as db:
        candidate = db.query(ExaminationJob.id).filter_by(state="pendiente").order_by(ExaminationJob.id).first()
        if candidate is None:
            return False
        changed = db.execute(update(ExaminationJob).where(ExaminationJob.id == candidate.id,
            ExaminationJob.state == "pendiente").values(state="preparando", claim_token=token,
            started_at=utcnow(), heartbeat_at=utcnow())).rowcount
        db.commit()
        if not changed:
            return True
        job = db.get(ExaminationJob, candidate.id)
        acquisition = db.get(Acquisition, job.acquisition_id)
        indicators = db.get(IndicatorSet, job.indicator_set_id) if job.indicator_set_id else None
        event(db, job, "preparando")
        error = None
        if not valid_scope(db, job, acquisition):
            error = "scope_or_operator_invalid"
        elif sha256(acquisition.original_bytes) != acquisition.sha256:
            error = "input_integrity_failed"
        elif sha256(job.configuration_json.encode("utf-8")) != job.configuration_sha256:
            error = "configuration_integrity_failed"
        elif job.indicator_set_id and (not indicators or indicators.case_id != job.case_id or
                indicators.organization_id != job.organization_id or sha256(indicators.original_bytes) != indicators.sha256):
            error = "indicator_integrity_or_scope_failed"
        try:
            configuration = read_json(job.configuration_json.encode("utf-8"), limit=65536)
            if configuration.get("engine_version") != ENGINE_VERSION or type(configuration.get("demo_rules")) is not bool:
                error = "engine_version_or_configuration_mismatch"
            if acquisition and (configuration.get("source_sha256") != acquisition.sha256 or
                    configuration.get("format") != acquisition.format):
                error = "source_configuration_mismatch"
            if configuration.get("indicator_set_sha256") != (indicators.sha256 if indicators else None):
                error = "indicator_configuration_mismatch"
        except (ValueError, AttributeError):
            error = "configuration_invalid"
        if error:
            event(db, job, "fallido", error)
            job.error_code, job.finished_at = error, utcnow()
            job.claim_token = ""
            db.commit()
            return True
        payload = canonical_bytes({"engine_version": ENGINE_VERSION, "acquisition_id": acquisition.id,
            "filename": acquisition.filename, "platform": acquisition.platform, "format": acquisition.format,
            "input": base64.b64encode(acquisition.original_bytes).decode("ascii"),
            "indicators": base64.b64encode(indicators.original_bytes).decode("ascii") if indicators else None,
            "demo_rules": configuration["demo_rules"]})
        event(db, job, "ejecutando")
        db.commit()
        job_id = job.id

    process = None
    try:
        with tempfile.TemporaryDirectory(prefix="operia-native-", dir=settings.temp_dir) as directory:
            # Output is drained in bounded threads so a child cannot fill a pipe or
            # expand an unbounded log on disk. No source path is passed to the child.
            process = spawn_worker("native")
            with factory() as db:
                current = db.get(ExaminationJob, job_id)
                if current and current.claim_token == token:
                    db.add(JobEvent(job_id=job_id, state="ejecutando", reason="sandbox_attached_v1:" + process.sandbox_identity))
                    db.commit()
            output, overflow = bytearray(), threading.Event()

            def drain():
                while True:
                    chunk = process.stdout.read(65536)
                    if not chunk:
                        break
                    if len(output) + len(chunk) > MAX_OUTPUT_BYTES:
                        overflow.set()
                        break
                    output.extend(chunk)

            def feed():
                try:
                    process.stdin.write(payload)
                    process.stdin.close()
                except (BrokenPipeError, OSError):
                    pass

            reader = threading.Thread(target=drain, daemon=True)
            writer = threading.Thread(target=feed, daemon=True)
            reader.start()
            writer.start()
            started, reason, cancelled = time.monotonic(), "", False
            while process.poll() is None:
                with factory() as db:
                    job = db.get(ExaminationJob, job_id)
                    acquisition = db.get(Acquisition, job.acquisition_id)
                    if job.claim_token != token or job.state not in ACTIVE:
                        reason = "claim_lost"
                    elif not valid_scope(db, job, acquisition):
                        reason = "scope_or_operator_changed"
                    elif job.cancel_requested:
                        reason, cancelled = "operator_cancelled", True
                    job.heartbeat_at = utcnow()
                    db.commit()
                if overflow.is_set():
                    reason = "output_quota_exceeded"
                if time.monotonic() - started >= timeout:
                    reason = "timeout"
                if reason:
                    terminate_tree(process)
                    break
                time.sleep(0.05)
            reader.join(timeout=5)
            writer.join(timeout=5)
            if overflow.is_set():
                reason = "output_quota_exceeded"
            with factory() as db:
                begin_write(db)
                job = db.get(ExaminationJob, job_id)
                acquisition = db.get(Acquisition, job.acquisition_id)
                if job.claim_token != token:
                    return True  # Never overwrite another owner's state.
                if job.cancel_requested:
                    reason, cancelled = "operator_cancelled", True
                if not valid_scope(db, job, acquisition):
                    reason = "scope_or_operator_changed"
                elif sha256(acquisition.original_bytes) != configuration["source_sha256"] or acquisition.sha256 != configuration["source_sha256"]:
                    reason = "input_changed_during_analysis"
                elif sha256(job.configuration_json.encode()) != job.configuration_sha256:
                    reason = "configuration_integrity_failed"
                current_indicators = db.get(IndicatorSet, job.indicator_set_id) if job.indicator_set_id else None
                expected_indicator_hash = configuration["indicator_set_sha256"]
                if expected_indicator_hash and (not current_indicators or current_indicators.organization_id != job.organization_id
                    or current_indicators.case_id != job.case_id or sha256(current_indicators.original_bytes) != expected_indicator_hash):
                    reason = "indicators_changed_during_analysis"
                if reason or process.returncode != 0:
                    event(db, job, "cancelado" if cancelled else "fallido", reason or "analysis_rejected")
                    job.error_code = reason or "analysis_rejected"
                else:
                    result = read_json(bytes(output), limit=MAX_OUTPUT_BYTES)
                    if result.get("origin") != "operia_native" or result.get("source_manifest", [{}])[0].get("sha256") != acquisition.sha256:
                        raise ValueError("Invalid child result")
                    ensure_capacity(db, job.organization_id, len(output))
                    job.result_bytes = bytes(output)
                    job.result_sha256 = sha256(bytes(output))
                    event(db, job, "completado_con_limitaciones")
                job.finished_at = utcnow()
                job.claim_token = ""
                db.commit()
    except BaseException as error:
        if process:
            terminate_tree(process)
        with factory() as db:
            job = db.get(ExaminationJob, job_id)
            if job and job.claim_token == token:
                state = "interrumpido" if isinstance(error, (KeyboardInterrupt, SystemExit)) else "fallido"
                reason = "sandbox_unavailable" if isinstance(error, SandboxUnavailable) else (str(error) if isinstance(error, RuntimeError) and str(error) in ("native_storage_quota_exceeded", "native_sqlite_only") else "worker_error")
                event(db, job, state, reason)
                job.error_code, job.finished_at, job.claim_token = reason, utcnow(), ""
                db.commit()
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise
    finally:
        if process:
            process.close()
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    # SQLAlchemy's shared Case mapper references other platform models. Register
    # that existing graph in a fresh worker process without running API startup.
    from operia.core import bootstrap as model_registry  # noqa: F401
    # Explicit initialization belongs to the application's documented migration.
    with worker_lock(settings.storage_dir / "native-mobile.worker.lock"):
        with database.SessionLocal() as db:
            recover_interrupted(db)
        while True:
            worked = run_once()
            if args.once:
                break
            if not worked:
                time.sleep(1)


if __name__ == "__main__":
    main()
