def create_case(client, headers, code="MIND-001"):
    response = client.post(
        "/api/cases",
        headers=headers,
        json={
            "case_code": code,
            "title": "Caso Mind",
            "description": "Prueba de memoria persistente.",
            "incident_type": "phishing / fraude digital",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_mind_status_and_catalogs(client, admin_headers):
    status = client.get("/api/mind", headers=admin_headers)
    assert status.status_code == 200
    assert status.json()["status"] == "active"

    prompts = client.get("/api/mind/prompts", headers=admin_headers)
    assert prompts.status_code == 200
    assert len(prompts.json()) >= 5

    agents = client.get("/api/mind/agents", headers=admin_headers)
    assert agents.status_code == 200
    assert len(agents.json()) >= 5


def test_mind_note_snapshot_and_graph(client, admin_headers):
    case = create_case(client, admin_headers, "MIND-002")

    note = client.post(
        "/api/mind/notes",
        headers=admin_headers,
        json={
            "case_id": case["id"],
            "note_type": "nota",
            "title": "Nota de prueba",
            "content": "Contenido controlado de prueba.",
            "tags": ["mind", "test"],
        },
    )
    assert note.status_code == 200
    assert note.json()["vault_path"].endswith(".md")

    snapshot = client.post(f"/api/mind/cases/{case['id']}/snapshot", headers=admin_headers)
    assert snapshot.status_code == 200
    assert snapshot.json()["graph_nodes"] >= 2
    assert snapshot.json()["graph_edges"] >= 1

    notes = client.get(f"/api/mind/cases/{case['id']}/notes", headers=admin_headers)
    assert notes.status_code == 200
    assert len(notes.json()) >= 2

    graph = client.get(f"/api/mind/cases/{case['id']}/graph", headers=admin_headers)
    assert graph.status_code == 200
    assert len(graph.json()["nodes"]) >= 2
    assert len(graph.json()["edges"]) >= 1

    search = client.get(f"/api/mind/search?q=controlado&case_id={case['id']}", headers=admin_headers)
    assert search.status_code == 200
    assert search.json()[0]["title"] == "Nota de prueba"
    assert search.json()[0]["score"] > 0

    audit = client.get(f"/api/mind/audit?case_id={case['id']}", headers=admin_headers)
    assert audit.status_code == 200
    actions = {item["action"] for item in audit.json()}
    assert "create_note" in actions
    assert "case_snapshot" in actions

    brief = client.get(f"/api/mind/cases/{case['id']}/brief", headers=admin_headers)
    assert brief.status_code == 200
    payload = brief.json()
    assert payload["case_code"] == "MIND-002"
    assert payload["graph_summary"]["notes"] >= 1
    assert any("Evidencia" in item or "evidencia" in item for item in payload["missing_information"])


def test_mind_report_snapshot_is_searchable(client, admin_headers):
    case = create_case(client, admin_headers, "MIND-003")
    report = client.post(f"/api/reports/case/{case['id']}/generate?author=Analista%20Mind", headers=admin_headers)
    assert report.status_code == 200
    report_id = report.json()["id"]

    snapshot = client.post(f"/api/mind/reports/{report_id}/snapshot", headers=admin_headers)
    assert snapshot.status_code == 200
    assert snapshot.json()["case_id"] == case["id"]
    assert snapshot.json()["vault_path"].endswith(".md")

    search = client.get(f"/api/mind/search?q=informe&case_id={case['id']}", headers=admin_headers)
    assert search.status_code == 200
    assert any(item["note_type"] == "informe" for item in search.json())

    graph = client.get(f"/api/mind/cases/{case['id']}/graph", headers=admin_headers)
    assert graph.status_code == 200
    edge_types = {item["relation_type"] for item in graph.json()["edges"]}
    assert "tiene_informe" in edge_types
    assert "guardado_en_memoria" in edge_types


def test_mind_presentation_snapshot_links_case_report_and_note(client, admin_headers):
    case = create_case(client, admin_headers, "MIND-004")
    report = client.post(f"/api/reports/case/{case['id']}/generate?author=Analista%20Mind", headers=admin_headers)
    assert report.status_code == 200
    report_id = report.json()["id"]

    presentation = client.post(
        f"/api/reports/{report_id}/presentations/generate?presentation_type=Exposicion%20ejecutiva",
        headers=admin_headers,
    )
    assert presentation.status_code == 200
    presentation_id = presentation.json()["id"]

    snapshot = client.post(f"/api/mind/presentations/{presentation_id}/snapshot", headers=admin_headers)
    assert snapshot.status_code == 200
    assert snapshot.json()["case_id"] == case["id"]
    assert snapshot.json()["vault_path"].endswith(".md")

    search = client.get(f"/api/mind/search?q=exposicion&case_id={case['id']}", headers=admin_headers)
    assert search.status_code == 200
    assert any(item["note_type"] == "exposicion" for item in search.json())

    graph = client.get(f"/api/mind/cases/{case['id']}/graph", headers=admin_headers)
    assert graph.status_code == 200
    edge_types = {item["relation_type"] for item in graph.json()["edges"]}
    assert "tiene_exposicion" in edge_types
    assert "deriva_en_exposicion" in edge_types
    assert "guardado_en_memoria" in edge_types
