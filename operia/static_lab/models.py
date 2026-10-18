"""Append-only imported static results, separate from provider execution."""
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, UniqueConstraint, event, text
from sqlalchemy.orm import Mapped, mapped_column, Session
from operia.core.database import Base
from operia.shared.time import utcnow

class StaticImport(Base):
    __tablename__ = 'static_lab_imports'
    __table_args__ = (UniqueConstraint('organization_id', 'case_id', 'evidence_id', 'raw_sha256', name='uq_static_import'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'), index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey('cases.id'), index=True)
    evidence_id: Mapped[int] = mapped_column(ForeignKey('evidence.id'))
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    sample_sha256: Mapped[str] = mapped_column(String(64))
    raw_sha256: Mapped[str] = mapped_column(String(64))
    normalized_sha256: Mapped[str] = mapped_column(String(64))
    raw_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    normalized_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

def install_protection(connection):
    if connection.dialect.name != 'sqlite':
        raise RuntimeError('static_lab_sqlite_only')
    for operation in ('UPDATE', 'DELETE'):
        connection.execute(text(f"CREATE TRIGGER IF NOT EXISTS static_lab_no_{operation.lower()} BEFORE {operation} ON static_lab_imports BEGIN SELECT RAISE(ABORT, 'static_lab_append_only'); END"))

@event.listens_for(Session, 'before_flush')
def immutable(db, context, instances):
    for item in list(db.dirty) + list(db.deleted):
        if isinstance(item, StaticImport) and (item in db.deleted or db.is_modified(item)):
            raise HTTPException(409, 'Resultado estático inmutable; importar una nueva versión')

class StaticJob(Base):
    __tablename__ = 'static_lab_jobs'
    __table_args__ = (UniqueConstraint('case_id','evidence_id','request_key',name='uq_static_job_request'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'), index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey('cases.id'), index=True)
    evidence_id: Mapped[int] = mapped_column(ForeignKey('evidence.id'))
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    request_key: Mapped[str] = mapped_column(String(64))
    source_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    source_sha256: Mapped[str] = mapped_column(String(64))
    runtime_identity: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(32), default='queued')
    error_code: Mapped[str] = mapped_column(String(64), default='')
    claim: Mapped[str] = mapped_column(String(64), default='')
    cancel_requested: Mapped[int] = mapped_column(Integer, default=0)
    result_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    result_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class StaticReview(Base):
    __tablename__ = 'static_lab_reviews'
    __table_args__ = (UniqueConstraint('job_id','version',name='uq_static_review_version'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'), index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey('cases.id'), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('static_lab_jobs.id'))
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    version: Mapped[int] = mapped_column(Integer)
    result_sha256: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(32))
    rationale: Mapped[str] = mapped_column(String(4000))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class StaticJobEvent(Base):
    __tablename__ = 'static_lab_job_events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('static_lab_jobs.id'), index=True)
    state: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(String(100), default='')
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

def install_job_protection(connection):
    for table in ('static_lab_reviews','static_lab_job_events'):
        for operation in ('UPDATE','DELETE'):
            connection.execute(text(f"CREATE TRIGGER IF NOT EXISTS {table}_no_{operation.lower()} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, 'static_lab_append_only'); END"))
    connection.execute(text("CREATE TRIGGER IF NOT EXISTS static_jobs_no_delete BEFORE DELETE ON static_lab_jobs BEGIN SELECT RAISE(ABORT, 'static_lab_append_only'); END"))
    connection.execute(text("""CREATE TRIGGER IF NOT EXISTS static_jobs_preserve BEFORE UPDATE ON static_lab_jobs WHEN
        OLD.organization_id IS NOT NEW.organization_id OR OLD.case_id IS NOT NEW.case_id OR
        OLD.evidence_id IS NOT NEW.evidence_id OR OLD.actor_id IS NOT NEW.actor_id OR
        OLD.source_bytes IS NOT NEW.source_bytes OR OLD.source_sha256 IS NOT NEW.source_sha256 OR
        OLD.request_key IS NOT NEW.request_key OR OLD.runtime_identity IS NOT NEW.runtime_identity OR
        OLD.recorded_at IS NOT NEW.recorded_at OR
        (OLD.state IN ('completed','failed','cancelled','interrupted') AND OLD.state IS NOT NEW.state) OR
        (OLD.result_bytes IS NOT NULL AND (OLD.result_bytes IS NOT NEW.result_bytes OR OLD.result_sha256 IS NOT NEW.result_sha256))
        BEGIN SELECT RAISE(ABORT, 'static_lab_append_only'); END"""))
