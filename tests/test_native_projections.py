import importlib
import json
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from alembic.migration import MigrationContext
from alembic.operations import Operations
from apps.api.main import app
from operia.identity.dependencies import get_optional_user, CurrentUser
from operia.forensic_jobs import worker
from operia.forensic_jobs.models import AnalysisProjection
from operia.forensic_engine.canonical import sha256
from test_native_mobile_workflow import setup, enqueue, native_review, database_factory


def prepare(client, headers, code="PROJECTION", filename="logcat-epoch.txt", format="android-logcat-epoch"):
    root, acquisition, raw = setup(client, headers, filename=filename, format=format, code=code)
    job = enqueue(client, headers, root, acquisition)
    assert worker.run_once(database_factory(), timeout=15)
    path = root + f"/jobs/{job['id']}"
    artifacts = client.get(path, headers=headers).json()["result"]["artifacts"]
    ids = [a["id"] for a in artifacts]
    revision = client.post(path + "/reviews", headers=headers, json=native_review(ids)).json()
    link = client.post(path + f"/integrations?review_id={revision['id']}", headers=headers).json()
    payload = {"integration_id": link["id"], "artifact_ids": ids,
        "hypothesis_text": "La URL mencionada podria corresponder a actividad de una aplicacion; requiere contraste",
        "facts_to_prove": "Corroborar registros de red independientes y actividad autorizada antes de concluir", "create_geo": True}
    return root, path, payload, acquisition


def test_projection_passive_idempotent_preserved_and_scoped(client, admin_headers, monkeypatch):
    root, path, payload, acquisition = prepare(client, admin_headers)
    def forbidden(*args, **kwargs):
        raise AssertionError("Projection must never use network")
    import operia.geo_trace.services as geo
    monkeypatch.setattr(geo, "geolocate_ip", forbidden)
    monkeypatch.setattr(geo, "analyze_url", forbidden)
    response = client.post(path + "/projections", headers=admin_headers, json=payload)
    assert response.status_code == 200, response.text
    value = response.json()
    assert client.post(path + "/projections", headers=admin_headers, json={**payload, "artifact_ids": list(reversed(payload["artifact_ids"]))}).json() == value
    original = client.get(path + f"/projections/{value['id']}", headers=admin_headers)
    assert sha256(original.content) == value["snapshot_sha256"]
    assert len(original.json()["geo_targets"]) == 2
    case_id = acquisition["case_id"]
    findings = client.get(f"/api/cases/{case_id}/findings", headers=admin_headers).json()
    hypotheses = client.get(f"/api/cases/{case_id}/hypotheses", headers=admin_headers).json()
    assert findings[0]["id"] == value["finding_id"] and findings[0]["status"] == "requiere corroboracion"
    assert hypotheses[0]["id"] == value["hypothesis_id"] and hypotheses[0]["support_degree"] == "bajo"
    targets = client.get(f"/api/geo/trace/targets?analysis_id={value['geo_analysis_id']}", headers=admin_headers).json()
    assert len(targets) == 2
    assert all(t["lat"] is None and t["lon"] is None and t["risk"] == "no_evaluado" and t["score"] == 0 for t in targets)
    assert all(set(json.loads(t["message"])["artifact_ids"]) <= set(payload["artifact_ids"]) for t in targets)
    for route in (f"/api/legal-report/findings/{value['finding_id']}", f"/api/legal-report/hypotheses/{value['hypothesis_id']}"):
        assert client.delete(route, headers=admin_headers).status_code == 409
    new = client.post(path + "/projections", headers=admin_headers, json={**payload, "hypothesis_text": "Hipotesis alternativa, referida a actividad legitima de diagnostico del dispositivo"})
    assert new.status_code == 200 and new.json()["id"] != value["id"]
    assert client.get(path + f"/projections/{value['id']}", headers=admin_headers).content == original.content
    assert len(client.get(path, headers=admin_headers).json()["projections"]) == 2
    app.dependency_overrides[get_optional_user] = lambda: CurrentUser(1, 9999, "Other", None, "admin")
    for url in (path + f"/projections/{value['id']}", f"/api/geo/trace/analyses/{value['geo_analysis_id']}/map", f"/api/geo-trace/analyses/{value['geo_analysis_id']}/map", f"/api/cases/{case_id}/findings"):
        assert client.get(url).status_code == 404
    assert client.post(path + "/projections", json=payload).status_code == 404
    app.dependency_overrides.pop(get_optional_user)
    assert client.get(path + f"/projections/{value['id']}").status_code == 401
    app.dependency_overrides[get_optional_user] = lambda: CurrentUser(1, acquisition["organization_id"], "Reader", None, "lector")
    assert client.post(path + "/projections", json=payload).status_code == 403
    app.dependency_overrides.pop(get_optional_user)


def test_projection_rejects_unreviewed_cross_case_and_corruption(client, admin_headers):
    root, path, payload, acquisition = prepare(client, admin_headers)
    other_root, other_path, other_payload, other = prepare(client, admin_headers, code="OTHER")
    assert client.post(path + "/projections", headers=admin_headers, json={**payload, "integration_id": other_payload["integration_id"]}).status_code == 404
    assert client.post(path + "/projections", headers=admin_headers, json={**payload, "artifact_ids": ["invented"]}).status_code == 422
    assert client.post(path + "/projections", headers=admin_headers, json={**payload, "artifact_ids": payload["artifact_ids"] * 2}).status_code == 422
    response = client.post(path + "/projections", headers=admin_headers, json=payload)
    value = response.json()
    with database_factory()() as db:
        db.get(AnalysisProjection, value["id"]).snapshot_bytes = b"tampered"
        db.commit()
    assert client.get(path + f"/projections/{value['id']}", headers=admin_headers).status_code == 409
    assert client.post(path + "/projections", headers=admin_headers, json=payload).status_code == 409
    assert client.post(f"/api/cases/{other['case_id']}/hypotheses", headers=admin_headers, json={
        "case_id": other["case_id"], "title": "Cross case", "description": "must reject", "finding_ids": str(value["finding_id"])}).status_code == 422


def test_projection_without_network_artifacts_and_additive_migration(client, admin_headers):
    root, path, payload, acquisition = prepare(client, admin_headers, filename="packages.txt", format="android-pm-packages")
    assert client.post(path + "/projections", headers=admin_headers, json=payload).status_code == 422
    value = client.post(path + "/projections", headers=admin_headers, json={**payload, "create_geo": False}).json()
    assert value["geo_analysis_id"] is None
    with database_factory()() as db:
        before = db.get(AnalysisProjection, value["id"]).snapshot_bytes
        migration = importlib.import_module("migrations.versions.20261016_0005_analysis_projection")
        with Operations.context(MigrationContext.configure(db.connection())):
            migration.upgrade()
            migration.upgrade()
            migration.downgrade()
        assert db.get(AnalysisProjection, value["id"]).snapshot_bytes == before
