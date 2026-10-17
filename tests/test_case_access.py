import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from operia.identity.case_access import CaseAccessEvent, CAPABILITIES
from operia.identity.models import User
from operia.audit.models import AuditLog
from operia.forensic_jobs import worker
from operia.forensic_jobs.models import ExaminationJob
from test_native_mobile_workflow import database_factory, setup, enqueue
from test_security_audit import second_tenant


def analyst(client, admin, role="analista", suffix="one"):
    response = client.post("/api/identity/users", headers=admin, json={"name": "Synthetic operator", "email": suffix + "@acl.test", "password": "SyntheticPassword123!", "role": role})
    assert response.status_code == 200, response.text
    uid = response.json()["id"]
    login = client.post("/api/identity/login", json={"email": suffix + "@acl.test", "password": "SyntheticPassword123!"})
    assert login.status_code == 200
    return uid, {"Authorization": "Bearer " + login.json()["access_token"]}


def grant(client, admin, case, uid, access="read", permissions=None):
    payload = {"user_id": uid, "access": access, "reason": "Synthetic authorization decision"}
    if permissions is not None:
        payload["permissions"] = permissions
    return client.post(f"/api/cases/{case}/access", headers=admin, json=payload)


def new_case(client, admin, code="ACL"):
    response = client.post("/api/cases", headers=admin, json={"case_code": code, "title": "Synthetic private case"})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_bootstrap_modules_share_only_the_synthetic_database(client):
    from importlib import import_module
    with database_factory()() as db:
        engine = db.bind
    for name in ("core", "cybercrime", "geo_trace", "geo_proximity", "rubrics"):
        assert import_module(f"operia.{name}.bootstrap").engine is engine
    with import_module("operia.geo_proximity.bootstrap").SessionLocal() as db:
        assert db.bind is engine


def test_inactive_users_can_be_revoked_before_reactivation(client, admin_headers):
    uid, headers = analyst(client, admin_headers)
    case = new_case(client, admin_headers)
    assert grant(client, admin_headers, case, uid).status_code == 200
    assert client.put(f"/api/identity/users/{uid}", headers=admin_headers, json={"status": "inactive"}).status_code == 200
    assert grant(client, admin_headers, case, uid).status_code == 404
    assert grant(client, admin_headers, case, uid, "revoked").status_code == 200
    assert client.put(f"/api/identity/users/{uid}", headers=admin_headers, json={"status": "active"}).status_code == 200
    login = client.post("/api/identity/login", json={"email": "one@acl.test", "password": "SyntheticPassword123!"})
    assert login.status_code == 200
    current = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert client.get(f"/api/cases/{case}", headers=current).status_code == 404


def test_default_deny_lists_counts_relationships_and_revocation(client, admin_headers):
    uid, headers = analyst(client, admin_headers)
    first, second = new_case(client, admin_headers), new_case(client, admin_headers, "OTHER")
    evidence = client.post("/api/evidence", headers=admin_headers, json={"case_id": first, "description": "Private evidence"}).json()
    assert client.get("/api/cases", headers=headers).json() == []
    assert client.get("/api/dashboard/", headers=headers).json()["metrics"]["cases"] == 0
    for path in (f"/api/cases/{first}", f"/api/evidence/{evidence['id']}", f"/api/mobile-forensics/cases/{first}/devices", f"/api/mind/cases/{first}/graph"):
        assert client.get(path, headers=headers).status_code == 404
    assert grant(client, admin_headers, first, uid).status_code == 200
    assert [row["id"] for row in client.get("/api/cases", headers=headers).json()] == [first]
    assert client.get("/api/dashboard/", headers=headers).json()["metrics"]["cases"] == 1
    assert client.get(f"/api/evidence/{evidence['id']}", headers=headers).status_code == 200
    assert client.get(f"/api/cases/{second}", headers=headers).status_code == 404
    assert client.post("/api/evidence", headers=headers, json={"case_id": first, "description": "Denied write"}).status_code == 404
    assert grant(client, admin_headers, first, uid, "revoked").status_code == 200
    assert client.get("/api/cases", headers=headers).json() == []
    assert client.get(f"/api/evidence/{evidence['id']}", headers=headers).status_code == 404
    assert client.get("/api/dashboard/", headers=headers).json()["metrics"]["evidence"] == 0
    with database_factory()() as db:
        assert db.query(AuditLog).filter(AuditLog.action.in_(["grant_case_access", "revoke_case_access"])).count() == 2
        assert db.query(CaseAccessEvent).filter_by(user_id=uid).count() == 10


