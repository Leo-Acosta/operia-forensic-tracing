import hashlib
import importlib
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, insert, text
from sqlalchemy.exc import IntegrityError
from alembic.migration import MigrationContext
from alembic.operations import Operations

from operia.evidence.models import ChainOfCustodyAction, CustodyLedgerEntry
from operia.evidence.schemas import CustodyRectification
from operia.evidence.custody import rectify
from operia.identity.dependencies import CurrentUser, get_optional_user
from test_native_mobile_workflow import database_factory
from test_security_audit import second_tenant


def setup_case(client, headers, code="LEDGER"):
    case = client.post("/api/cases", headers=headers, json={"case_code": code, "title": "Synthetic custody"}).json()["id"]
    evidence = client.post("/api/evidence", headers=headers, json={"case_id": case, "description": "Synthetic original"}).json()["id"]
    response = client.post("/api/evidence/custody-actions", headers=headers, json={"case_id": case,
        "evidence_id": evidence, "detailed_description": "Original fact", "user_responsible": "Spoofed actor", "user_role": "spoofed"})
    assert response.status_code == 200, response.text
    return case, evidence, response.json()


def correct(client, headers, action, **overrides):
    return client.post(f"/api/evidence/custody-actions/{action}/rectifications", headers=headers,
        json={"reason": "Documented synthetic correction", "changes": {"detailed_description": "Corrected fact"}, **overrides})


def test_versions_identity_history_and_published_records(client, admin_headers):
    from operia.reports.models import Report, ReportVersion
    from operia.exports.models import ExportManifest
    from pathlib import Path
    case, evidence, original = setup_case(client, admin_headers)
    assert original["user_responsible"] == "Test Admin"
    assert original["ledger_entry"]["actor_user_id"] == 1
    assert original["ledger_entry"]["version"] == 0
    report = client.post(f"/api/reports/case/{case}/generate?author=Synthetic", headers=admin_headers).json()
    assert client.get(f"/api/exports/reports/{report['id']}/pdf", headers=admin_headers).status_code == 200
    from operia.core.config import settings
    bitacora = client.get(f"/api/legal-report/cases/{case}/custody-actions/export", headers=admin_headers)
    assert bitacora.status_code == 200
    first_bitacora = next(settings.exports_dir.glob("*bitacora*"))
    first_bitacora_bytes = first_bitacora.read_bytes()
    def snapshot():
        with database_factory()() as db:
            rows = {model.__tablename__: [[getattr(row, col.name) for col in model.__table__.columns]
                for row in db.query(model).order_by(model.id).all()] for model in (Report, ReportVersion, ExportManifest)}
            files = {row.file_path: hashlib.sha256(Path(row.file_path).read_bytes()).hexdigest() for row in db.query(ExportManifest)}
        return rows, files
    before = snapshot()
    first = correct(client, admin_headers, original["id"], occurred_at="2026-01-02T10:00:00-03:00")
    assert first.status_code == 200, first.text
    first = first.json()
    second = correct(client, admin_headers, first["id"]).json()
    assert first["ledger_entry"]["version"] == 1 and second["ledger_entry"]["version"] == 2
    assert second["ledger_entry"]["previous_action_id"] == first["id"]
    assert first["ledger_entry"]["occurred_at"] is not None
    assert first["ledger_entry"]["occurred_at"] == "2026-01-02T13:00:00+00:00"
    assert first["ledger_entry"]["occurred_at_original"].endswith("-03:00")
    history = client.get(f"/api/evidence/custody-actions/{second['id']}/history", headers=admin_headers)
    assert history.status_code == 200
    assert history.json() == [original, first, second]
    assert correct(client, admin_headers, original["id"]).status_code == 409
    assert snapshot() == before
    assert client.get(f"/api/reports/{report['id']}", headers=admin_headers).json()["markdown_content"] == report["markdown_content"]
    latest_bitacora = client.get(f"/api/legal-report/cases/{case}/custody-actions/export", headers=admin_headers)
    assert latest_bitacora.status_code == 200
    assert latest_bitacora.content != bitacora.content
    assert first_bitacora.read_bytes() == first_bitacora_bytes
    assert len(list(settings.exports_dir.glob("*bitacora*"))) == 2


@pytest.mark.parametrize("prefix", ["/api/evidence", "/api/legal-report"])
@pytest.mark.parametrize("method", ["put", "delete"])
def test_existing_mutation_routes_are_blocked(client, admin_headers, prefix, method):
    case, _, original = setup_case(client, admin_headers)
    kwargs = {"json": {"case_id": case, "detailed_description": "overwrite"}} if method == "put" else {}
    response = getattr(client, method)(f"{prefix}/custody-actions/{original['id']}", headers=admin_headers, **kwargs)
    assert response.status_code == 409
    history = client.get(f"/api/evidence/custody-actions/{original['id']}/history", headers=admin_headers).json()
    assert history == [original]


def test_parent_deletion_and_orm_mutation_are_blocked(client, admin_headers):
    case, evidence, original = setup_case(client, admin_headers)
    assert client.delete(f"/api/cases/{case}", headers=admin_headers).status_code == 409
    assert client.delete(f"/api/evidence/{evidence}", headers=admin_headers).status_code == 409
    with database_factory()() as db:
        db.get(ChainOfCustodyAction, original["id"]).status = "overwritten"
        with pytest.raises(HTTPException): db.commit()
        db.rollback()
        db.delete(db.get(CustodyLedgerEntry, db.query(CustodyLedgerEntry).filter_by(action_id=original["id"]).one().id))
        with pytest.raises(HTTPException): db.commit()
        db.rollback()


