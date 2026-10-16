"""Synthetic pilot fixtures only; no real acquisitions or MVT execution."""
import base64
import hashlib
import importlib
import json
import sqlite3
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import HTTPException
from sqlalchemy import create_engine, text

from apps.api.main import app
from operia.core.database import Base, get_db
from operia.identity.dependencies import CurrentUser, get_optional_user
from operia.mobile_forensics.models import MobileExam
from operia.mobile_forensics.service import bounded_json, parse_result


META = {"authorization": "Consentimiento sintético de prueba", "data_owner_consent": True,
    "scope": "Únicamente registros sintéticos", "provenance": "Fixture sintético creado para pruebas",
    "acquisition_method": "fixture sintético", "acquisition_date": "desconocida",
    "retention_policy": "Eliminar solo según política del caso de prueba",
    "declared_mvt_version": "sintética-no-ejecutada", "declared_run_id": "fixture-001",
    "indicators_description": "Desconocidos; motor no ejecutado"}
RAW = b' [ {"url": "https://example.invalid/", "timestamp": "ambiguo"} ]\r\n'


def setup_case(client, headers, code="MOBILE-SYNTHETIC"):
    response = client.post("/api/cases", json={"case_code": code, "title": "Fixture móvil"}, headers=headers)
    assert response.status_code == 200, response.text
    case_id = response.json()["id"]
    root = f"/api/mobile-forensics/cases/{case_id}"
    response = client.post(root + "/devices", json={"label": "Fixture", "platform": "ios"}, headers=headers)
    assert response.status_code == 200, response.text
    return root, response.json()["id"]


def import_file(client, headers, root, device_id, raw=RAW, filename="safari_history_detected.json", metadata=None):
    return client.post(f"{root}/devices/{device_id}/imports", headers=headers, json={
        "metadata": metadata or META, "filename": filename, "content_base64": base64.b64encode(raw).decode()})


def review_payload(**changes):
    return {"conclusion": "actividad_sospechosa", "record_indexes": [0],
        "rationale": "Coincidencia sintética pendiente de corroboración", "alternatives": "Fixture sin dispositivo real",
        "limitations": "No hay adquisición real ni motor ejecutado", "current_activity": "No determinable con estos datos",
        "chronology": "Fecha original ambigua, sin normalizar", "attribution": "No existe sustento para atribución", **changes}


def test_preservation_review_and_export_snapshots(client, admin_headers):
    root, device = setup_case(client, admin_headers)
    response = import_file(client, admin_headers, root, device)
    assert response.status_code == 200, response.text
    exam = response.json()
    path = f'{root}/exams/{exam["id"]}'
    assert exam["sha256"] == hashlib.sha256(RAW).hexdigest()
    assert exam["coverage"] == "parcial_no_verificada" and exam["candidate_count"] == 1
    assert client.get(path + "/original", headers=admin_headers).content == RAW
    assert import_file(client, admin_headers, root, device).status_code == 409
    assert client.post(path + "/reviews", json=review_payload(record_indexes=[1]), headers=admin_headers).status_code == 422
    first = client.post(path + "/reviews", json=review_payload(), headers=admin_headers)
    assert first.status_code == 200, first.text
    export = client.post(path + "/exports", headers=admin_headers).json()
    url = path + f'/exports/{export["id"]}'
    snapshot = client.get(url, headers=admin_headers)
    assert hashlib.sha256(snapshot.content).hexdigest() == export["sha256"]
    assert snapshot.json()["review_id"] == first.json()["id"]
    assert snapshot.json()["report_id"] == export["id"]
    assert client.post(path + "/reviews", json=review_payload(conclusion="inconcluso"), headers=admin_headers).status_code == 200
    detail = client.get(path, headers=admin_headers).json()
    assert len(detail["reviews"]) == 2 and detail["records"][0]["pointer"] == "/0"
    assert client.get(url, headers=admin_headers).content == snapshot.content
    assert client.get(path + "?offset=-1", headers=admin_headers).status_code == 422
    assert client.get(path + "/original").status_code == 401


@pytest.mark.parametrize("raw,filename", [
    (b'{}', "sms.json"), (b'[{}]', "sms.json"), (b'[1]', "sms.json"),
    (b'[{"url":"x"}]', "unknown.json"), (RAW, "../safari_history.json"),
    (RAW, "C:\\safari_history.json"), (b'not json', "sms.json"),
    (b'[{"url":"x","url":"y"}]', "safari_history.json"),
    (b'[{"url":"x","number":NaN}]', "safari_history.json"),
    (b'[{"url":"x","number":1e999}]', "safari_history.json"),
    (b'[{"url":"\\ud800"}]', "safari_history.json"),
    (b'[' * 33 + b']' * 33, "sms.json"),
])
def test_hostile_or_incompatible_formats(raw, filename):
    with pytest.raises(HTTPException) as exc:
        parse_result(raw, filename, "ios")
    assert exc.value.status_code == 422


