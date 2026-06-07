from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from operia.core.database import get_db
from operia.cases.models import Case
from operia.geo_trace.models import GeoTarget, GeoTraceAnalysis
from operia.geo_trace.services import analyze_url, create_target_map, evidence_hash, extract_ips, extract_urls, geolocate_ip
from operia.exports.service import export_pdf
from operia.identity.dependencies import CurrentUser, require_permission
from operia.legal_report.services.report_service import populate_report_sections, snapshot_report
from operia.reports.models import Report

router = APIRouter()


def as_dict(obj: Any) -> dict[str, Any]:
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}


def target_payload(origin: str, data: dict[str, Any], analysis_id: int, case_id: int | None, url: str | None = None, host: str | None = None) -> dict[str, Any]:
    geo = data.get("geo") if isinstance(data.get("geo"), dict) else data
    return {
        "analysis_id": analysis_id,
        "case_id": case_id,
        "origin": origin,
        "ip": data.get("ip") or geo.get("ip"),
        "url": url or data.get("url"),
        "host": host or data.get("host"),
        "target_type": str(data.get("target_type") or geo.get("target_type") or "unknown"),
        "country": geo.get("country"),
        "city": geo.get("city"),
        "isp": geo.get("isp"),
        "org": geo.get("org"),
        "asn": geo.get("asn"),
        "lat": geo.get("lat"),
        "lon": geo.get("lon"),
        "geo_source": geo.get("geo_source"),
        "confidence": str(geo.get("confidence") or "media"),
        "category": geo.get("category"),
        "network_category": geo.get("network_category"),
        "risk": str(geo.get("risk") or "bajo"),
        "score": int(geo.get("score") or 0),
        "fraud_probability": float(geo.get("fraud_probability") or 0),
        "expected_cost": float(geo.get("expected_cost") or 0),
        "economic_impact": float(geo.get("economic_impact") or 0),
        "indicators": ", ".join(geo.get("indicators") or []),
        "message": str(data.get("message") or geo.get("message") or ""),
    }


@router.get("/")
def status() -> dict[str, object]:
    return {
        "module": "Geo Trace",
        "status": "migrated",
        "description": "IP/URL parsing, enrichment, forensic risk scoring, map generation, and shared PDF export.",
        "shared_dependencies": ["cases", "reports", "exports", "common_database", "shared_config", "dashboard"],
    }


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    return {
        "analyses": db.query(GeoTraceAnalysis).count(),
        "targets": db.query(GeoTarget).count(),
        "high_risk_targets": db.query(GeoTarget).filter(GeoTarget.risk == "alto").count(),
        "mapped_targets": db.query(GeoTarget).filter(GeoTarget.lat.is_not(None), GeoTarget.lon.is_not(None)).count(),
    }


@router.post("/analyze")
def create_analysis(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("evidence:write")),
):
    case_id = payload.get("case_id")
    if case_id and not db.get(Case, int(case_id)):
        raise HTTPException(404, "Caso no encontrado")
    text = payload.get("input_text") or ""
    ips = extract_ips(text)
    urls = extract_urls(text)
    analysis = GeoTraceAnalysis(case_id=case_id, title=payload.get("title") or "Geo Trace analysis", input_text=text)
    db.add(analysis)
    db.flush()
    targets_for_map: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    for ip in ips:
        result = geolocate_ip(ip)
        row_payload = target_payload("IP", result, analysis.id, case_id)
        row = GeoTarget(**row_payload)
        db.add(row)
        targets_for_map.append(row_payload)
        results.append(row_payload)
    for url in urls:
        result = analyze_url(url)
        row_payload = target_payload("URL", result, analysis.id, case_id, url=url, host=result.get("host"))
        row = GeoTarget(**row_payload)
        db.add(row)
        targets_for_map.append(row_payload)
        results.append(row_payload)
    analysis.evidence_hash = evidence_hash({"input": text, "targets": results})
    analysis.summary = f"IPs detectadas: {len(ips)}. URLs detectadas: {len(urls)}. Targets registrados: {len(results)}."
    analysis.map_path = str(create_target_map(targets_for_map, f"geo_trace_analysis_{analysis.id}.html"))
    db.commit()
    db.refresh(analysis)
    return {"analysis": as_dict(analysis), "targets": results}


@router.get("/analyses")
def list_analyses(case_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(GeoTraceAnalysis)
    if case_id is not None:
        query = query.filter(GeoTraceAnalysis.case_id == case_id)
    return [as_dict(row) for row in query.order_by(GeoTraceAnalysis.id.desc()).all()]


@router.get("/targets")
def list_targets(analysis_id: int | None = None, case_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(GeoTarget)
    if analysis_id is not None:
        query = query.filter(GeoTarget.analysis_id == analysis_id)
    if case_id is not None:
        query = query.filter(GeoTarget.case_id == case_id)
    return [as_dict(row) for row in query.order_by(GeoTarget.id.desc()).all()]


@router.get("/analyses/{analysis_id}/map")
def export_map(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.get(GeoTraceAnalysis, analysis_id)
    if not analysis or not analysis.map_path:
        raise HTTPException(404, "Mapa no encontrado")
    return FileResponse(analysis.map_path, media_type="text/html", filename=f"geo-trace-{analysis_id}.html")


@router.post("/analyses/{analysis_id}/export/pdf")
def export_analysis_pdf(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:write")),
):
    analysis = db.get(GeoTraceAnalysis, analysis_id)
    if not analysis:
        raise HTTPException(404, "Analisis no encontrado")
    if not analysis.case_id:
        raise HTTPException(400, "El analisis debe estar asociado a un caso para exportar PDF")
    case = db.get(Case, analysis.case_id) if analysis.case_id else None
    targets = db.query(GeoTarget).filter(GeoTarget.analysis_id == analysis_id).order_by(GeoTarget.id.asc()).all()
    lines = [
        "# Geo Trace Forensic Report",
        "",
        f"## Analisis",
        f"- ID: {analysis.id}",
        f"- Caso: {case.case_code if case else 'sin caso'}",
        f"- Titulo: {analysis.title}",
        f"- Hash evidencia logica: `{analysis.evidence_hash or 'pendiente'}`",
        "",
        "## Resumen",
        analysis.summary,
        "",
        "## Targets",
    ]
    lines += [
        f"- {target.origin} {target.ip or target.host or '-'} | {target.country or '-'} / {target.city or '-'} | riesgo: {target.risk} | score: {target.score} | impacto: {target.economic_impact}"
        for target in targets
    ] or ["- Sin targets."]
    report = Report(
        case_id=analysis.case_id,
        title=f"Geo Trace - {analysis.title}",
        author="OPERIA Geo Trace",
        markdown_content="\n".join(lines),
    )
    db.add(report)
    db.flush()
    report.sections = populate_report_sections(report, report.markdown_content)
    report.versions.append(snapshot_report(report, report.author, "Generacion desde Geo Trace"))
    db.commit()
    db.refresh(report)
    return FileResponse(export_pdf(report), filename=f"geo-trace-analysis-{analysis_id}.pdf")