@pytest.mark.parametrize("table", ["chain_of_custody_actions", "custody_ledger_entries"])
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_sqlite_blocks_core_and_bulk_bypasses(client, admin_headers, table, operation):
    setup_case(client, admin_headers)
    with database_factory()() as db:
        sql = f"UPDATE {table} SET id=id" if operation == "UPDATE" else f"DELETE FROM {table}"
        with pytest.raises(IntegrityError, match="custody_append_only"):
            db.execute(text(sql))
        db.rollback()


def test_legacy_events_remain_unattributed_and_can_be_rectified(client, admin_headers):
    case, evidence, _ = setup_case(client, admin_headers)
    with database_factory()() as db:
        result = db.execute(insert(ChainOfCustodyAction).values(case_id=case, evidence_id=evidence,
            detailed_description="Legacy synthetic fact", user_responsible="Historical operator"))
        key = result.inserted_primary_key[0]; db.commit()
    before = client.get(f"/api/evidence/custody-actions/{key}/history", headers=admin_headers).json()[0]
    assert before["ledger_entry"] is None and before["user_responsible"] == "Historical operator"
    response = correct(client, admin_headers, key)
    assert response.status_code == 200
    history = client.get(f"/api/evidence/custody-actions/{key}/history", headers=admin_headers).json()
    assert history[0] == before and history[1]["ledger_entry"]["version"] == 1


def test_unauthorized_and_cross_scope_requests_add_nothing(client, admin_headers):
    from apps.api.main import app
    case, _, original = setup_case(client, admin_headers)
    _, _, other = second_tenant(client)
    assert correct(client, {}, original["id"]).status_code == 401
    assert correct(client, other, original["id"]).status_code == 404
    assert client.get(f"/api/evidence/custody-actions/{original['id']}/history", headers=other).status_code == 404
    app.dependency_overrides[get_optional_user] = lambda: CurrentUser(1, 1, "Reader", None, "lector")
    try:
        assert correct(client, {}, original["id"]).status_code == 403
    finally: app.dependency_overrides.pop(get_optional_user)
    assert len(client.get(f"/api/evidence/custody-actions/{original['id']}/history", headers=admin_headers).json()) == 1


@pytest.mark.parametrize("payload", [{"reason": " "}, {"changes": {"case_id": "2"}},
    {"changes": {"user_responsible": "spoof"}}, {"actor_user_id": 999},
    {"occurred_at": "2026-01-02T10:00:00"}])
def test_invalid_rectifications_are_rejected(client, admin_headers, payload):
    _, _, original = setup_case(client, admin_headers)
    assert correct(client, admin_headers, original["id"], **payload).status_code == 422


def test_concurrent_rectifications_have_one_winner_and_no_orphan(client, admin_headers):
    _, _, original = setup_case(client, admin_headers)
    factory = database_factory(); barrier = Barrier(2)
    def attempt():
        with factory() as db:
            db.info["request_actor"] = CurrentUser(1, 1, "Test Admin", None, "admin")
            target = db.get(ChainOfCustodyAction, original["id"])
            barrier.wait(timeout=10)
            try:
                item = rectify(db, target, CustodyRectification(reason="Concurrent correction"))
                db.commit()
                return item.id
            except HTTPException as error:
                db.rollback(); assert error.status_code == 409
                return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(lambda _: attempt(), range(2)))
    assert sum(item is not None for item in result) == 1
    history = client.get(f"/api/evidence/custody-actions/{original['id']}/history", headers=admin_headers).json()
    assert len(history) == 2 and history[-1]["ledger_entry"]["version"] == 1


def test_additive_upgrade_downgrade_preserves_legacy_rows(tmp_path):
    migration = importlib.import_module("migrations.versions.20261017_0006_custody_ledger")
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE cases(id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE evidence(id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE chain_of_custody_actions(id INTEGER PRIMARY KEY, case_id INTEGER, evidence_id INTEGER, original TEXT)"))
        connection.execute(text("INSERT INTO chain_of_custody_actions VALUES (1,1,1,'synthetic original')"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade(); migration.upgrade(); migration.downgrade()
        assert connection.execute(text("SELECT * FROM chain_of_custody_actions")).all() == [(1, 1, 1, "synthetic original")]
        assert connection.execute(text("SELECT count(*) FROM custody_ledger_entries")).scalar() == 0
        with pytest.raises(IntegrityError): connection.execute(text("DELETE FROM chain_of_custody_actions"))
    engine.dispose()


def test_migration_resolves_foreign_keys_in_clean_process():
    import subprocess
    import sys
    source = """
import importlib
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects.sqlite import dialect
m = importlib.import_module('migrations.versions.20261017_0006_custody_ledger')
str(CreateTable(m.CustodyLedgerEntry.__table__).compile(dialect=dialect()))
print('ok')
"""
    result = subprocess.run([sys.executable, "-c", source], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


@pytest.mark.parametrize("table", ["cases", "evidence"])
def test_sqlite_parent_deletion_cannot_orphan_history(client, admin_headers, table):
    case, evidence, _ = setup_case(client, admin_headers)
    key = case if table == "cases" else evidence
    with database_factory()() as db:
        with pytest.raises(IntegrityError, match="custody_parent_preserved"):
            db.execute(text(f"DELETE FROM {table} WHERE id=:key"), {"key": key})
        db.rollback()


def test_case_query_cannot_mismatch_rectification_target(client, admin_headers):
    _, _, original = setup_case(client, admin_headers)
    other, _, _ = setup_case(client, admin_headers, "OTHER-LEDGER")
    response = client.post(f"/api/evidence/custody-actions/{original['id']}/rectifications?case_id={other}",
        headers=admin_headers, json={"reason": "Cross case attempt"})
    assert response.status_code == 422
