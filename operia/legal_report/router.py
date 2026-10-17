from pathlib import Path
from shutil import copyfileobj
from uuid import uuid4
from operia.evidence.router import safe_path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from operia.legal_report.config import UPLOAD_DIR
from operia.cases.models import Case, DamageCalculation, DamageItem, Finding, Hypothesis, TechnicalData
from operia.core.database import get_db
from operia.evidence.models import ChainOfCustodyAction, Evidence
from operia.legal_knowledge.models import LegalMapping, LegalSource
from operia.reports.models import Presentation, PresentationReview, PresentationSlide, Report, ReportReview, ReportSection, ReportVersion, Template
from operia.legal_report.schemas.domain import (
    CaseEvaluationResult,
    CaseCreate,
    CaseRead,
    CustodyActionCreate,
    CustodyActionRead,
    DamageItemCreate,
    DamageItemRead,
    DashboardRead,
    EvidenceCreate,
    EvidenceRead,
    FindingCreate,
    FindingRead,
    HypothesisCreate,
    HypothesisRead,
    LegalMappingCreate,
    LegalMappingRead,
    LegalSourceCreate,
    LegalSourceRead,
    PresentationRead,
    PresentationReviewResult,
    PresentationSlideRead,
    PresentationSlideUpdate,
    ReportRead,
    ReportUpdate,
    ReviewResult,
    TechnicalDataCreate,
    TechnicalDataRead,
)
from operia.exports.service import export_docx, export_html, export_markdown, export_pdf, export_presentation_pdf
from operia.legal_report.services.hash_service import md5_file, sha256_file
from operia.legal_report.services.ai_legal_service import apply_automatic_legal_mappings, generate_automatic_legal_analysis
from operia.legal_report.services.ai_case_evaluation_service import evaluate_report_case, evaluation_to_markdown
from operia.legal_report.services.consistency_service import enrich_case
from operia.legal_report.services.legal_knowledge_base import sync_official_sources
from operia.legal_report.services.presentation_service import build_presentation
from operia.legal_report.services.report_service import build_integral_markdown, polish_report_markdown, populate_report_sections, snapshot_report
from operia.legal_report.services.review_service import review_presentation, review_report

router = APIRouter()


class SectionUpdate(BaseModel):
    content: str
    user: str = "Operia"


@router.get("/")
def module_status() -> dict[str, object]:
    return {
        "module": "Forensic Legal Report",
        "status": "migrated",
        "description": "Legal-forensic reports, editable sections, reviews, legal mappings, presentations, and exports.",
        "main_routes": [
            "/dashboard",
            "/cases",
            "/cases/{case_id}/reports",
            "/reports/{report_id}/review",
            "/reports/{report_id}/export/{fmt}",
            "/presentations/{presentation_id}/export/pdf",
        ],
    }


