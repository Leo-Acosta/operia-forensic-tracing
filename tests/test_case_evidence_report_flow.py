def test_case_evidence_report_flow_with_audit(client, admin_headers):
    case = client.post(
        "/api/cases",
        json={
            "case_code": "TEST-CASE-001",
            "title": "Caso de prueba",
            "description": "phishing con acceso no autorizado",
            "incident_type": "phishing",
        },
        headers=admin_headers,
    )
    assert case.status_code == 200
    case_id = case.json()["id"]
    assert case.json()["case_code"] == "TEST-CASE-001"

    evidence = client.post(
        "/api/evidence",
        json={
            "case_id": case_id,
            "evidence_type": "log",
            "description": "Log de acceso",
            "sha256_hash": "abc123",
        },
        headers=admin_headers,
    )
    assert evidence.status_code == 200
    assert evidence.json()["case_id"] == case_id

    report = client.post(f"/api/reports/case/{case_id}/generate?author=pytest", headers=admin_headers)
    assert report.status_code == 200
    report_id = report.json()["id"]

    reports = client.get(f"/api/reports/case/{case_id}", headers=admin_headers)
    assert reports.status_code == 200
    assert any(item["id"] == report_id for item in reports.json())

    logs = client.get(f"/api/audit/logs?case_id={case_id}", headers=admin_headers)
    assert logs.status_code == 200
    actions = {item["action"] for item in logs.json()}
    assert {"create_case", "create_evidence", "generate_report"}.issubset(actions)
