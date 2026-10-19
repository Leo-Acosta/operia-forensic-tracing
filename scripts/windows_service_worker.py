"""Supervised worker loops; existing claims, custody, recovery and sandbox remain."""
import os
from pathlib import Path
import time

if __name__=='__main__':
    from operia.core.config import settings
    from operia.security.production import enforce_production
    enforce_production(settings)
    from operia.core import bootstrap as registry
    from operia.core.database import SessionLocal
    from operia.forensic_jobs.worker import worker_lock
    kind=os.environ['OPERIA_SERVICE_WORKER_KIND']
    stop=Path(os.environ['OPERIA_SERVICE_STOP_FILE'])
    if kind not in ('native','static'): raise RuntimeError('service_worker_kind_rejected')
    lock=settings.storage_dir/('native-mobile.worker.lock' if kind=='native' else 'static-service-poller.lock')
    with worker_lock(lock):
        if kind=='native':
            from operia.forensic_jobs.worker import run_once,recover_interrupted
            with SessionLocal() as db: recover_interrupted(db)
        else:
            from operia.static_lab.worker import run_once
        while not stop.exists():
            worked=run_once()
            if not worked: time.sleep(.5)
