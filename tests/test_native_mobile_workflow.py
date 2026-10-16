import base64
import importlib
import json
import sqlite3
import sys
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

from apps.api.main import app
from operia.core.database import Base, get_db
from operia.forensic_engine.canonical import canonical_bytes, sha256
from operia.forensic_jobs import worker
from operia.forensic_jobs.models import Acquisition, ExaminationJob, ExportRecord, IndicatorSet, JobEvent
from operia.identity.dependencies import CurrentUser, get_optional_user
from operia.cases.models import Case

FIXTURES = Path(__file__).parent / "fixtures" / "native_mobile"
META = {"authorization": "Autorización sintética para pruebas", "scope": "Solo fixture sintético original",
    "provenance": "Corpus de pruebas de este proyecto", "acquisition_method": "fixture original",
    "acquisition_date_original": "desconocida", "retention_policy": "Solo pruebas locales autorizadas",
    "restrictions": "No usar como muestra real", "declared_os_version": "desconocida"}


def database_factory():
    # Uses exactly the database overridden by the existing client fixture.
    def factory():
        generator = app.dependency_overrides[get_db]()
        db = next(generator)
        # Session.close is enough; keep generator alive for the context lifetime.
        db.info["test_generator"] = generator
        return db
    return factory


def setup(client, headers, platform="android", filename="packages.txt", format="android-pm-packages", code="NATIVE-SYNTHETIC", raw=None):
    case = client.post("/api/cases", headers=headers, json={"case_code": code, "title": "Fixture propio"})
    assert case.status_code == 200, case.text
    case_id = case.json()["id"]
    root = f"/api/mobile-forensics/native/cases/{case_id}"
    device = client.post(f"/api/mobile-forensics/cases/{case_id}/devices", headers=headers,
        json={"label": "Fixture propio", "platform": platform}).json()
    original = (FIXTURES / filename).read_bytes() if raw is None else raw
    acquisition = client.post(root + "/acquisitions", headers=headers, json={"device_id": device["id"],
        "metadata": META, "filename": filename, "format": format, "content_base64": base64.b64encode(original).decode()})
    assert acquisition.status_code == 200, acquisition.text
    return root, acquisition.json(), original


def enqueue(client, headers, root, acquisition, **extra):
    response = client.post(root + "/jobs", headers=headers, json={"acquisition_id": acquisition["id"], **extra})
    assert response.status_code == 200, response.text
    return response.json()


def native_review(ids, **changes):
    return {"conclusion": "inconcluso", "artifact_ids": ids, "rationale": "Observaciones sintéticas; sin dispositivo real",
        "alternatives": "Fixture de prueba sin inteligencia de amenazas", "limitations": "No constituye validación real",
        "current_activity": "No determinable con estos datos", "chronology": "Sin cronología de ataque comprobada",
        "attribution": "Sin evidencia para atribuir responsables", "coverage_justification": "Alcance restringido al archivo sintético", **changes}


