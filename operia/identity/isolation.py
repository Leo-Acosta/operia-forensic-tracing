"""Request-local tenant scope, including legacy rows inherited through their case."""
from fastapi import Depends, HTTPException, Request
from sqlalchemy import event, inspect, or_, and_
from sqlalchemy.orm import Session, with_loader_criteria
from operia.core.database import Base, get_db
from operia.identity.dependencies import require_user, CurrentUser
from operia.identity.permissions import has_permission


def case_predicate(model, organization_id):
    from operia.cases.models import Case
    from operia.identity.models import User, AuthToken, Membership
    if model in (User, AuthToken, Membership):
        return model.organization_id == organization_id
    if model is Case:
        return model.organization_id == organization_id
    if hasattr(model, "case_id"):
        inherited = model.case_id.in_(SessionScope.case_ids(organization_id))
        if inspect(model).columns.case_id.nullable and hasattr(model, "organization_id"):
            inherited = or_(inherited, and_(model.case_id.is_(None), model.organization_id == organization_id))
    else:
        from sqlalchemy import select
        for column in inspect(model).columns:
            for fk in column.foreign_keys:
                parent = next((m.class_ for m in Base.registry.mappers if m.local_table is fk.column.table), None)
                if parent is not None and parent is not model and hasattr(parent, "case_id"):
                    inherited = getattr(model, column.key).in_(select(getattr(parent, fk.column.key)).where(case_predicate(parent, organization_id)))
                    break
            else:
                continue
            break
        else:
            return None
    if hasattr(model, "organization_id"):
        return and_(inherited, or_(model.organization_id == organization_id, model.organization_id.is_(None)))
    return inherited


class SessionScope:
    @staticmethod
    def case_ids(organization_id):
        from sqlalchemy import select
        from operia.cases.models import Case
        return select(Case.id).where(Case.organization_id == organization_id)


@event.listens_for(Session, "do_orm_execute")
def scoped_queries(state):
    org = state.session.info.get("request_organization")
    if org is None or not state.is_select:
        return
    for mapper in Base.registry.mappers:
        model = mapper.class_
        predicate = case_predicate(model, org)
        if predicate is not None:
            state.statement = state.statement.options(with_loader_criteria(model, predicate, include_aliases=True))


@event.listens_for(Session, "before_flush")
def validate_writes(db, context, instances):
    org = db.info.get("request_organization")
    if org is None:
        return
    from operia.cases.models import Case
    from operia.forensic_jobs.models import EvidenceIntegration, AnalysisProjection
    for item in list(db.new) + list(db.dirty) + list(db.deleted):
        if isinstance(item, Case):
            if item in db.new:
                item.organization_id = org
            elif item.organization_id != org or inspect(item).attrs.organization_id.history.has_changes():
                raise HTTPException(409, "No se permite trasladar casos entre organizaciones")
        if item in db.new and hasattr(item, "organization_id") and item.organization_id is None:
            item.organization_id = org
        item_case_id = getattr(item, "case_id", None)
        if item_case_id is None:
            from operia.reports.models import Report, Presentation
            for key, parent_model in (("report_id", Report), ("presentation_id", Presentation)):
                parent_id = getattr(item, key, None)
                if parent_id is not None:
                    parent = db.get(parent_model, parent_id)
                    if not parent:
                        raise HTTPException(404, "Documento padre no disponible")
                    item_case_id = parent.case_id
                    break
        if hasattr(item, "case_id") and item.case_id is not None:
            history = inspect(item).attrs.case_id.history
            if item not in db.new and history.has_changes():
                raise HTTPException(409, "No se permite trasladar registros entre casos")
            case = db.get(Case, item.case_id)
            if not case or case.organization_id != org:
                raise HTTPException(404, "Caso no disponible")
            if getattr(item, "organization_id", org) not in (None, org):
                raise HTTPException(404, "Organización incompatible")
            if hasattr(item, "organization_id") and item in db.new:
                item.organization_id = org
        if item_case_id is not None:
            for column in inspect(type(item)).columns:
                for fk in column.foreign_keys:
                    target = next((m.class_ for m in Base.registry.mappers if m.local_table is fk.column.table), None)
                    value = getattr(item, column.key, None)
                    if value is None or target is None or target is Case or not hasattr(target, "case_id"):
                        continue
                    parent = db.get(target, value)
                    if not parent or parent.case_id != item_case_id:
                        raise HTTPException(422, "Referencia ajena al caso")
        if item.__tablename__ == "hypotheses":
            import re
            from operia.cases.models import Finding
            from operia.evidence.models import Evidence
            for key, model in (("finding_ids", Finding), ("evidence_ids", Evidence)):
                raw = getattr(item, key, None) or ""
                if raw:
                    ids = re.split(r"[,\s]+", raw.strip())
                    if len(ids) > 100 or any(not value.isdecimal() for value in ids) or len(ids) != len(set(ids)):
                        raise HTTPException(422, "Referencias de hipotesis invalidas")
                    for value in ids:
                        referenced = db.get(model, int(value))
                        if not referenced or referenced.case_id != item.case_id:
                            raise HTTPException(422, "Referencia de hipotesis ajena al caso")
        if item in db.dirty or item in db.deleted:
            projection_key = {"findings": "finding_id", "hypotheses": "hypothesis_id", "geo_trace_analyses": "geo_analysis_id"}.get(item.__tablename__)
            if projection_key and db.query(AnalysisProjection).filter(getattr(AnalysisProjection, projection_key) == item.id).first():
                if item in db.deleted or db.is_modified(item, include_collections=False):
                    raise HTTPException(409, "Analisis proyectado preservado: crear otra proyeccion")
            if item.__tablename__ == "geo_trace_targets" and db.query(AnalysisProjection).filter_by(geo_analysis_id=item.analysis_id).first():
                raise HTTPException(409, "Target proyectado preservado")
            name = item.__tablename__
            if name in {"report_sections", "report_versions"}:
                if db.query(EvidenceIntegration).filter_by(report_id=item.report_id).first():
                    raise HTTPException(409, "Seccion o version integrada preservada")
            key = {"evidence": "evidence_id", "reports": "report_id", "chain_of_custody_actions": "custody_id"}.get(name)
            if key and db.query(EvidenceIntegration).filter(getattr(EvidenceIntegration, key) == item.id).first():
                if item in db.deleted or db.is_modified(item, include_collections=False):
                    raise HTTPException(409, "Registro integrado preservado: crear una nueva revisión")


