from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from operia.ai_assistant.models import AIInteraction
from operia.audit.models import AuditLog
from operia.audit.service import write_audit
from operia.cases.models import Case, CaseParticipant, DamageCalculation, DamageItem, Finding, Hypothesis, TechnicalData
from operia.core.database import get_db
from operia.cybercrime.models import ForensicLabSession, ProofMatrixRow, ToolLaunchLog
from operia.evidence.models import ChainOfCustodyAction, Evidence
from operia.exports.models import ExportManifest
from operia.geo_proximity.models import GeoProximityQuery
from operia.geo_trace.models import GeoTarget, GeoTraceAnalysis
from operia.identity.dependencies import CurrentUser, get_optional_user, require_permission
from operia.legal_knowledge.models import LegalCitation, LegalEvaluation, LegalMappingEvidence
from operia.reports.models import Report, ReportReview
from operia.cases.schemas import (
    CaseCreate,
    CaseRead,
    CaseParticipantCreate,
    CaseParticipantRead,
    DamageItemCreate,
    DamageItemRead,
    FindingCreate,
    FindingRead,
    HypothesisCreate,
    HypothesisRead,
    TechnicalDataCreate,
    TechnicalDataRead,
)
from operia.shared.crud import get_or_404, update_from_payload

router = APIRouter()


def case_closure_status(db: Session, case: Case) -> dict[str, object]:
    evidence_count = db.query(Evidence).filter_by(case_id=case.id).count()
    custody_count = db.query(ChainOfCustodyAction).filter_by(case_id=case.id).count()
    reports = db.query(Report).filter_by(case_id=case.id).all()
    reviewed_reports = [report for report in reports if report.review_score > 0 or report.status in {"revisado", "finalizado", "cerrado"}]
    exported_pdf_count = (
        db.query(ExportManifest)
        .filter_by(case_id=case.id, export_type="pdf")
        .count()
    )
    requirements = {
        "evidence": evidence_count > 0,
        "custody": custody_count > 0,
        "report": len(reports) > 0,
        "review": len(reviewed_reports) > 0,
        "pdf_export": exported_pdf_count > 0,
    }
    labels = {
        "evidence": "Cargar al menos una evidencia.",
        "custody": "Registrar al menos una accion de cadena de custodia.",
        "report": "Generar al menos un informe.",
        "review": "Revisar el informe y obtener score.",
        "pdf_export": "Exportar un PDF final con manifiesto.",
    }
    missing = [labels[key] for key, ok in requirements.items() if not ok]
    return {
        "case_id": case.id,
        "case_code": case.case_code,
        "status": case.status,
        "ready_to_close": not missing and case.status != "cerrado",
        "already_closed": case.status == "cerrado",
        "requirements": requirements,
        "missing": missing,
        "counts": {
            "evidence": evidence_count,
            "custody_actions": custody_count,
            "reports": len(reports),
            "reviewed_reports": len(reviewed_reports),
            "pdf_exports": exported_pdf_count,
        },
    }


@router.get("/")
def status() -> dict[str, object]:
    return {
        "module": "Cases",
        "status": "canonical",
        "description": "Shared case files, technical data, findings, hypotheses, and damage tracking.",
    }


@router.post("", response_model=CaseRead)
def create_case(
    payload: CaseCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:write")),
):
    item = Case(**payload.model_dump())
    if current_user and current_user.organization_id:
        item.organization_id = current_user.organization_id
    db.add(item)
    db.flush()
    from operia.identity.case_access import grant_creator
    grant_creator(db, item, current_user)
    write_audit(db, "create_case", "cases", current_user, case_id=item.id, entity_type="case", entity_id=str(item.id), details=item.case_code)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[CaseRead])
def list_cases(
    db: Session = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_optional_user),
):
    query = db.query(Case)
    if current_user and current_user.organization_id:
        query = query.filter(Case.organization_id.in_([current_user.organization_id, None]))
    return query.order_by(desc(Case.updated_at)).all()


@router.get("/{case_id}", response_model=CaseRead)
def read_case(case_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Case, case_id)


@router.get("/{case_id}/closure-status")
def read_case_closure_status(case_id: int, db: Session = Depends(get_db)):
    return case_closure_status(db, get_or_404(db, Case, case_id))


@router.post("/{case_id}/close")
def close_case(
    case_id: int,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:write")),
):
    payload = payload or {}
    case = get_or_404(db, Case, case_id)
    status = case_closure_status(db, case)
    if status["already_closed"]:
        return status | {"message": "El caso ya estaba cerrado."}
    case.status = "cerrado"
    note = str(payload.get("closure_note") or "Cierre operativo del caso desde OPERIA.")
    missing_before_close = list(status["missing"])
    if missing_before_close:
        note = f"{note}\nAdvertencias al cierre: {'; '.join(missing_before_close)}"
    case.general_observations = (case.general_observations or "").rstrip() + f"\n\n[Cierre] {note}"
    db.add(
        ChainOfCustodyAction(
            case_id=case.id,
            action_type="cierre de caso",
            detailed_description=note,
            tool_used="OPERIA Cases",
            status="cerrada",
        )
    )
    write_audit(
        db,
        "close_case",
        "cases",
        current_user,
        case_id=case.id,
        entity_type="case",
        entity_id=str(case.id),
        severity="warning",
        details=note,
    )
    db.commit()
    db.refresh(case)
    return case_closure_status(db, case) | {
        "message": "Caso cerrado correctamente.",
        "closure_warnings": missing_before_close,
        "closure_mode": "cierre_operativo_con_advertencias" if missing_before_close else "cierre_operativo_completo",
    }