def get_or_404(db: Session, model, item_id: int):
    item = db.get(model, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    return item


def update_from_payload(item, payload: BaseModel):
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    return item


@router.get("/dashboard", response_model=DashboardRead)
def dashboard(db: Session = Depends(get_db)):
    cases = db.query(Case).order_by(desc(Case.updated_at)).limit(5).all()
    actions = db.query(ChainOfCustodyAction).order_by(desc(ChainOfCustodyAction.action_at)).limit(8).all()
    damage_total = sum(item.amount for item in db.query(DamageItem).all())
    metrics = {
        "cases": db.query(Case).count(),
        "open_cases": db.query(Case).filter(Case.status != "cerrado").count(),
        "closed_cases": db.query(Case).filter(Case.status == "cerrado").count(),
        "draft_reports": db.query(Report).filter(Report.status == "borrador").count(),
        "reviewed_reports": db.query(Report).filter(Report.status.in_(["revisado", "finalizado"])).count(),
        "evidence": db.query(Evidence).count(),
        "validated_findings": db.query(Finding).filter(Finding.status == "validado").count(),
        "estimated_damage": damage_total,
        "alerts": db.query(Report).filter(Report.review_score < 70).count(),
    }
    return {"metrics": metrics, "recent_cases": cases, "recent_actions": actions}


@router.post("/cases", response_model=CaseRead)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    item = Case(**payload.model_dump())
    db.add(item)
    db.flush()
    from operia.identity.case_access import grant_creator
    grant_creator(db, item, db.info["request_actor"])
    db.commit()
    db.refresh(item)
    return item


@router.get("/cases", response_model=list[CaseRead])
def list_cases(db: Session = Depends(get_db)):
    return db.query(Case).order_by(desc(Case.updated_at)).all()


@router.get("/cases/{case_id}", response_model=CaseRead)
def read_case(case_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Case, case_id)


@router.put("/cases/{case_id}", response_model=CaseRead)
def update_case(case_id: int, payload: CaseCreate, db: Session = Depends(get_db)):
    item = get_or_404(db, Case, case_id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/cases/{case_id}")
def delete_case(case_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Case, case_id))
    db.commit()
    return {"ok": True}


@router.post("/technical-data", response_model=TechnicalDataRead)
def create_technical_data(payload: TechnicalDataCreate, db: Session = Depends(get_db)):
    get_or_404(db, Case, payload.case_id)
    item = TechnicalData(**payload.model_dump())
    db.add(item)
    db.add(ChainOfCustodyAction(case_id=payload.case_id, action_type="carga", detailed_description=f"Dato tÃ©cnico cargado: {payload.description}", user_responsible=payload.loaded_by))
    db.commit()
    db.refresh(item)
    return item


@router.get("/cases/{case_id}/technical-data", response_model=list[TechnicalDataRead])
def list_technical_data(case_id: int, db: Session = Depends(get_db)):
    return db.query(TechnicalData).filter_by(case_id=case_id).order_by(desc(TechnicalData.created_at)).all()


@router.put("/technical-data/{item_id}", response_model=TechnicalDataRead)
def update_technical_data(item_id: int, payload: TechnicalDataCreate, db: Session = Depends(get_db)):
    item = get_or_404(db, TechnicalData, item_id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/technical-data/{item_id}")
def delete_technical_data(item_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, TechnicalData, item_id))
    db.commit()
    return {"ok": True}


@router.post("/technical-data/{item_id}/convert-to-evidence", response_model=EvidenceRead)
def convert_to_evidence(item_id: int, db: Session = Depends(get_db)):
    data = get_or_404(db, TechnicalData, item_id)
    evidence = Evidence(
        case_id=data.case_id,
        technical_data_id=data.id,
        evidence_type=data.data_type,
        description=data.description,
        source=data.source,
        responsible=data.loaded_by,
        file_location=data.associated_file,
        preservation_method="ConversiÃ³n lÃ³gica desde dato tÃ©cnico registrado en Operia",
        tool_used="Operia MVP",
        integrity_status="pendiente de validaciÃ³n",
        confidence_level=data.initial_relevance,
    )
    data.status = "convertido en evidencia"
    db.add(evidence)
    db.flush()
    db.add(ChainOfCustodyAction(case_id=data.case_id, evidence_id=evidence.id, action_type="preservaciÃ³n", detailed_description=f"Dato tÃ©cnico #{data.id} convertido en evidencia.", tool_used="Operia MVP"))
    db.commit()
    db.refresh(evidence)
    return evidence


@router.post("/evidence", response_model=EvidenceRead)
def create_evidence(payload: EvidenceCreate, db: Session = Depends(get_db)):
    item = Evidence(**payload.model_dump())
    db.add(item)
    db.flush()
    db.add(ChainOfCustodyAction(case_id=item.case_id, evidence_id=item.id, action_type="carga", detailed_description=f"Evidencia cargada: {item.description}", hash_after=item.sha256_hash))
    db.commit()
    db.refresh(item)
    return item


@router.post("/cases/{case_id}/evidence/upload", response_model=EvidenceRead)
def upload_evidence(case_id: int, description: str, responsible: str = "", custodian: str = "", file: UploadFile = File(...), db: Session = Depends(get_db)):
    get_or_404(db, Case, case_id)
    case_dir = UPLOAD_DIR / str(case_id)
    case_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "evidence.bin").name
    destination = safe_path(str(case_dir / (uuid4().hex + "-" + safe_name)), case_id)
    with destination.open("xb") as buffer:
        copyfileobj(file.file, buffer)
    sha = sha256_file(destination)
    evidence = Evidence(
        case_id=case_id,
        evidence_type="archivo",
        description=description,
        responsible=responsible,
        custodian=custodian,
        sha256_hash=sha,
        md5_hash=md5_file(destination),
        file_location=str(destination),
        preservation_method="Carga local con cÃ¡lculo automÃ¡tico de SHA-256",
        tool_used="Operia hash_service",
        integrity_status="integra",
        confidence_level="alto",
    )
    db.add(evidence)
    db.flush()
    db.add(ChainOfCustodyAction(case_id=case_id, evidence_id=evidence.id, action_type="carga", detailed_description=f"Archivo preservado: {safe_name}", tool_used="Operia hash_service", hash_after=sha, user_responsible=responsible))
    db.commit()
    db.refresh(evidence)
    return evidence