@pytest.mark.parametrize("platform,filename,format,expected", [
    ("ios", "profile.plist", "apple-profile-plist", 1),
    ("android", "packages.txt", "android-pm-packages", 2),
    ("android", "logcat-epoch.txt", "android-logcat-epoch", 3),
])
def test_native_end_to_end_real_worker_subprocess(client, admin_headers, platform, filename, format, expected):
    root, acquisition, raw = setup(client, admin_headers, platform, filename, format)
    assert acquisition["sha256"] == sha256(raw)
    assert client.get(root + f'/acquisitions/{acquisition["id"]}/original', headers=admin_headers).content == raw
    job = enqueue(client, admin_headers, root, acquisition, demo_rules=True)
    assert job["state"] == "pendiente"
    assert enqueue(client, admin_headers, root, acquisition, demo_rules=True)["id"] == job["id"]
    path = root + f'/jobs/{job["id"]}'
    assert client.post(path + "/exports", headers=admin_headers, json={"format": "json"}).status_code == 409
    assert worker.run_once(database_factory(), timeout=15)
    detail = client.get(path, headers=admin_headers)
    assert detail.status_code == 200, detail.text
    value = detail.json()
    assert value["job"]["state"] == "completado_con_limitaciones", value
    result = value["result"]
    assert result["origin"] == "operia_native" and result["counts"]["artifacts"] == expected
    ids = [item["id"] for item in result["artifacts"]]
    assert client.post(path + "/reviews", headers=admin_headers, json=native_review(ids,
        conclusion="sin_indicios_en_el_alcance_examinado")).status_code == 422  # DEMO alone is insufficient.
    assert client.post(path + "/reviews", headers=admin_headers, json=native_review(["other-case-id"])).status_code == 422
    first = client.post(path + "/reviews", headers=admin_headers, json=native_review(ids))
    assert first.status_code == 200, first.text
    export = client.post(path + "/exports", headers=admin_headers, json={"format": "json"}).json()
    original_snapshot = client.get(path + f'/exports/{export["id"]}', headers=admin_headers)
    assert sha256(original_snapshot.content) == export["sha256"]
    assert original_snapshot.json()["report_id"] == export["id"]
    assert original_snapshot.json()["result_sha256"] == value["job"]["result_sha256"]
    assert client.post(path + "/reviews", headers=admin_headers, json=native_review(ids, rationale="Corrección sintética explícita del análisis")).status_code == 200
    assert client.get(path + f'/exports/{export["id"]}', headers=admin_headers).content == original_snapshot.content
    csv_export = client.post(path + "/exports", headers=admin_headers, json={"format": "csv"}).json()
    csv = client.get(path + f'/exports/{csv_export["id"]}', headers=admin_headers)
    assert csv.status_code == 200 and b"normalized_utc" in csv.content
    assert len(client.get(path, headers=admin_headers).json()["reviews"]) == 2
    assert client.post(path + "/reviews", headers=admin_headers, json=native_review(ids,
        conclusion="compromiso_confirmado_por_revision_profesional")).status_code == 422


def test_indicator_sets_are_exact_scoped_and_used(client, admin_headers):
    root, acquisition, raw = setup(client, admin_headers, "android", "logcat-epoch.txt", "android-logcat-epoch")
    indicators = (FIXTURES / "indicators.json").read_bytes()
    response = client.post(root + "/indicator-sets", headers=admin_headers, content=indicators)
    assert response.status_code == 200, response.text
    assert response.json()["sha256"] == sha256(indicators)
    assert client.post(root + "/indicator-sets", headers=admin_headers, content=indicators).status_code == 409
    job = enqueue(client, admin_headers, root, acquisition, indicator_set_id=response.json()["id"])
    worker.run_once(database_factory(), timeout=15)
    path = root + f'/jobs/{job["id"]}'
    detail = client.get(path, headers=admin_headers).json()
    assert detail["result"]["counts"]["alerts"] == 2
    assert detail["result"]["configuration"]["indicator_set_sha256"] == sha256(indicators)
    export = client.post(path + "/exports", headers=admin_headers, json={}).json()
    snapshot = client.get(path + f'/exports/{export["id"]}', headers=admin_headers).json()
    assert base64.b64decode(snapshot["indicator_original_base64"]) == indicators
    assert client.post(path + "/reviews", headers=admin_headers, json=native_review(
        [detail["result"]["artifacts"][0]["id"]], conclusion="sin_indicios_en_el_alcance_examinado")).status_code == 422


def test_scope_auth_role_and_cross_case_objects(client, admin_headers):
    root, acquisition, raw = setup(client, admin_headers)
    other, other_acq, _ = setup(client, admin_headers, code="NATIVE-OTHER")
    job = enqueue(client, admin_headers, root, acquisition)
    assert client.post(other + "/jobs", headers=admin_headers, json={"acquisition_id": acquisition["id"]}).status_code == 404
    assert client.get(other + f'/jobs/{job["id"]}', headers=admin_headers).status_code == 404
    assert client.get(root + "/acquisitions").status_code == 401
    for org in (None, 99999):
        app.dependency_overrides[get_optional_user] = lambda org=org: CurrentUser(1, org, "Otro", None, "admin")
        for suffix in ("/acquisitions", "/jobs", "/indicator-sets", f'/jobs/{job["id"]}', f'/acquisitions/{acquisition["id"]}/original'):
            assert client.get(root + suffix).status_code == 404
        assert client.post(root + "/jobs", json={"acquisition_id": acquisition["id"]}).status_code == 404
    app.dependency_overrides[get_optional_user] = lambda: CurrentUser(1, acquisition["organization_id"], "Lector", None, "lector")
    assert client.post(root + f'/jobs/{job["id"]}/cancel').status_code == 403
    app.dependency_overrides.pop(get_optional_user)