def test_capabilities_and_role_intersection(client, admin_headers):
    uid, headers = analyst(client, admin_headers)
    case = new_case(client, admin_headers)
    assert grant(client, admin_headers, case, uid, permissions=["evidence"]).status_code == 200
    assert client.post("/api/evidence", headers=headers, json={"case_id": case, "description": "Allowed"}).status_code == 200
    assert client.post(f"/api/reports/case/{case}/generate", headers=headers).status_code == 404
    assert grant(client, admin_headers, case, uid, permissions=["reports"]).status_code == 200
    report = client.post(f"/api/reports/case/{case}/generate", headers=headers)
    assert report.status_code == 200, report.text
    rid = report.json()["id"]
    assert client.get(f"/api/reports/{rid}/export/json", headers=headers).status_code == 404
    assert client.put(f"/api/reports/{rid}", headers=headers, json={"status": "final"}).status_code == 404
    assert grant(client, admin_headers, case, uid, "revoked", ["evidence"]).status_code == 200
    assert client.get(f"/api/cases/{case}", headers=headers).status_code == 200
    assert client.post("/api/evidence", headers=headers, json={"case_id": case, "description": "Denied"}).status_code == 404
    reader, reader_headers = analyst(client, admin_headers, "lector", "reader")
    assert grant(client, admin_headers, case, reader, "write").status_code == 200
    assert client.post("/api/evidence", headers=reader_headers, json={"case_id": case, "description": "RBAC denied"}).status_code == 403
    assert client.get(f"/api/cases/{case}/access/me", headers=reader_headers).status_code == 200


def test_admin_scope_no_self_grant_and_immutable_audit(client, admin_headers):
    case = new_case(client, admin_headers)
    uid, headers = analyst(client, admin_headers)
    org, foreign_uid, foreign = second_tenant(client)
    assert grant(client, admin_headers, case, foreign_uid).status_code == 404
    assert grant(client, foreign, case, uid).status_code == 404
    assert grant(client, headers, case, uid, "write").status_code == 403
    assert grant(client, admin_headers, case, uid, permissions=["unknown"]).status_code == 422
    assert grant(client, admin_headers, case, uid, permissions=[]).status_code == 422
    assert grant(client, admin_headers, case, uid).status_code == 200
    before = client.get(f"/api/cases/{case}/access", headers=admin_headers).json()
    assert before and before[-1]["actor_id"] == 1
    with database_factory()() as db:
        row = db.query(CaseAccessEvent).filter_by(user_id=uid).first()
        row.reason = "Tampered"
        with pytest.raises(HTTPException):
            db.commit()
        db.rollback()
        for statement in ("UPDATE case_access_events SET reason='Tampered'", "DELETE FROM case_access_events"):
            with pytest.raises(IntegrityError):
                db.execute(text(statement)); db.commit()
            db.rollback()
    assert client.get(f"/api/cases/{case}/access", headers=admin_headers).json() == before


def test_creator_has_explicit_access_without_opening_other_cases(client, admin_headers):
    uid, headers = analyst(client, admin_headers)
    other = new_case(client, admin_headers)
    own = new_case(client, headers, "CREATOR")
    assert client.get(f"/api/cases/{own}", headers=headers).status_code == 200
    assert client.get(f"/api/cases/{other}", headers=headers).status_code == 404
    with database_factory()() as db:
        assert db.query(CaseAccessEvent).filter_by(user_id=uid, case_id=own).count() == len(CAPABILITIES)