@router.get("/cases/{case_id}/evidence", response_model=list[EvidenceRead])
def list_evidence(case_id: int, db: Session = Depends(get_db)):
    return db.query(Evidence).filter_by(case_id=case_id).order_by(desc(Evidence.created_at)).all()


@router.get("/evidence/{evidence_id}", response_model=EvidenceRead)
def read_evidence(evidence_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Evidence, evidence_id)


@router.put("/evidence/{evidence_id}", response_model=EvidenceRead)
def update_evidence(evidence_id: int, payload: EvidenceCreate, db: Session = Depends(get_db)):
    item = get_or_404(db, Evidence, evidence_id)
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/evidence/{evidence_id}")
def delete_evidence(evidence_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Evidence, evidence_id))
    db.commit()
    return {"ok": True}


@router.post("/custody-actions", response_model=CustodyActionRead)
def create_action(payload: CustodyActionCreate, db: Session = Depends(get_db)):
    item = ChainOfCustodyAction(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/custody-actions/{action_id}", response_model=CustodyActionRead)
def update_action(action_id: int, payload: CustodyActionCreate, db: Session = Depends(get_db)):
    get_or_404(db, ChainOfCustodyAction, action_id)
    raise HTTPException(409, "custody_append_only: registrar una rectificación en /api/evidence")


@router.delete("/custody-actions/{action_id}")
def delete_action(action_id: int, db: Session = Depends(get_db)):
    get_or_404(db, ChainOfCustodyAction, action_id)
    raise HTTPException(409, "custody_append_only: registrar una rectificación en /api/evidence")


@router.get("/cases/{case_id}/custody-actions", response_model=list[CustodyActionRead])
def list_actions(case_id: int, evidence_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(ChainOfCustodyAction).filter_by(case_id=case_id)
    if evidence_id:
        query = query.filter_by(evidence_id=evidence_id)
    return query.order_by(ChainOfCustodyAction.action_at).all()


@router.get("/cases/{case_id}/custody-actions/export")
def export_actions(case_id: int, db: Session = Depends(get_db)):
    actions = list_actions(case_id, db=db)
    text = "\n".join(f"{a.action_at} | {a.action_type} | Evidencia {a.evidence_id or '-'} | {a.detailed_description}" for a in actions)
    from operia.exports.paths import new_export_path
    path = new_export_path(f"bitacora-caso-{case_id}.md")
    path.write_text(f"# Bitacora Forense Caso {case_id}\n\n{text}", encoding="utf-8")
    return FileResponse(path)


@router.post("/findings", response_model=FindingRead)
def create_finding(payload: FindingCreate, db: Session = Depends(get_db)):
    if not payload.evidence_id and not payload.supporting_evidence:
        raise HTTPException(status_code=400, detail="El hallazgo debe vincular evidencia o indicar evidencia de respaldo. No se permite saltar de dato tÃ©cnico a conclusiÃ³n.")
    if payload.evidence_id:
        evidence = get_or_404(db, Evidence, payload.evidence_id)
        if evidence.case_id != payload.case_id:
            raise HTTPException(status_code=400, detail="La evidencia seleccionada no pertenece al caso.")
        if not payload.technical_data_id and evidence.technical_data_id:
            payload.technical_data_id = evidence.technical_data_id
    if payload.technical_data_id:
        data = get_or_404(db, TechnicalData, payload.technical_data_id)
        if data.case_id != payload.case_id:
            raise HTTPException(status_code=400, detail="El dato tÃ©cnico seleccionado no pertenece al caso.")
    item = Finding(**payload.model_dump())
    db.add(item)
    db.add(ChainOfCustodyAction(case_id=payload.case_id, evidence_id=payload.evidence_id, action_type="anÃ¡lisis", detailed_description=f"Hallazgo creado: {payload.title}"))
    db.commit()
    db.refresh(item)
    return item


@router.get("/cases/{case_id}/findings", response_model=list[FindingRead])
def list_findings(case_id: int, db: Session = Depends(get_db)):
    return db.query(Finding).filter_by(case_id=case_id).order_by(desc(Finding.created_at)).all()


@router.post("/findings/{finding_id}/{status}", response_model=FindingRead)
def set_finding_status(finding_id: int, status: str, db: Session = Depends(get_db)):
    item = get_or_404(db, Finding, finding_id)
    item.status = status
    db.commit()
    db.refresh(item)
    return item


@router.put("/findings/{finding_id}", response_model=FindingRead)
def update_finding(finding_id: int, payload: FindingCreate, db: Session = Depends(get_db)):
    item = update_from_payload(get_or_404(db, Finding, finding_id), payload)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/findings/{finding_id}")
def delete_finding(finding_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Finding, finding_id))
    db.commit()
    return {"ok": True}


@router.post("/hypotheses", response_model=HypothesisRead)
def create_hypothesis(payload: HypothesisCreate, db: Session = Depends(get_db)):
    item = Hypothesis(**payload.model_dump())
    db.add(item)
    db.add(ChainOfCustodyAction(case_id=payload.case_id, action_type="generaciÃ³n de hipÃ³tesis", detailed_description=f"HipÃ³tesis creada: {payload.title}"))
    db.commit()
    db.refresh(item)
    return item


@router.get("/cases/{case_id}/hypotheses", response_model=list[HypothesisRead])
def list_hypotheses(case_id: int, db: Session = Depends(get_db)):
    return db.query(Hypothesis).filter_by(case_id=case_id).order_by(desc(Hypothesis.created_at)).all()


@router.put("/hypotheses/{hypothesis_id}", response_model=HypothesisRead)
def update_hypothesis(hypothesis_id: int, payload: HypothesisCreate, db: Session = Depends(get_db)):
    item = update_from_payload(get_or_404(db, Hypothesis, hypothesis_id), payload)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/hypotheses/{hypothesis_id}")
def delete_hypothesis(hypothesis_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Hypothesis, hypothesis_id))
    db.commit()
    return {"ok": True}


