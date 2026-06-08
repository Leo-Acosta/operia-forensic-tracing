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
    agent_keys = {item["key"] for item in agents.json()}
    assert {"agente_deepfake", "agente_iot", "agente_blockchain"}.issubset(agent_keys)

    prompt_keys = {item["key"] for item in prompts.json()}
    assert {"construir_grafo", "auditar_grafo", "analisis_deepfake", "analisis_blockchain", "analisis_iot"}.issubset(prompt_keys)

    catalog = client.get("/api/mind/graph/catalog", headers=admin_headers)
    assert catalog.status_code == 200
    assert "wallet" in catalog.json()["node_types"]
    assert "sostiene" in catalog.json()["relation_types"]


def test_mind_manual_graph_relation(client, admin_headers):
    case = create_case(client, admin_headers, "MIND-GRAPH-001")

    source = client.post(
        "/api/mind/graph/nodes",
        headers=admin_headers,
        json={
            "case_id": case["id"],
            "node_type": "url",
            "label": "https://example.test/login",
            "source_module": "cybercrime",
            "source_entity_type": "indicator",
            "source_entity_id": "url-1",
        },
    )
    assert source.status_code == 200

    target = client.post(
        "/api/mind/graph/nodes",
        headers=admin_headers,
        json={
            "case_id": case["id"],
            "node_type": "finding",
            "label": "URL compatible con phishing",
            "source_module": "cybercrime",
            "source_entity_type": "finding",
            "source_entity_id": "finding-1",
        },
    )
    assert target.status_code == 200

    relation = client.post(
        "/api/mind/graph/edges",
        headers=admin_headers,
        json={
            "case_id": case["id"],
            "source_node_key": source.json()["node_key"],
            "target_node_key": target.json()["node_key"],
            "relation_type": "sostiene",
            "label": "Indicador preservado sostiene hallazgo técnico",
            "confidence": "alto",
        },
    )
    assert relation.status_code == 200
    assert relation.json()["relation_type"] == "sostiene"

    graph = client.get(f"/api/mind/graph?case_id={case['id']}", headers=admin_headers)
    assert graph.status_code == 200
    assert len(graph.json()["nodes"]) == 2
    assert len(graph.json()["edges"]) == 1


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


def test_mind_graph_is_used_by_report_without_cross_case_leakage(client, admin_headers):
    case_a = create_case(client, admin_headers)
    case_b = client.post(
        "/api/cases",
        json={
            "case_code": "MIND-LEAK-B",
            "title": "Caso contaminante Mind",
            "description": "CONTAMINANTE-MIND-NO-DEBE-APARECER",
            "incident_type": "phishing",
        },
        headers=admin_headers,
    ).json()

    source = client.post(
        "/api/mind/graph/nodes",
        json={
            "case_id": case_a["id"],
            "node_key": f"url:{case_a['id']}",
            "node_type": "url",
            "label": "URL preservada del caso A",
            "source_module": "cybercrime",
        },
        headers=admin_headers,
    )
    assert source.status_code == 200
    source_key = source.json()["node_key"]
    target = client.post(
        "/api/mind/graph/nodes",
        json={
            "case_id": case_a["id"],
            "node_key": f"finding:{case_a['id']}",
            "node_type": "finding",
            "label": "Hallazgo relacional caso A",
            "source_module": "cybercrime",
        },
        headers=admin_headers,
    )
    assert target.status_code == 200
    target_key = target.json()["node_key"]
    edge = client.post(
        "/api/mind/graph/edges",
        json={
            "case_id": case_a["id"],
            "source_node_key": source_key,
            "target_node_key": target_key,
            "relation_type": "sostiene",
            "label": "URL sostiene hallazgo técnico",
            "confidence": "alto",
        },
        headers=admin_headers,
    )
    assert edge.status_code == 200
    note = client.post(
        "/api/mind/notes",
        json={
            "case_id": case_a["id"],
            "note_type": "hallazgo",
            "title": "Nota relacional caso A",
            "summary": "Resumen incorporable del caso A.",
            "content": "Contenido de memoria del caso A.",
            "tags": ["mind", "reporte"],
        },
        headers=admin_headers,
    )
    assert note.status_code == 200

    leaked = client.post(
        "/api/mind/notes",
        json={
            "case_id": case_b["id"],
            "note_type": "hallazgo",
            "title": "CONTAMINANTE-MIND-NO-DEBE-APARECER",
            "summary": "No debe filtrarse al caso A.",
            "content": "No debe filtrarse al caso A.",
            "tags": ["mind"],
        },
        headers=admin_headers,
    )
    assert leaked.status_code == 200

    report = client.post(f"/api/reports/case/{case_a['id']}/generate?author=Analista%20Mind", headers=admin_headers)
    assert report.status_code == 200
    markdown = report.json()["markdown_content"]
    assert "Memoria forense y grafo relacional del caso" in markdown
    assert "URL preservada del caso A" in markdown
    assert "Hallazgo relacional caso A" in markdown
    assert "Nota relacional caso A" in markdown
    assert "CONTAMINANTE-MIND-NO-DEBE-APARECER" not in markdown


def test_presentation_generates_oral_versions_and_case_theory(client, admin_headers):
    case = create_case(client, admin_headers)
    evidence = client.post(
        "/api/evidence",
        json={
            "case_id": case["id"],
            "description": "Captura central para exposición oral",
            "sha256_hash": "e" * 64,
        },
        headers=admin_headers,
    )
    assert evidence.status_code == 200
    report = client.post(f"/api/reports/case/{case['id']}/generate?author=Analista%20Mind", headers=admin_headers)
    assert report.status_code == 200
    presentation = client.post(
        f"/api/reports/{report.json()['id']}/presentations/generate?presentation_type=Exposicion%20oral%20CTF",
        headers=admin_headers,
    )
    assert presentation.status_code == 200
    slides = client.get(f"/api/reports/presentations/{presentation.json()['id']}/slides", headers=admin_headers)
    assert slides.status_code == 200
    titles = {item["title"] for item in slides.json()}
    full_text = "\n".join(item["text"] + "\n" + item["speaker_notes"] for item in slides.json())
    assert "Resumen oral" in titles
    assert "Teoría del caso" in titles
    assert "Preguntas posibles y respuestas sugeridas" in titles
    assert "Versión de 10 minutos" in titles
    assert "En tres minutos" in full_text
    assert "En diez minutos" in full_text
    assert "Captura central para exposición oral" in full_text