async def enforce_scope(request: Request, db: Session = Depends(get_db), user: CurrentUser = Depends(require_user)):
    if not user.organization_id:
        raise HTTPException(403, "Organización requerida")
    from operia.core.config import settings
    module = request.url.path.removeprefix(settings.api_prefix + "/").split("/", 1)[0]
    writing = request.method not in ("GET", "HEAD", "OPTIONS")
    permissions = {"evidence": "evidence", "reports": "reports", "exports": "reports", "legal-report": "reports", "rubrics": "reports",
                   "legal": "legal", "legal-knowledge": "legal", "cases": "cases", "cybercrime": "evidence",
                   "geo": "evidence", "geo-trace": "evidence", "geo-proximity": "evidence"}
    permission = permissions.get(module, "cases") + (":write" if writing else ":read")
    if module in ("ai", "mind", "ai-security") and writing:
        permission = "ai:use"
    if module == "legal-knowledge" and request.url.path.endswith("/articles/recommend"):
        permission = "legal:read"
    if module == "audit":
        permission = "audit:read"
    if not has_permission(user.role, permission):
        raise HTTPException(403, "Permiso insuficiente")
    db.info["request_organization"] = user.organization_id
    from operia.cases.models import Case
    body = {}
    if request.headers.get("content-type", "").split(";", 1)[0] == "application/json":
        try:
            data = await request.json()
            body = data if isinstance(data, dict) else {}
        except ValueError:
            pass  # Endpoint validation reports malformed bodies.
    references = {**dict(request.query_params), **body, **request.path_params}
    case_id = references.get("case_id")
    try:
        case_id = int(case_id) if case_id is not None else None
    except (TypeError, ValueError):
        raise HTTPException(422, "Identificador de caso invalido")
    if case_id is not None and not db.get(Case, int(case_id)):
        raise HTTPException(404, "Caso no disponible")

    if request.method == "DELETE" and case_id is not None:
        from operia.forensic_jobs.models import Acquisition, IndicatorSet, ExaminationJob
        from operia.mobile_forensics.models import MobileExam, MobileDevice
        for model in (Acquisition, IndicatorSet, ExaminationJob, MobileExam, MobileDevice):
            if db.query(model).filter_by(case_id=int(case_id)).first():
                raise HTTPException(409, "Caso con historicos moviles preservados; no se permite eliminar")
    from operia.evidence.models import Evidence, ChainOfCustodyAction
    from operia.reports.models import Report, Presentation, PresentationSlide, ReportSection
    from operia.cases.models import Finding, Hypothesis
    objects = {"finding_id": Finding, "hypothesis_id": Hypothesis, "report_id": Report, "evidence_id": Evidence, "action_id": ChainOfCustodyAction,
               "presentation_id": Presentation, "slide_id": PresentationSlide, "section_id": ReportSection}
    if request.url.path.startswith(("/api/geo/trace", "/api/geo-trace")):
        from operia.geo_trace.models import GeoTraceAnalysis
        objects["analysis_id"] = GeoTraceAnalysis
    for key, model in objects.items():
        value = references.get(key)
        if value is not None:
            try:
                item = db.get(model, int(value))
            except (TypeError, ValueError):
                raise HTTPException(422, "Identificador invalido")
            if not item:
                raise HTTPException(404, "Recurso no disponible")
            parent_case = getattr(item, "case_id", None)
            if parent_case is not None:
                if case_id is not None and parent_case != case_id:
                    raise HTTPException(422, "Referencias de distintos casos")
                case_id = parent_case
