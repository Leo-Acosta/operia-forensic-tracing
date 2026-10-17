from fastapi import APIRouter, Depends

from operia.ai_assistant.router import router as ai_assistant_router
from operia.ai_security.router import router as ai_security_router
from operia.audit.router import router as audit_router
from operia.cases.router import router as cases_router
from operia.cybercrime.router import router as cybercrime_router
from operia.dashboard.router import router as dashboard_router
from operia.evidence.router import router as evidence_router
from operia.exports.router import router as exports_router
from operia.geo_proximity.router import router as geo_proximity_router
from operia.geo_trace.router import router as geo_trace_router
from operia.identity.router import router as identity_router
from operia.identity.dependencies import require_permission
from operia.legal_knowledge.router import router as legal_knowledge_router
from operia.legal_report.legal_router import router as legal_router
from operia.legal_report.router import router as legal_report_router
from operia.mind.router import router as mind_router
from operia.mobile_forensics.router import router as mobile_router
from operia.mobile_forensics.native_router import router as native_mobile_router
from operia.reports.router import router as reports_router
from operia.rubrics.router import router as rubrics_router
from operia.settings.router import router as settings_router
from operia.users_cases.router import router as users_cases_router

from operia.identity.isolation import enforce_scope
from operia.mobile_forensics.projection_router import router as projection_router

from operia.identity.case_access import router as case_access_router

api_router = APIRouter()
api_router.include_router(case_access_router, tags=["case-access"])
api_router.include_router(projection_router, dependencies=[Depends(enforce_scope)], prefix="/mobile-forensics", tags=["native-projections"])
api_router.include_router(mobile_router, dependencies=[Depends(enforce_scope)], prefix="/mobile-forensics", tags=["mobile-forensics"])
api_router.include_router(native_mobile_router, dependencies=[Depends(enforce_scope)], prefix="/mobile-forensics", tags=["native-mobile"])


@api_router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "product": "OPERIA Forensic Tracing"}


api_router.include_router(dashboard_router, dependencies=[Depends(enforce_scope)], prefix="/dashboard", tags=["dashboard"])
api_router.include_router(identity_router, prefix="/identity", tags=["identity"])
api_router.include_router(audit_router, dependencies=[Depends(enforce_scope)], prefix="/audit", tags=["audit"])
api_router.include_router(cases_router, dependencies=[Depends(enforce_scope)], prefix="/cases", tags=["cases"])
api_router.include_router(users_cases_router, dependencies=[Depends(enforce_scope)], prefix="/users-cases", tags=["users-cases"])
api_router.include_router(evidence_router, dependencies=[Depends(enforce_scope)], prefix="/evidence", tags=["evidence"])
api_router.include_router(cybercrime_router, dependencies=[Depends(enforce_scope)], prefix="/cybercrime", tags=["cybercrime"])
api_router.include_router(legal_router, dependencies=[Depends(enforce_scope)], prefix="/legal", tags=["legal"])
api_router.include_router(
    legal_report_router,
    prefix="/legal-report",
    tags=["legal-report-legacy"],
    dependencies=[Depends(enforce_scope), Depends(require_permission("reports:write"))],
)
api_router.include_router(legal_knowledge_router, dependencies=[Depends(enforce_scope)], prefix="/legal-knowledge", tags=["legal-knowledge"])
api_router.include_router(ai_assistant_router, dependencies=[Depends(enforce_scope)], prefix="/ai", tags=["ai"])
api_router.include_router(ai_security_router, dependencies=[Depends(enforce_scope)], prefix="/ai-security", tags=["ai-security"])
api_router.include_router(mind_router, dependencies=[Depends(enforce_scope)], prefix="/mind", tags=["mind"])
api_router.include_router(geo_trace_router, dependencies=[Depends(enforce_scope)], prefix="/geo/trace", tags=["geo-trace"])
api_router.include_router(geo_trace_router, dependencies=[Depends(enforce_scope)], prefix="/geo-trace", tags=["geo-trace-legacy"])
api_router.include_router(geo_proximity_router, dependencies=[Depends(enforce_scope)], prefix="/geo/proximity", tags=["geo-proximity"])
api_router.include_router(geo_proximity_router, dependencies=[Depends(enforce_scope)], prefix="/geo-proximity", tags=["geo-proximity-legacy"])
api_router.include_router(reports_router, dependencies=[Depends(enforce_scope)], prefix="/reports", tags=["reports"])
api_router.include_router(rubrics_router, dependencies=[Depends(enforce_scope)], prefix="/rubrics", tags=["rubrics"])
api_router.include_router(exports_router, dependencies=[Depends(enforce_scope)], prefix="/exports", tags=["exports"])
api_router.include_router(settings_router, prefix="/settings", tags=["settings"])
