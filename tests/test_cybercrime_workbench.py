def test_cybercrime_indicator_analyzer_classifies_email_and_hash(client, admin_headers):
    email_response = client.post(
        "/api/cybercrime/analyze-indicator",
        json={"indicator": "support.verify@example-login.com"},
        headers=admin_headers,
    )
    assert email_response.status_code == 200
    email_result = email_response.json()
    assert email_result["indicator_type"] == "email"
    assert email_result["risk_level"] == "high"
    assert email_result["confidence"] == "high"
    assert email_result["observables"]["domain"] == "example-login.com"
    assert "Preservar cabeceras completas" in " ".join(email_result["recommended_actions"])

    hash_response = client.post(
        "/api/cybercrime/analyze-indicator",
        json={"indicator": "a91f7c8e2f93cbb6a62e4d3e8e6bff91a03a40d7c9a4b39f8d91ac27aa981e22"},
        headers=admin_headers,
    )
    assert hash_response.status_code == 200
    hash_result = hash_response.json()
    assert hash_result["indicator_type"] == "hash"
    assert hash_result["observables"]["hash_type"] == "SHA-256"
    assert "no atribuye autoria" in " ".join(hash_result["findings"])


def test_cybercrime_workbench_creates_lab_session_and_proof_row(client, admin_headers):
    case_response = client.post(
        "/api/cases",
        json={
            "case_code": "CYBER-001",
            "title": "Caso cybercrime",
            "description": "phishing con indicador tecnico",
            "incident_type": "phishing",
        },
        headers=admin_headers,
    )
    assert case_response.status_code == 200
    case_id = case_response.json()["id"]

    lab_response = client.post(
        "/api/cybercrime/lab/sessions",
        json={"case_id": case_id, "title": "Analisis de indicador", "operator": "Analista QA"},
        headers=admin_headers,
    )
    assert lab_response.status_code == 200
    assert lab_response.json()["case_id"] == case_id
    assert lab_response.json()["session_code"].startswith("LAB-")

    proof_response = client.post(
        "/api/cybercrime/proof-matrix",
        json={
            "case_id": case_id,
            "defensible_conclusion": "El indicador permite orientar la investigacion, pero no atribuye autoria por si solo.",
            "legal_framing": "Requiere vinculo con evidencia y encuadre legal aprobado.",
            "confidence_level": "medio",
        },
        headers=admin_headers,
    )
    assert proof_response.status_code == 200
    assert proof_response.json()["case_id"] == case_id
    assert proof_response.json()["confidence_level"] == "medio"

    dashboard = client.get("/api/cybercrime/dashboard", headers=admin_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["lab_sessions"] >= 1
    assert dashboard.json()["proof_matrix_rows"] >= 1
