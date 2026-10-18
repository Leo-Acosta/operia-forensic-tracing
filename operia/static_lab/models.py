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