@pytest.mark.parametrize("when", ["pending", "running", "publication"])
def test_worker_revocation_before_during_and_before_publication(client, admin_headers, monkeypatch, when):
    root, acquisition, raw = setup(client, admin_headers)
    case = acquisition["case_id"]
    uid, headers = analyst(client, admin_headers)
    assert grant(client, admin_headers, case, uid, permissions=["analysis"]).status_code == 200
    job = enqueue(client, headers, root, acquisition)
    spawned = []
    original = worker.spawn_worker
    def spawn(*args, **kwargs):
        process = original(*args, **kwargs)
        spawned.append(process)
        if when == "running":
            assert grant(client, admin_headers, case, uid, "revoked", ["analysis"]).status_code == 200
        return process
    if when == "pending":
        assert grant(client, admin_headers, case, uid, "revoked", ["analysis"]).status_code == 200
        monkeypatch.setattr(worker, "spawn_worker", lambda *a, **k: pytest.fail("Denied job must not spawn"))
    else:
        monkeypatch.setattr(worker, "spawn_worker", spawn)
        if when == "publication":
            original_begin = worker.begin_write
            def before_publication(db):
                assert grant(client, admin_headers, case, uid, "revoked", ["analysis"]).status_code == 200
                original_begin(db)
            monkeypatch.setattr(worker, "begin_write", before_publication)
    assert worker.run_once(database_factory(), timeout=15)
    with database_factory()() as db:
        current = db.get(ExaminationJob, job["id"])
        assert current.state == "fallido"
        assert current.error_code in {"scope_or_operator_invalid", "scope_or_operator_changed"}
        assert current.result_bytes is None and not current.result_sha256
    assert all(process.poll() is not None for process in spawned)


@pytest.mark.parametrize("alias", ["cases", "legal-report/cases"])
def test_creation_aliases_grant_creator(client, admin_headers, alias):
    uid, headers = analyst(client, admin_headers)
    response = client.post("/api/" + alias, headers=headers, json={"case_code": "CREATOR-ALIAS", "title": "Synthetic"})
    assert response.status_code == 200, response.text
    case = response.json()["id"]
    assert client.get(f"/api/cases/{case}", headers=headers).status_code == 200
    assert len(client.get(f"/api/cases/{case}/access/me", headers=headers).json()["capabilities"]) == len(CAPABILITIES)


def test_exports_files_and_manifests_revalidate(client, admin_headers):
    uid, headers = analyst(client, admin_headers)
    case = new_case(client, admin_headers)
    report = client.post(f"/api/reports/case/{case}/generate", headers=admin_headers).json()
    exported = client.post("/api/exports/json", headers=admin_headers, json={"case_id": case, "content": {"synthetic": True}})
    assert exported.status_code == 200, exported.text
    manifest = exported.headers["X-OPERIA-Export-Manifest-Id"]
    assert grant(client, admin_headers, case, uid).status_code == 200
    assert client.get(f"/api/exports/manifests/{manifest}", headers=headers).status_code == 200
    for path in (f"/api/exports/manifests/{manifest}/download", f"/api/reports/{report['id']}/export/markdown", f"/api/exports/reports/{report['id']}/pdf"):
        assert client.get(path, headers=headers).status_code == 404
    assert grant(client, admin_headers, case, uid, permissions=["export"]).status_code == 200
    original = client.get(f"/api/exports/manifests/{manifest}/download", headers=headers)
    assert original.status_code == 200
    assert client.get(f"/api/reports/{report['id']}/export/markdown", headers=headers).status_code == 200
    assert grant(client, admin_headers, case, uid, "revoked").status_code == 200
    assert client.get(f"/api/exports/manifests/{manifest}/download", headers=headers).status_code == 404
    assert client.get(f"/api/exports/manifests/{manifest}/download", headers=admin_headers).content == original.content


