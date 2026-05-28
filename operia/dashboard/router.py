from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from operia.core.database import get_db
from operia.cases.models import Case
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
from operia.evidence.models import Evidence
from operia.exports.models import ExportManifest
from operia.legal_report.services.report_service import final_pericial_checklist
from operia.reports.models import Report

router = APIRouter()


@router.get("/")
def dashboard(db: Session = Depends(get_db)) -> dict[str, object]:
    reports = db.query(Report).order_by(Report.updated_at.desc()).limit(20).all()
    ready_reports = [report for report in reports if final_pericial_checklist(report)["ready"]]
    cases = db.query(Case).all()
    cases_by_status: dict[str, int] = {}
    for case in cases:
        cases_by_status[case.status] = cases_by_status.get(case.status, 0) + 1
    evidence_without_hash = db.query(Evidence).filter(Evidence.sha256_hash == "").count()
    unsealed_final_reports = db.query(Report).filter(Report.status == "final", ~Report.observations.contains("OPERIA-SEAL-")).count()
    return {
        "metrics": {
            "cases": db.query(Case).count(),
            "evidence": db.query(Evidence).count(),
            "reports": db.query(Report).count(),
            "exports": db.query(ExportManifest).count(),
            "ready_final_reports": len(ready_reports),
            "evidence_without_hash": evidence_without_hash,
            "unsealed_final_reports": unsealed_final_reports,
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
        "cases_by_status": cases_by_status,
        "report_readiness": [
            {
                "report_id": report.id,
                "case_id": report.case_id,
                "title": report.title,
                "status": report.status,
                "review_score": report.review_score,
                "ready_for_final": report in ready_reports,
            }
            for report in reports
        ],
        "alerts": [
            "Usar exportacion final sellada para informes destinados a presentacion externa.",
            "Completar hashes y custodia antes de cerrar casos.",
            "Validar mapeo legal con evidencia concreta antes de sostener atribucion.",
        ],
    }
