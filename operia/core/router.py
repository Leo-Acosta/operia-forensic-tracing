from fastapi import APIRouter

from operia.cybercrime.router import router as cybercrime_router
from operia.dashboard.router import router as dashboard_router
from operia.evidence.router import router as evidence_router
from operia.exports.router import router as exports_router
from operia.geo_proximity.router import router as geo_proximity_router
from operia.geo_trace.router import router as geo_trace_router
from operia.legal_report.router import router as legal_report_router
from operia.reports.router import router as reports_router
from operia.settings.router import router as settings_router
from operia.users_cases.router import router as users_cases_router

api_router = APIRouter()


@api_router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "product": "OPERIA Forensic Tracing"}


api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(users_cases_router, prefix="/users-cases", tags=["users-cases"])
api_router.include_router(evidence_router, prefix="/evidence", tags=["evidence"])
api_router.include_router(cybercrime_router, prefix="/cybercrime", tags=["cybercrime"])
api_router.include_router(legal_report_router, prefix="/legal-report", tags=["legal-report"])
api_router.include_router(geo_trace_router, prefix="/geo-trace", tags=["geo-trace"])
api_router.include_router(geo_proximity_router, prefix="/geo-proximity", tags=["geo-proximity"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(exports_router, prefix="/exports", tags=["exports"])
api_router.include_router(settings_router, prefix="/settings", tags=["settings"])