def test_participants_need_dedicated_capability(client, admin_headers):
    uid, headers = analyst(client, admin_headers)
    case = new_case(client, admin_headers)
    assert grant(client, admin_headers, case, uid, permissions=["evidence"]).status_code == 200
    path = f"/api/cases/{case}/participants"
    assert client.post(path, headers=headers, json={"display_name": "Synthetic participant"}).status_code == 404
    assert grant(client, admin_headers, case, uid, permissions=["participants"]).status_code == 200
    assert client.post(path, headers=headers, json={"display_name": "Synthetic participant"}).status_code == 200


def test_migration_idempotent_preserves_history(client, admin_headers):
    import importlib
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    case = new_case(client, admin_headers)
    with database_factory()() as db:
        rows = db.execute(text("SELECT * FROM case_access_events ORDER BY id")).all()
        engine = db.bind
    migration = importlib.import_module("migrations.versions.20261017_0007_case_access")
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade(); migration.upgrade(); migration.downgrade()
        assert connection.execute(text("SELECT * FROM case_access_events ORDER BY id")).all() == rows
        assert connection.execute(text("PRAGMA integrity_check")).scalar() == "ok"


def test_worker_completed_history_survives_revocation(client, admin_headers):
    root, acquisition, raw = setup(client, admin_headers)
    case = acquisition["case_id"]
    uid, headers = analyst(client, admin_headers)
    assert grant(client, admin_headers, case, uid, permissions=["analysis"]).status_code == 200
    job = enqueue(client, headers, root, acquisition)
    assert worker.run_once(database_factory(), timeout=15)
    with database_factory()() as db:
        row = db.get(ExaminationJob, job["id"])
        before = (row.state, row.result_bytes, row.result_sha256, row.finished_at)
        assert row.result_bytes
    assert grant(client, admin_headers, case, uid, "revoked").status_code == 200
    with database_factory()() as db:
        row = db.get(ExaminationJob, job["id"])
        assert (row.state, row.result_bytes, row.result_sha256, row.finished_at) == before
    assert client.get(root + f"/jobs/{job['id']}", headers=headers).status_code == 404
    assert client.get(root + f"/jobs/{job['id']}", headers=admin_headers).status_code == 200


def test_bulk_writes_and_cached_objects_cannot_bypass_revocation(client, admin_headers):
    from operia.identity.dependencies import CurrentUser
    from operia.evidence.models import Evidence
    uid, headers = analyst(client, admin_headers)
    case = new_case(client, admin_headers)
    evidence = client.post("/api/evidence", headers=admin_headers, json={"case_id": case, "description": "Preserved"}).json()
    assert grant(client, admin_headers, case, uid).status_code == 200
    with database_factory()() as db:
        user = db.get(User, uid)
        actor = CurrentUser(uid, user.organization_id, user.name, user.email, user.role)
        db.info.update(request_organization=user.organization_id, request_actor=actor, case_capability="evidence", case_writing=True)
        assert db.query(Evidence).filter_by(id=evidence["id"]).update({"description": "Denied bulk write"}, synchronize_session=False) == 0
        db.commit()
    assert grant(client, admin_headers, case, uid, permissions=["evidence"]).status_code == 200
    with database_factory()() as db:
        item = db.get(Evidence, evidence["id"])
        assert grant(client, admin_headers, case, uid, "revoked").status_code == 200
        db.info.update(request_organization=actor.organization_id, request_actor=actor, case_capability="evidence", case_writing=True)
        item.description = "Denied cached write"
        with pytest.raises(HTTPException):
            db.commit()
        db.rollback()
    assert client.get(f"/api/evidence/{evidence['id']}", headers=admin_headers).json()["description"] == "Preserved"