def test_cancellation_timeout_restart_retry_and_worker_scope(client, admin_headers, monkeypatch):
    root, acquisition, raw = setup(client, admin_headers)
    job = enqueue(client, admin_headers, root, acquisition)
    path = root + f'/jobs/{job["id"]}'
    assert client.post(path + "/cancel", headers=admin_headers).json()["state"] == "cancelado"
    assert not worker.run_once(database_factory())
    assert client.post(path + "/retry", headers=admin_headers).json()["state"] == "pendiente"
    worker.run_once(database_factory(), timeout=0)
    assert client.get(path, headers=admin_headers).json()["job"]["error_code"] == "timeout"
    client.post(path + "/retry", headers=admin_headers)
    original_spawn = worker.spawn_worker
    children = []
    def cancel_running(*args, **kwargs):
        process = original_spawn(*args, **kwargs)
        if args[0] == "native":
            children.append(process)
            assert client.post(path + "/cancel", headers=admin_headers).status_code == 200
        return process
    with monkeypatch.context() as patch:
        patch.setattr(worker, "spawn_worker", cancel_running)
        worker.run_once(database_factory(), timeout=15)
    assert children and children[0].poll() is not None
    assert client.get(path, headers=admin_headers).json()["job"]["state"] == "cancelado"
    client.post(path + "/retry", headers=admin_headers)
    with database_factory()() as db:
        row = db.get(ExaminationJob, job["id"])
        row.state, row.claim_token = "ejecutando", "dead-owner"
        db.commit()
        assert worker.recover_interrupted(db) == 1
    assert client.get(path, headers=admin_headers).json()["job"]["state"] == "interrumpido"
    client.post(path + "/retry", headers=admin_headers)
    with database_factory()() as db:
        db.get(Case, acquisition["case_id"]).organization_id = 99999
        db.commit()
    worker.run_once(database_factory())
    with database_factory()() as db:
        row = db.get(ExaminationJob, job["id"])
        assert row.state == "fallido" and row.error_code == "scope_or_operator_invalid"


def test_corruption_unsupported_empty_and_integrity_failures(client, admin_headers):
    root, acquisition, raw = setup(client, admin_headers, raw=b"", code="EMPTY")
    job = enqueue(client, admin_headers, root, acquisition)
    worker.run_once(database_factory(), timeout=15)
    path = root + f'/jobs/{job["id"]}'
    value = client.get(path, headers=admin_headers).json()
    assert value["result"]["detection_status"] == "sin_datos_analizables"
    assert client.post(path + "/reviews", headers=admin_headers, json=native_review([],
        conclusion="sin_indicios_en_el_alcance_examinado")).status_code == 422
    other, acq, raw = setup(client, admin_headers, raw=b"not a package inventory", code="UNSUPPORTED")
    other_job = enqueue(client, admin_headers, other, acq)
    worker.run_once(database_factory(), timeout=15)
    assert client.get(other + f'/jobs/{other_job["id"]}', headers=admin_headers).json()["result"]["coverage"]["sources"][0]["status"] == "no_compatible"
    with database_factory()() as db:
        row = db.get(ExaminationJob, job["id"])
        row.result_bytes = b"{}"
        db.commit()
    assert client.get(path, headers=admin_headers).status_code == 409


def test_limits_input_mutation_and_lock(client, admin_headers, tmp_path):
    root, acquisition, raw = setup(client, admin_headers)
    job = enqueue(client, admin_headers, root, acquisition)
    with database_factory()() as db:
        db.get(Acquisition, acquisition["id"]).original_bytes = b"changed"
        db.commit()
    worker.run_once(database_factory())
    detail = client.get(root + f'/jobs/{job["id"]}', headers=admin_headers).json()
    assert detail["job"]["state"] == "fallido" and detail["job"]["error_code"] == "input_integrity_failed"
    assert client.get(root + f'/acquisitions/{acquisition["id"]}/original', headers=admin_headers).status_code == 409
    assert client.post(root + "/acquisitions", headers=admin_headers, content=b"x" * (7 * 1024 * 1024 + 1)).status_code == 413
    with worker.worker_lock(tmp_path / "worker.lock"):
        with pytest.raises(RuntimeError):
            with worker.worker_lock(tmp_path / "worker.lock"):
                pass