def test_empty_results_consent_limits_and_corruption(client, admin_headers, monkeypatch):
    root, device = setup_case(client, admin_headers)
    empty = import_file(client, admin_headers, root, device, b'[]', "sms.json")
    assert empty.status_code == 200
    assert empty.json()["coverage"] == "sin_datos_analizables"
    path = f'{root}/exams/{empty.json()["id"]}'
    assert client.post(path + "/reviews", headers=admin_headers,
        json=review_payload(conclusion="sin_indicios_en_el_alcance_examinado", record_indexes=[])).status_code == 422
    assert import_file(client, admin_headers, root, device, metadata={**META, "data_owner_consent": False}).status_code == 422
    from operia.core.config import settings
    monkeypatch.setattr(settings, "mobile_import_max_bytes", 8)
    assert import_file(client, admin_headers, root, device).status_code == 413
    monkeypatch.setattr(settings, "mobile_import_max_bytes", 5 * 1024 * 1024)
    assert client.post(f"{root}/devices/{device}/imports", headers=admin_headers, content=b'x' * (7 * 1024 * 1024)).status_code == 413
    generator = app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        item = db.get(MobileExam, empty.json()["id"])
        item.original_bytes = b'[{}]'
        db.commit()
    finally:
        generator.close()
    for suffix in ("", "/original"):
        assert client.get(path + suffix, headers=admin_headers).status_code == 409
    assert client.post(path + "/exports", headers=admin_headers).status_code == 409
    assert client.post(path + "/reviews", json=review_payload(), headers=admin_headers).status_code == 409


def test_scope_and_permissions_are_strict(client, admin_headers):
    root, device = setup_case(client, admin_headers)
    exam = import_file(client, admin_headers, root, device).json()
    path = f'{root}/exams/{exam["id"]}'
    other_root, other_device = setup_case(client, admin_headers, "MOBILE-OTHER")
    assert client.get(other_root + f'/exams/{exam["id"]}', headers=admin_headers).status_code == 404
    assert import_file(client, admin_headers, other_root, device).status_code == 404
    assert client.get(root + "/devices").status_code == 401
    for org in (None, 99999):
        app.dependency_overrides[get_optional_user] = lambda org=org: CurrentUser(1, org, "Otro", None, "admin")
        for suffix in ("/devices", "/exams", f'/exams/{exam["id"]}', f'/exams/{exam["id"]}/original'):
            assert client.get(root + suffix).status_code == 404
        assert import_file(client, {}, root, device).status_code == 404
        assert client.post(path + "/reviews", json=review_payload()).status_code == 404
        assert client.post(path + "/exports").status_code == 404
    app.dependency_overrides[get_optional_user] = lambda: CurrentUser(1, 1, "Lector", None, "lector")
    assert client.post(root + "/devices", json={"label": "x", "platform": "ios"}).status_code == 403
    assert client.post(path + "/reviews", json=review_payload()).status_code == 403
    app.dependency_overrides.pop(get_optional_user)


def test_engine_does_not_claim_validation(client, admin_headers):
    state = client.get("/api/mobile-forensics/engine", headers=admin_headers).json()
    assert state["validated"] is False and state["execution_enabled"] is False


def test_backup_tool_refuses_overwrite_and_detects_tampering(tmp_path):
    from scripts.sqlite_backup import copy_database, verify
    source, backup, restored = [tmp_path / name for name in ("source.db", "backup.db", "restored.db")]
    with sqlite3.connect(source) as db:
        db.execute("CREATE TABLE original (bytes BLOB)")
        db.execute("INSERT INTO original VALUES (?)", (RAW,))
    copy_database(source, backup)
    verify(backup)
    copy_database(backup, restored)
    with sqlite3.connect(restored) as db:
        assert db.execute("SELECT bytes FROM original").fetchone()[0] == RAW
    with pytest.raises(ValueError):
        copy_database(source, backup)
    with backup.open("ab") as stream:
        stream.write(b"altered")
    with pytest.raises(ValueError, match="hash"):
        verify(backup)


def test_additive_migration_backup_restore(tmp_path):
    """Synthetic previous SQLite database, upgrade twice, then backup restoration."""
    path = tmp_path / "previous.db"
    engine = create_engine(f"sqlite:///{path}")
    mobile_tables = {"mobile_devices", "mobile_exams", "mobile_reviews", "mobile_exports"}
    old_tables = [table for table in Base.metadata.sorted_tables if table.name not in mobile_tables]
    Base.metadata.create_all(engine, tables=old_tables)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO cases (id,case_code,title,description,responsible,client_or_victim,incident_type,status,jurisdiction,general_observations,created_at,updated_at) VALUES (1,'OLD','Anterior','','','','','abierto','','',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        connection.execute(text("INSERT INTO evidence (id,case_id,description,evidence_type,source,responsible,custodian,sha256_hash,preservation_method,tool_used,evidence_nature,was_altered,alteration_justification,custody_observations,integrity_status,confidence_level,acquired_at,created_at,updated_at) VALUES (1,1,'Original previo','','','','','abc','','','',0,'','','','',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
    engine.dispose()
    backup = tmp_path / "backup.db"
    with sqlite3.connect(path) as source, sqlite3.connect(backup) as destination:
        source.backup(destination)
    module = importlib.import_module("migrations.versions.20261016_0002_mobile_pilot")
    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            module.upgrade()
            module.upgrade()
            module.downgrade()  # Retention-preserving code rollback.
        assert connection.execute(text("SELECT description,sha256_hash FROM evidence WHERE id=1")).one() == ("Original previo", "abc")
        assert connection.execute(text("SELECT title FROM cases WHERE id=1")).scalar() == "Anterior"
        assert connection.execute(text("SELECT count(*) FROM mobile_exams")).scalar() == 0
    restored = tmp_path / "restored.db"
    with sqlite3.connect(backup) as source, sqlite3.connect(restored) as destination:
        source.backup(destination)
        assert destination.execute("SELECT description,sha256_hash FROM evidence WHERE id=1").fetchone() == ("Original previo", "abc")
        assert destination.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    engine.dispose()
