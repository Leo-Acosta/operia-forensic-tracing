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


# Historical external rows are seeded as prior persisted data, never imported as native truth.
RAW = b' [ {"url": "https://example.invalid/", "timestamp": "ambiguo"} ]\r\n'


def historical(client, headers):
    from operia.cases.models import Case
    from operia.identity.models import User
    from operia.mobile_forensics.models import MobileExport, MobileReview
    case = client.post("/api/cases", json={"case_code": "LEGACY-ONLY", "title": "Histórico externo"}, headers=headers).json()
    root = f'/api/mobile-forensics/cases/{case["id"]}'
    device = client.post(root + "/devices", json={"label": "Histórico", "platform": "ios"}, headers=headers).json()
    generator = app.dependency_overrides[get_db](); db = next(generator)
    try:
        case_row = db.get(Case, case["id"])
        user = db.query(User).filter_by(organization_id=case_row.organization_id).first()
        exam = MobileExam(organization_id=case_row.organization_id, case_id=case_row.id, device_id=device["id"], operator_id=user.id,
            authorization="Autorización sintética histórica", data_owner_consent=True, scope="Solo fixture histórico",
            provenance="Fixture original del piloto externo", acquisition_method="fixture", acquisition_date="desconocida",
            retention_policy="Conservar para regresión", declared_mvt_version="sintética-no-ejecutada", declared_run_id="legacy-fixture",
            indicators_description="desconocidos", filename="safari_history_detected.json", sha256=hashlib.sha256(RAW).hexdigest(),
            original_bytes=RAW, record_count=1, candidate_count=1, coverage="parcial_no_verificada", limitations="Sin adquisición real")
        db.add(exam); db.flush()
        snapshot = b'{"schema":"operia-mobile-pilot/1","source":"external historical fixture"}\n'
        export = MobileExport(exam_id=exam.id, created_by=user.id, content=snapshot, sha256=hashlib.sha256(snapshot).hexdigest())
        db.add(export); db.commit()
        return root, device["id"], exam.id, export.id, snapshot
    finally:
        generator.close()


def test_historical_original_and_snapshot_are_not_reclassified(client, admin_headers):
    root, device, exam, export, snapshot = historical(client, admin_headers)
    path = f"{root}/exams/{exam}"
    response = client.get(path, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["exam"]["origin"] == "external_historical"
    assert response.json()["exam"]["native_engine_result"] is False
    assert response.json()["exam"]["declared_mvt_version"] == "sintética-no-ejecutada"
    assert client.get(path + "/original", headers=admin_headers).content == RAW
    assert client.get(path + f"/exports/{export}", headers=admin_headers).content == snapshot
    assert client.post(f"{root}/devices/{device}/imports", headers=admin_headers, json={}).status_code == 410
    for suffix in ("/reviews", "/exports"):
        assert client.post(path + suffix, headers=admin_headers, json={}).status_code == 410
    assert client.get(path + "/original").status_code == 401


def test_historical_isolation_and_integrity(client, admin_headers):
    root, device, exam, export, snapshot = historical(client, admin_headers)
    path = f"{root}/exams/{exam}"
    app.dependency_overrides[get_optional_user] = lambda: CurrentUser(1, 99999, "Otra organización", None, "admin")
    assert client.get(path).status_code == 404
    app.dependency_overrides.pop(get_optional_user)
    generator = app.dependency_overrides[get_db](); db = next(generator)
    try:
        db.get(MobileExam, exam).original_bytes = b'[]'
        db.commit()
    finally:
        generator.close()
    assert client.get(path, headers=admin_headers).status_code == 409
    assert client.get(path + "/original", headers=admin_headers).status_code == 409


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
    old_tables = [table for table in Base.metadata.sorted_tables if table.name not in mobile_tables and not table.name.startswith("native_mobile_")]
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