def test_storage_and_output_quotas_are_enforced(client, admin_headers, monkeypatch):
    from operia.core.config import settings
    root, acquisition, raw = setup(client, admin_headers)
    job = enqueue(client, admin_headers, root, acquisition)
    path = root + f'/jobs/{job["id"]}'
    with monkeypatch.context() as patch:
        patch.setattr(worker, "MAX_OUTPUT_BYTES", 64)
        worker.run_once(database_factory(), timeout=15)
    assert client.get(path, headers=admin_headers).json()["job"]["error_code"] == "output_quota_exceeded"
    client.post(path + "/retry", headers=admin_headers)
    with monkeypatch.context() as patch:
        patch.setattr(settings, "mobile_storage_quota_bytes", 1)
        worker.run_once(database_factory(), timeout=15)
        response = client.post(root + "/jobs", headers=admin_headers, json={"acquisition_id": acquisition["id"], "demo_rules": True})
        assert response.status_code == 409 and "quota" in response.text
    assert client.get(path, headers=admin_headers).json()["job"]["error_code"] == "native_storage_quota_exceeded"


def test_standalone_cli_uses_only_stdlib_and_migration_retains_old_tables(tmp_path):
    import subprocess
    output = tmp_path / "canonical.json"
    completed = subprocess.run([sys.executable, "-S", "-m", "operia.forensic_engine", str(FIXTURES / "profile.plist"),
        "--platform", "ios", "--format", "apple-profile-plist", "--output", str(output)], capture_output=True, timeout=15)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(output.read_bytes())["origin"] == "operia_native"
    engine = create_engine(f"sqlite:///{tmp_path / 'prior.db'}")
    old = [table for table in Base.metadata.sorted_tables if not table.name.startswith("native_mobile_")]
    Base.metadata.create_all(engine, tables=old)
    from operia.mobile_forensics.models import MobileExport
    with engine.begin() as connection:
        # SQLite fixture intentionally uses previous external rows without claiming real provenance.
        connection.execute(MobileExport.__table__.insert().values(id=1, exam_id=1, created_by=1,
            content=b'{"historical":"unchanged"}', sha256=sha256(b'{"historical":"unchanged"}')))
    migration = importlib.import_module("migrations.versions.20261016_0003_native_mobile")
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade(); migration.upgrade(); migration.downgrade()
        assert connection.execute(MobileExport.__table__.select()).mappings().one()["content"] == b'{"historical":"unchanged"}'
        assert "native_mobile_jobs" in inspect(connection).get_table_names()
    engine.dispose()


def test_worker_cli_in_fresh_process_loads_shared_model_graph(client, admin_headers, tmp_path):
    import os
    import subprocess
    root, acquisition, raw = setup(client, admin_headers)
    job = enqueue(client, admin_headers, root, acquisition)
    with database_factory()() as db:
        database_url = str(db.bind.url)
    environment = os.environ.copy()
    environment["OPERIA_DATABASE_URL"] = database_url
    environment["OPERIA_STORAGE_DIR"] = str(tmp_path)
    (tmp_path / "temp").mkdir(exist_ok=True)
    completed = subprocess.run([sys.executable, "-m", "operia.forensic_jobs.worker", "--once"],
        env=environment, capture_output=True, timeout=30)
    assert completed.returncode == 0, completed.stderr
    assert client.get(root + f'/jobs/{job["id"]}', headers=admin_headers).json()["job"]["state"] == "completado_con_limitaciones"


def test_input_change_during_analysis_never_publishes_completed_result(client, admin_headers, monkeypatch):
    root, acquisition, raw = setup(client, admin_headers)
    job = enqueue(client, admin_headers, root, acquisition)
    spawn = worker.spawn_worker
    def changed_input(*args, **kwargs):
        process = spawn(*args, **kwargs)
        if args[0] == "native":
            with database_factory()() as db:
                db.get(Acquisition, acquisition["id"]).original_bytes = b"changed after child input snapshot"
                db.commit()
        return process
    monkeypatch.setattr(worker, "spawn_worker", changed_input)
    worker.run_once(database_factory(), timeout=15)
    value = client.get(root + f'/jobs/{job["id"]}', headers=admin_headers).json()
    assert value["job"]["state"] == "fallido"
    assert value["job"]["error_code"] == "input_changed_during_analysis"
    assert value["result"] is None