@router.post("/legal-sources", response_model=LegalSourceRead)
def create_legal_source(payload: LegalSourceCreate, db: Session = Depends(get_db)):
    item = LegalSource(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/legal-sources", response_model=list[LegalSourceRead])
def list_legal_sources(db: Session = Depends(get_db)):
    return db.query(LegalSource).order_by(LegalSource.title).all()


@router.post("/legal-sources/sync-official")
def sync_legal_sources(db: Session = Depends(get_db)):
    updated = sync_official_sources(db)
    db.commit()
    return {
        "updated": updated,
        "message": "Fuentes oficiales sincronizadas. La doctrina, jurisprudencia o citas no cargadas siguen marcadas como Fuente pendiente de verificaciÃ³n.",
    }


@router.put("/legal-sources/{source_id}", response_model=LegalSourceRead)
def update_legal_source(source_id: int, payload: LegalSourceCreate, db: Session = Depends(get_db)):
    item = update_from_payload(get_or_404(db, LegalSource, source_id), payload)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/legal-sources/{source_id}")
def delete_legal_source(source_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, LegalSource, source_id))
    db.commit()
    return {"ok": True}


@router.post("/legal-mappings", response_model=LegalMappingRead)
def create_legal_mapping(payload: LegalMappingCreate, db: Session = Depends(get_db)):
    item = LegalMapping(**payload.model_dump())
    db.add(item)
    db.add(ChainOfCustodyAction(case_id=payload.case_id, action_type="revisiÃ³n jurÃ­dica", detailed_description=f"Encuadre legal cargado: {payload.legal_area}"))
    db.commit()
    db.refresh(item)
    return item


@router.get("/cases/{case_id}/legal-mappings", response_model=list[LegalMappingRead])
def list_legal_mappings(case_id: int, db: Session = Depends(get_db)):
    return db.query(LegalMapping).filter_by(case_id=case_id).order_by(desc(LegalMapping.created_at)).all()


