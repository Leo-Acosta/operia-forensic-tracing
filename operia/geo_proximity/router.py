from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from operia.core.database import get_db
from operia.cases.models import Case
from operia.geo_proximity.models import GeoProximityQuery, LocationReference
from operia.geo_proximity.services import distance_km
from operia.exports.service import export_pdf
from operia.identity.dependencies import CurrentUser, require_permission
from operia.legal_report.services.report_service import populate_report_sections, snapshot_report
from operia.reports.models import Report

router = APIRouter()


def as_dict(obj: Any) -> dict[str, Any]:
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}


@router.get("/")
def status() -> dict[str, object]:
    return {
        "module": "Geo Proximity",
        "status": "migrated",
        "description": "Nearest-location lookup migrated from geo-apple-demo without Flask.",
        "shared_dependencies": ["cases", "reports", "exports", "common_database", "shared_config", "dashboard"],
    }


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    return {
        "locations": db.query(LocationReference).count(),
        "queries": db.query(GeoProximityQuery).count(),
    }


@router.get("/locations")
def list_locations(db: Session = Depends(get_db)):
    return [as_dict(row) for row in db.query(LocationReference).order_by(LocationReference.name.asc()).all()]


@router.post("/locations")
def create_location(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("evidence:write")),
):
    row = LocationReference(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return as_dict(row)


@router.get("/nearest")
def nearest(
    lat: float,
    lon: float,
    case_id: int | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("evidence:write")),
):
    if case_id and not db.get(Case, case_id):
        raise HTTPException(404, "Caso no encontrado")
    query = db.query(LocationReference)
    if category:
        query = query.filter(LocationReference.category == category)
    locations = query.all()
    if not locations:
        raise HTTPException(404, "No hay ubicaciones de referencia cargadas")
    best = min(locations, key=lambda item: distance_km(lat, lon, item.lat, item.lon))
    distance = distance_km(lat, lon, best.lat, best.lon)
    row = GeoProximityQuery(
        case_id=case_id,
        lat=lat,
        lon=lon,
        nearest_location_id=best.id,
        nearest_name=best.name,
        distance_km=distance,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"query": as_dict(row), "nearest": as_dict(best)}


@router.get("/queries")
def list_queries(case_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(GeoProximityQuery)
    if case_id is not None:
        query = query.filter(GeoProximityQuery.case_id == case_id)
    return [as_dict(row) for row in query.order_by(GeoProximityQuery.id.desc()).all()]


@router.post("/queries/{query_id}/export/pdf")
def export_query_pdf(
    query_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:write")),
):
    query = db.get(GeoProximityQuery, query_id)
    if not query:
        raise HTTPException(404, "Consulta no encontrada")
    if not query.case_id:
        raise HTTPException(400, "La consulta debe estar asociada a un caso para exportar PDF")
    case = db.get(Case, query.case_id)
    lines = [
        "# Geo Proximity Report",
        "",
        "## Consulta",
        f"- Caso: {case.case_code if case else query.case_id}",
        f"- Latitud: {query.lat}",
        f"- Longitud: {query.lon}",
        f"- Ubicacion mas cercana: {query.nearest_name}",
        f"- Distancia: {query.distance_km:.2f} km",
        "",
        "## Alcance",
        "Este informe documenta una consulta de proximidad geografica derivada del modulo geo-apple-demo.",
    ]
    report = Report(
        case_id=query.case_id,
        title=f"Geo Proximity - {query.nearest_name}",
        author="OPERIA Geo Proximity",
        markdown_content="\n".join(lines),
    )
    db.add(report)
    db.flush()
    report.sections = populate_report_sections(report, report.markdown_content)
    report.versions.append(snapshot_report(report, report.author, "Generacion desde Geo Proximity"))
    db.commit()
    db.refresh(report)
    return FileResponse(export_pdf(report), filename=f"geo-proximity-query-{query_id}.pdf")