@router.post("/{case_id}/participants", response_model=CaseParticipantRead)
def create_participant(
    case_id: int,
    payload: CaseParticipantCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:write")),
):
    case = get_or_404(db, Case, case_id)
    item = CaseParticipant(**payload.model_dump(), case_id=case.id)
    item.organization_id = current_user.organization_id if current_user and current_user.organization_id else case.organization_id
    db.add(item)
    db.flush()
    write_audit(
        db,
        "create_case_participant",
        "cases",
        current_user,
        case_id=case.id,
        entity_type="case_participant",
        entity_id=str(item.id),
        details=f"{item.participant_type}: {item.display_name}",
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/{case_id}/participants", response_model=list[CaseParticipantRead])
def list_participants(case_id: int, db: Session = Depends(get_db)):
    get_or_404(db, Case, case_id)
    return db.query(CaseParticipant).filter_by(case_id=case_id).order_by(CaseParticipant.participant_type, CaseParticipant.display_name).all()


@router.put("/participants/{participant_id}", response_model=CaseParticipantRead)
def update_participant(
    participant_id: int,
    payload: CaseParticipantCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:write")),
):
    item = update_from_payload(get_or_404(db, CaseParticipant, participant_id), payload)
    write_audit(
        db,
        "update_case_participant",
        "cases",
        current_user,
        case_id=item.case_id,
        entity_type="case_participant",
        entity_id=str(item.id),
        details=f"{item.participant_type}: {item.display_name}",
    )
    db.commit()
    db.refresh(item)
    return item


@router.delete("/participants/{participant_id}")
def delete_participant(
    participant_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:write")),
):
    item = get_or_404(db, CaseParticipant, participant_id)
    case_id = item.case_id
    details = f"{item.participant_type}: {item.display_name}"
    write_audit(db, "delete_case_participant", "cases", current_user, case_id=case_id, entity_type="case_participant", entity_id=str(item.id), severity="warning", details=details)
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.put("/{case_id}", response_model=CaseRead)
def update_case(
    case_id: int,
    payload: CaseCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:write")),
):
    item = update_from_payload(get_or_404(db, Case, case_id), payload)
    write_audit(db, "update_case", "cases", current_user, case_id=item.id, entity_type="case", entity_id=str(item.id), details=item.case_code)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{case_id}")
def delete_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:write")),
):
    case = get_or_404(db, Case, case_id)
    report_ids = [row.id for row in db.query(Report.id).filter_by(case_id=case_id).all()]
    if db.query(ChainOfCustodyAction.id).filter_by(case_id=case_id).first():
        raise HTTPException(409, "custody_parent_preserved")
    deleted_reports = len(report_ids)
    db.query(ExportManifest).filter(ExportManifest.case_id == case_id).delete(synchronize_session=False)
    if report_ids:
        db.query(ExportManifest).filter(ExportManifest.report_id.in_(report_ids)).delete(synchronize_session=False)
        db.query(ReportReview).filter(ReportReview.report_id.in_(report_ids)).delete(synchronize_session=False)
        db.query(LegalCitation).filter(LegalCitation.report_id.in_(report_ids)).delete(synchronize_session=False)
        db.query(LegalEvaluation).filter(LegalEvaluation.report_id.in_(report_ids)).delete(synchronize_session=False)
    db.query(LegalMappingEvidence).filter_by(case_id=case_id).delete(synchronize_session=False)
    db.query(ProofMatrixRow).filter_by(case_id=case_id).delete(synchronize_session=False)
    db.query(ForensicLabSession).filter_by(case_id=case_id).delete(synchronize_session=False)
    db.query(ToolLaunchLog).filter_by(case_id=case_id).delete(synchronize_session=False)
    db.query(AIInteraction).filter_by(case_id=case_id).delete(synchronize_session=False)
    db.query(GeoTarget).filter_by(case_id=case_id).delete(synchronize_session=False)
    db.query(GeoTraceAnalysis).filter_by(case_id=case_id).delete(synchronize_session=False)
    db.query(GeoProximityQuery).filter_by(case_id=case_id).delete(synchronize_session=False)
    db.query(LegalCitation).filter_by(case_id=case_id).delete(synchronize_session=False)
    db.query(LegalEvaluation).filter_by(case_id=case_id).delete(synchronize_session=False)
    write_audit(
        db,
        "delete_case",
        "cases",
        current_user,
        case_id=case_id,
        entity_type="case",
        entity_id=str(case_id),
        severity="warning",
        details=f"Caso eliminado: {case.case_code}. Informes asociados eliminados: {deleted_reports}.",
    )
    db.query(AuditLog).filter_by(case_id=case_id).update({"case_id": None}, synchronize_session=False)
    db.delete(case)
    db.commit()
    return {"ok": True, "deleted_case_id": case_id, "deleted_reports": deleted_reports}