@router.post("/cases/{case_id}/ai/legal-analysis")
def automatic_legal_analysis(case_id: int, apply: bool = True, db: Session = Depends(get_db)):
    case = get_or_404(db, Case, case_id)
    if apply:
        created, analysis = apply_automatic_legal_mappings(case)
        for item in created:
            db.add(item)
        db.add(ChainOfCustodyAction(
            case_id=case.id,
            action_type="revisiÃ³n jurÃ­dica",
            detailed_description=f"IA legal automÃ¡tica generÃ³ {len(created)} encuadre(s) preliminar(es) y clasificÃ³ el incidente como: {', '.join(analysis['incident_classification'])}.",
            tool_used="Operia IA legal local",
            legal_observations=analysis["defensible_conclusion"],
            status="requiere revisiÃ³n humana",
        ))
        db.commit()
        analysis["created_mappings"] = len(created)
        return analysis
    analysis = generate_automatic_legal_analysis(case)
    analysis["created_mappings"] = 0
    return analysis


@router.post("/cases/{case_id}/ai/enrich-consistency")
def enrich_case_consistency(case_id: int, apply: bool = True, db: Session = Depends(get_db)):
    case = get_or_404(db, Case, case_id)
    result = enrich_case(case, apply=apply)
    if apply:
        db.commit()
    return result


@router.put("/legal-mappings/{mapping_id}", response_model=LegalMappingRead)
def update_legal_mapping(mapping_id: int, payload: LegalMappingCreate, db: Session = Depends(get_db)):
    item = update_from_payload(get_or_404(db, LegalMapping, mapping_id), payload)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/legal-mappings/{mapping_id}")
def delete_legal_mapping(mapping_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, LegalMapping, mapping_id))
    db.commit()
    return {"ok": True}


@router.post("/damage-items", response_model=DamageItemRead)
def create_damage_item(payload: DamageItemCreate, db: Session = Depends(get_db)):
    item = DamageItem(**payload.model_dump())
    db.add(item)
    db.add(ChainOfCustodyAction(case_id=payload.case_id, action_type="cuantificaciÃ³n econÃ³mica", detailed_description=f"DaÃ±o cargado: {payload.concept} {payload.amount} {payload.currency}"))
    db.commit()
    db.refresh(item)
    return item


@router.get("/cases/{case_id}/damage-items", response_model=list[DamageItemRead])
def list_damage_items(case_id: int, db: Session = Depends(get_db)):
    return db.query(DamageItem).filter_by(case_id=case_id).order_by(desc(DamageItem.created_at)).all()


@router.put("/damage-items/{damage_id}", response_model=DamageItemRead)
def update_damage_item(damage_id: int, payload: DamageItemCreate, db: Session = Depends(get_db)):
    item = update_from_payload(get_or_404(db, DamageItem, damage_id), payload)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/damage-items/{damage_id}")
def delete_damage_item(damage_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, DamageItem, damage_id))
    db.commit()
    return {"ok": True}


@router.post("/cases/{case_id}/damage-total")
def calculate_damage(case_id: int, methodology: str = "DaÃ±o total estimado", db: Session = Depends(get_db)):
    items = db.query(DamageItem).filter_by(case_id=case_id).all()
    total = sum(item.amount for item in items)
    calculation = DamageCalculation(case_id=case_id, methodology=methodology, total_amount=total, formula_summary="Suma simple de conceptos cargados")
    db.add(calculation)
    db.commit()
    return {"case_id": case_id, "total": total, "currency": items[0].currency if items else "ARS", "methodology": methodology}


@router.post("/cases/{case_id}/reports/generate", response_model=ReportRead)
def generate_report(case_id: int, author: str = "", db: Session = Depends(get_db)):
    case = get_or_404(db, Case, case_id)
    db.expire(
        case,
        [
            "evidence",
            "actions",
            "findings",
            "hypotheses",
            "legal_mappings",
            "participants",
            "damage_items",
            "rubric_evaluations",
            "deepfake_analyses",
            "blockchain_transactions",
            "iot_devices",
        ],
    )
    markdown = build_integral_markdown(case)
    report = Report(case=case, title=f"Informe integral - {case.title}", author=author, markdown_content=markdown)
    db.add(report)
    db.flush()
    report.sections = populate_report_sections(report, markdown)
    report.versions.append(snapshot_report(report, author, "GeneraciÃ³n inicial automÃ¡tica"))
    db.commit()
    db.refresh(report)
    return report


