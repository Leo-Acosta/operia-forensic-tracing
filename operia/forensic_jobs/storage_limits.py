"""SQLite-local transactional byte accounting, including outputs and snapshots."""
from sqlalchemy import func, select, text

from operia.core.config import settings
from operia.forensic_jobs.models import Acquisition, ExaminationJob, ExportRecord, IndicatorSet, EvidenceIntegration, AnalysisProjection


def begin_write(db):
    if db.bind.dialect.name != "sqlite":
        raise RuntimeError("native_sqlite_only")
    # SQLite's default legacy transaction mode doesn't BEGIN on SELECT. Acquire
    # the writer lock before measuring/reserving bytes or counting queued jobs.
    db.execute(text("BEGIN IMMEDIATE"))


def ensure_capacity(db, organization_id, added_bytes):
    total = 0
    for model, column in ((Acquisition, Acquisition.original_bytes), (IndicatorSet, IndicatorSet.original_bytes),
                          (ExaminationJob, ExaminationJob.result_bytes), (EvidenceIntegration, EvidenceIntegration.snapshot_bytes), (AnalysisProjection, AnalysisProjection.snapshot_bytes)):
        total += db.scalar(select(func.coalesce(func.sum(func.length(column)), 0)).where(
            model.organization_id == organization_id)) or 0
    total += db.scalar(select(func.coalesce(func.sum(func.length(ExportRecord.content)), 0)).join(
        ExaminationJob, ExaminationJob.id == ExportRecord.job_id).where(ExaminationJob.organization_id == organization_id)) or 0
    if total + added_bytes > settings.mobile_storage_quota_bytes:
        raise RuntimeError("native_storage_quota_exceeded")