@router.post("/{case_id}/technical-data", response_model=TechnicalDataRead)
def create_technical_data(
    case_id: int,
    payload: TechnicalDataCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("evidence:write")),
):
    get_or_404(db, Case, case_id)
    data = payload.model_dump()
    data["case_id"] = case_id
    item = TechnicalData(**data)
    db.add(item)
    db.add(
        ChainOfCustodyAction(
            case_id=case_id,
            action_type="carga",
            detailed_description=f"Dato tecnico cargado: {payload.description}",
            user_responsible=payload.loaded_by,
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/{case_id}/technical-data", response_model=list[TechnicalDataRead])
def list_technical_data(case_id: int, db: Session = Depends(get_db)):
    return db.query(TechnicalData).filter_by(case_id=case_id).order_by(desc(TechnicalData.created_at)).all()


@router.post("/technical-data/{item_id}/convert-to-evidence")
def convert_technical_data_to_evidence(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("evidence:write")),
):
    data = get_or_404(db, TechnicalData, item_id)
    evidence = Evidence(
        case_id=data.case_id,
        technical_data_id=data.id,
        evidence_type=data.data_type,
        description=data.description,
        source=data.source,
        responsible=data.loaded_by,
        file_location=data.associated_file,
        preservation_method="Conversion logica desde dato tecnico registrado en OPERIA",
        tool_used="OPERIA Cases",
        integrity_status="pendiente de validacion",
        confidence_level=data.initial_relevance,
    )
    data.status = "convertido en evidencia"
    db.add(evidence)
    db.flush()
    db.add(
        ChainOfCustodyAction(
            case_id=data.case_id,
            evidence_id=evidence.id,
            action_type="preservacion",
            detailed_description=f"Dato tecnico #{data.id} convertido en evidencia.",
            tool_used="OPERIA Cases",
        )
    )
    db.commit()
    db.refresh(evidence)
    return evidence


@router.post("/{case_id}/findings", response_model=FindingRead)
def create_finding(
    case_id: int,
    payload: FindingCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:write")),
):
    get_or_404(db, Case, case_id)
    data = payload.model_dump()
    data["case_id"] = case_id
    item = Finding(**data)
    db.add(item)
    db.add(ChainOfCustodyAction(case_id=case_id, action_type="analisis", detailed_description=f"Hallazgo creado: {payload.title}"))
    db.commit()
    db.refresh(item)
    return item


@router.get("/{case_id}/findings", response_model=list[FindingRead])
def list_findings(case_id: int, db: Session = Depends(get_db)):
    return db.query(Finding).filter_by(case_id=case_id).order_by(desc(Finding.created_at)).all()


@router.post("/{case_id}/hypotheses", response_model=HypothesisRead)
def create_hypothesis(
    case_id: int,
    payload: HypothesisCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:write")),
):
    get_or_404(db, Case, case_id)
    data = payload.model_dump()
    data["case_id"] = case_id
    item = Hypothesis(**data)
    db.add(item)
    db.add(ChainOfCustodyAction(case_id=case_id, action_type="generacion de hipotesis", detailed_description=f"Hipotesis creada: {payload.title}"))
    db.commit()
    db.refresh(item)
    return item


@router.get("/{case_id}/hypotheses", response_model=list[HypothesisRead])
def list_hypotheses(case_id: int, db: Session = Depends(get_db)):
    return db.query(Hypothesis).filter_by(case_id=case_id).order_by(desc(Hypothesis.created_at)).all()


@router.post("/{case_id}/damage-items", response_model=DamageItemRead)
def create_damage_item(
    case_id: int,
    payload: DamageItemCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:write")),
):
    get_or_404(db, Case, case_id)
    data = payload.model_dump()
    data["case_id"] = case_id
    item = DamageItem(**data)
    db.add(item)
    db.add(ChainOfCustodyAction(case_id=case_id, action_type="cuantificación económica", detailed_description=f"Daño cargado: {payload.concept}"))
    db.commit()
    db.refresh(item)
    return item


@router.get("/{case_id}/damage-items", response_model=list[DamageItemRead])
def list_damage_items(case_id: int, db: Session = Depends(get_db)):
    return db.query(DamageItem).filter_by(case_id=case_id).order_by(desc(DamageItem.created_at)).all()


@router.post("/{case_id}/damage-total")
def calculate_damage(
    case_id: int,
    methodology: str = "Daño total estimado",
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:write")),
):
    get_or_404(db, Case, case_id)
    items = db.query(DamageItem).filter_by(case_id=case_id).all()
    total = sum(item.amount for item in items)
    calculation = DamageCalculation(case_id=case_id, methodology=methodology, total_amount=total, formula_summary="Suma simple de conceptos cargados")
    db.add(calculation)
    db.commit()
    return {"case_id": case_id, "total": total, "currency": items[0].currency if items else "ARS", "methodology": methodology}