@router.get("/cases/{case_id}/reports", response_model=list[ReportRead])
def list_reports(case_id: int, db: Session = Depends(get_db)):
    return db.query(Report).filter_by(case_id=case_id).order_by(desc(Report.updated_at)).all()


@router.get("/reports/{report_id}", response_model=ReportRead)
def read_report(report_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Report, report_id)


@router.put("/reports/{report_id}", response_model=ReportRead)
def update_report(report_id: int, payload: ReportUpdate, db: Session = Depends(get_db)):
    report = get_or_404(db, Report, report_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(report, key, value)
    db.add(snapshot_report(report, payload.author or report.author, "Edicion manual del informe"))
    db.commit()
    db.refresh(report)
    return report


@router.post("/reports/{report_id}/duplicate", response_model=ReportRead)
def duplicate_report(report_id: int, db: Session = Depends(get_db)):
    report = get_or_404(db, Report, report_id)
    duplicate = Report(case_id=report.case_id, title=f"{report.title} - copia", version="1.0", author=report.author, markdown_content=report.markdown_content, template_used=report.template_used)
    db.add(duplicate)
    db.commit()
    db.refresh(duplicate)
    return duplicate


@router.get("/reports/{report_id}/versions")
def list_report_versions(report_id: int, db: Session = Depends(get_db)):
    return db.query(ReportVersion).filter_by(report_id=report_id).order_by(desc(ReportVersion.created_at)).all()


@router.get("/reports/{report_id}/sections")
def list_report_sections(report_id: int, db: Session = Depends(get_db)):
    get_or_404(db, Report, report_id)
    return db.query(ReportSection).filter_by(report_id=report_id).order_by(ReportSection.order_index).all()


@router.put("/report-sections/{section_id}")
def update_report_section(section_id: int, payload: SectionUpdate, db: Session = Depends(get_db)):
    section = get_or_404(db, ReportSection, section_id)
    section.content = payload.content
    report = section.report
    ordered = db.query(ReportSection).filter_by(report_id=report.id).order_by(ReportSection.order_index).all()
    report.markdown_content = "# Operia Forensic Legal Report\n\n" + "\n\n".join(
        f"## {item.title}\n\n{item.content.strip()}" for item in ordered
    )
    db.add(snapshot_report(report, payload.user, f"EdiciÃ³n manual de secciÃ³n: {section.title}"))
    db.commit()
    db.refresh(section)
    return section


@router.post("/reports/{report_id}/review", response_model=ReviewResult)
def review_report_endpoint(report_id: int, db: Session = Depends(get_db)):
    report = get_or_404(db, Report, report_id)
    result = review_report(report, report.case)
    report.review_score = result["score"]
    db.add(ReportReview(report_id=report.id, score=result["score"], status=result["status"], critical_errors="\n".join(result["critical_errors"]), warnings="\n".join(result["warnings"]), suggestions="\n".join(result["suggestions"]), incomplete_sections="\n".join(result["incomplete_sections"]), unsupported_conclusions="\n".join(result["unsupported_conclusions"])))
    db.commit()
    return result


@router.post("/reports/{report_id}/polish", response_model=ReportRead)
def polish_report_endpoint(report_id: int, db: Session = Depends(get_db)):
    report = get_or_404(db, Report, report_id)
    report.markdown_content = polish_report_markdown(report)
    report.status = "en revision"
    db.add(snapshot_report(report, "Operia IA", "Emporlijado automÃ¡tico con encuadre legal, tipo de cibercrimen y enfoque para competencia"))
    db.commit()
    db.refresh(report)
    return report


@router.post("/reports/{report_id}/ai/evaluate-case", response_model=CaseEvaluationResult)
def evaluate_case_from_report(report_id: int, apply: bool = True, db: Session = Depends(get_db)):
    report = get_or_404(db, Report, report_id)
    evaluation = evaluate_report_case(report)
    if apply:
        block = evaluation_to_markdown(evaluation)
        marker = "## EvaluaciÃ³n integral IA del caso"
        if marker in report.markdown_content:
            report.markdown_content = report.markdown_content.split(marker, 1)[0].rstrip() + "\n\n" + block.strip() + "\n"
        else:
            report.markdown_content = (report.markdown_content or "").rstrip() + "\n\n" + block.strip() + "\n"

        existing = db.query(ReportSection).filter_by(report_id=report.id, title="EvaluaciÃ³n integral IA del caso").first()
        if existing:
            existing.content = block.split(marker, 1)[1].strip() if marker in block else block
        else:
            last_order = max([section.order_index for section in report.sections] or [0])
            report.sections.append(ReportSection(
                report=report,
                order_index=last_order + 1,
                title="EvaluaciÃ³n integral IA del caso",
                content=block.split(marker, 1)[1].strip() if marker in block else block,
                section_type="ia",
            ))
        report.review_score = evaluation["overall_score"]
        report.status = "en revisiÃ³n"
        db.add(snapshot_report(report, "Operia IA", "EvaluaciÃ³n integral automÃ¡tica del caso desde el informe"))
        db.add(ChainOfCustodyAction(
            case_id=report.case_id,
            action_type="revisiÃ³n",
            detailed_description=f"IA evaluÃ³ integralmente el caso desde el informe #{report.id}. Score: {evaluation['overall_score']}/100.",
            tool_used="Operia IA evaluador local",
            result_obtained=evaluation["defensible_conclusion"],
            legal_observations=evaluation["legal_justification"],
            status="requiere revisiÃ³n humana",
        ))
        db.commit()
    return evaluation


@router.get("/reports/{report_id}/export/{fmt}")
def export_report(report_id: int, fmt: str, db: Session = Depends(get_db)):
    report = get_or_404(db, Report, report_id)
    exporters = {"markdown": export_markdown, "html": export_html, "docx": export_docx, "pdf": export_pdf}
    if fmt not in exporters:
        raise HTTPException(status_code=400, detail="Formato no soportado")
    path = exporters[fmt](report)
    return FileResponse(path, filename=path.name)


@router.post("/reports/{report_id}/presentations/generate", response_model=PresentationRead)
def generate_presentation(report_id: int, presentation_type: str = "PresentaciÃ³n ejecutiva breve", db: Session = Depends(get_db)):
    report = get_or_404(db, Report, report_id)
    presentation = build_presentation(report.case, report, presentation_type)
    db.add(presentation)
    db.commit()
    db.refresh(presentation)
    return presentation


@router.get("/cases/{case_id}/presentations", response_model=list[PresentationRead])
def list_presentations(case_id: int, db: Session = Depends(get_db)):
    return db.query(Presentation).filter_by(case_id=case_id).order_by(desc(Presentation.updated_at)).all()


@router.get("/presentations/{presentation_id}/slides", response_model=list[PresentationSlideRead])
def list_presentation_slides(presentation_id: int, db: Session = Depends(get_db)):
    presentation = get_or_404(db, Presentation, presentation_id)
    return sorted(presentation.slides, key=lambda slide: slide.slide_number)


@router.put("/presentation-slides/{slide_id}", response_model=PresentationSlideRead)
def update_presentation_slide(slide_id: int, payload: PresentationSlideUpdate, db: Session = Depends(get_db)):
    slide = get_or_404(db, PresentationSlide, slide_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(slide, key, value)
    db.commit()
    db.refresh(slide)
    return slide


@router.post("/presentations/{presentation_id}/review", response_model=PresentationReviewResult)
def review_presentation_endpoint(presentation_id: int, db: Session = Depends(get_db)):
    presentation = get_or_404(db, Presentation, presentation_id)
    result = review_presentation(presentation)
    presentation.review_score = result["score"]
    db.add(PresentationReview(presentation_id=presentation.id, score=result["score"], clarity=result["clarity"], evidentiary_strength=result["evidentiary_strength"], narrative_coherence=result["narrative_coherence"], legal_solidity=result["legal_solidity"], visual_quality=result["visual_quality"], oral_exposure_risks="\n".join(result["oral_exposure_risks"]), recommendations="\n".join(result["recommendations"])))
    db.commit()
    return result


@router.get("/presentations/{presentation_id}/export/pdf")
def export_presentation(presentation_id: int, db: Session = Depends(get_db)):
    presentation = get_or_404(db, Presentation, presentation_id)
    path = export_presentation_pdf(presentation)
    db.commit()
    return FileResponse(path, filename=path.name)


@router.get("/templates")
def list_templates(db: Session = Depends(get_db)):
    return db.query(Template).order_by(Template.name).all()

