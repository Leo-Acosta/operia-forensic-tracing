from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from operia.core.database import get_db
from operia.cybercrime.models import (
    BlockchainTransaction,
    CTFChallenge,
    CTFEvent,
    DeepfakeAnalysis,
    ExternalTool,
    ForensicLabSession,
    IoTDevice,
    ProofMatrixRow,
)
from operia.geo_proximity.models import GeoProximityQuery, LocationReference
from operia.geo_trace.models import GeoTarget, GeoTraceAnalysis
from operia.legal_report.models import Case, Evidence, Report

router = APIRouter()


@router.get("/")
def dashboard(db: Session = Depends(get_db)) -> dict[str, object]:
    return {
        "metrics": {
            "cases": db.query(Case).count(),
            "evidence": db.query(Evidence).count(),
            "reports": db.query(Report).count(),
            "exports": 0,
            "geo_trace_analyses": db.query(GeoTraceAnalysis).count(),
            "geo_targets": db.query(GeoTarget).count(),
            "geo_proximity_locations": db.query(LocationReference).count(),
            "geo_proximity_queries": db.query(GeoProximityQuery).count(),
            "cybercrime_tools": db.query(ExternalTool).count(),
            "cybercrime_lab_sessions": db.query(ForensicLabSession).count(),
            "ctf_events": db.query(CTFEvent).count(),
            "ctf_challenges": db.query(CTFChallenge).count(),
            "deepfake_analyses": db.query(DeepfakeAnalysis).count(),
            "iot_devices": db.query(IoTDevice).count(),
            "blockchain_transactions": db.query(BlockchainTransaction).count(),
            "proof_matrix_rows": db.query(ProofMatrixRow).count(),
        },
        "alerts": [
            "Cybercrime Intelligence Analyst backend module is migrated.",
            "Geo Trace and Geo Proximity backend modules are migrated.",
            "Legacy Cybercrime frontend screen is not migrated yet.",
        ],
    }
