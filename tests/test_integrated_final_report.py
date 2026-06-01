from io import BytesIO

from pypdf import PdfReader


def _case(client, admin_headers, code: str, incident_type: str = "phishing"):
    response = client.post(
        "/api/cases",
        json={
            "case_code": code,
            "title": f"Informe integrado {code}",
            "description": "Caso de prueba para informe final integrado del desafio.",
            "incident_type": incident_type,
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    return response.json()["id"]


def _evidence(client, admin_headers, case_id: int, hash_char: str = "1"):
    response = client.post(
        "/api/evidence",
        json={
            "case_id": case_id,
            "evidence_type": "captura",
            "description": "Captura preservada con identificador verificable",
            "source": "Fuente aportada por denunciante",
            "sha256_hash": hash_char * 64,
            "tool_used": "hash local",
            "preservation_method": "copia preservada con hash",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    return response.json()["id"], response.json()["sha256_hash"]


def _report(client, admin_headers, case_id: int):
    response = client.post(f"/api/reports/case/{case_id}/generate?author=Analista%20Final", headers=admin_headers)
    assert response.status_code == 200
    return response.json()


def _pdf_text(client, admin_headers, report_id: int) -> str:
    response = client.get(f"/api/exports/reports/{report_id}/pdf", headers=admin_headers)
    assert response.status_code == 200
    return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(response.content)).pages)


def test_final_report_without_deepfake_does_not_render_deepfake_section(client, admin_headers):
    case_id = _case(client, admin_headers, "FINAL-NOMEDIA-001")
    _evidence(client, admin_headers, case_id)

    report = _report(client, admin_headers, case_id)
    markdown = report["markdown_content"].lower()
    pdf_text = _pdf_text(client, admin_headers, report["id"]).lower()

    assert "written legal evidence report 2026" in markdown
    assert "technical approach & investigative techniques used" in markdown
    assert "autenticación de medios y análisis deepfake" not in markdown
    assert "deepfake" not in markdown
    assert "deepfake" not in pdf_text


def test_final_report_with_deepfake_renders_media_authentication_section(client, admin_headers):
    case_id = _case(client, admin_headers, "FINAL-DEEPFAKE-001", "autenticacion de medios")
    evidence_id, evidence_hash = _evidence(client, admin_headers, case_id, "2")
    analysis = client.post(
        "/api/cybercrime/deepfake",
        json={
            "case_id": case_id,
            "evidence_id": evidence_id,
            "media_type": "video",
            "source_origin": "Publicacion preservada con fecha y hora",
            "metadata_summary": "Metadatos y compresion revisados.",
            "tool_used": "revision frame-by-frame",
            "findings": "Indicios de edicion sin conclusion definitiva.",
            "limitations": "Requiere fuente original y pericia especializada.",
            "classification": "indicios de edicion",
            "checklist": {"source_origin": True, "hash": True, "metadata": True, "limitations": True},
        },
        headers=admin_headers,
    )
    assert analysis.status_code == 200
    assert analysis.json()["evidence_hash"] == evidence_hash

    report = _report(client, admin_headers, case_id)
    lowered = report["markdown_content"].lower()
    assert "autenticaci" in lowered and "deepfake" in lowered
    assert "no permite afirmar de forma concluyente" in report["markdown_content"]
    assert "Autenticación de medios" in _pdf_text(client, admin_headers, report["id"])


def test_final_report_with_blockchain_renders_blockchain_section(client, admin_headers):
    case_id = _case(client, admin_headers, "FINAL-CHAIN-001", "blockchain")
    evidence_id, evidence_hash = _evidence(client, admin_headers, case_id, "3")
    tx = client.post(
        "/api/cybercrime/blockchain",
        json={
            "case_id": case_id,
            "evidence_id": evidence_id,
            "source_wallet": "bc1qsource",
            "destination_wallet": "bc1qdest",
            "tx_hash": "4" * 64,
            "blockchain": "Bitcoin",
            "token": "BTC",
            "amount": 0.1,
            "approximate_value": 1000,
            "route_hypothesis": "Ruta compatible con pago denunciado.",
            "wallet_classification": "wallet receptora",
            "limitations": "No hay titularidad personal de la wallet.",
        },
        headers=admin_headers,
    )
    assert tx.status_code == 200
    assert tx.json()["evidence_hash"] == evidence_hash

    report = _report(client, admin_headers, case_id)
    assert "Análisis forense de blockchain" in report["markdown_content"]
    pdf_text = _pdf_text(client, admin_headers, report["id"])
    assert "Analisis forense de blockchain" in pdf_text or "Análisis forense de blockchain" in pdf_text
    assert "no identifica por si sola" in report["markdown_content"]


def test_final_report_with_iot_renders_iot_section(client, admin_headers):
    case_id = _case(client, admin_headers, "FINAL-IOT-001", "iot")
    evidence_id, evidence_hash = _evidence(client, admin_headers, case_id, "5")
    device = client.post(
        "/api/cybercrime/iot",
        json={
            "case_id": case_id,
            "evidence_id": evidence_id,
            "device_type": "camara IP",
            "manufacturer": "Acme",
            "model": "Cam-200",
            "firmware": "2.0.0",
            "internal_ip": "192.168.0.20",
            "mac": "00:aa:bb:cc:dd:ee",
            "open_ports": "80/tcp observado en configuracion",
            "logs_available": "logs exportados",
            "limitations": "No se ejecutaron escaneos reales.",
            "checklist": {"physical_identification": True, "evidence_hash": True, "logs": True},
        },
        headers=admin_headers,
    )
    assert device.status_code == 200
    assert device.json()["evidence_hash"] == evidence_hash

    report = _report(client, admin_headers, case_id)
    assert "Análisis forense de dispositivos IoT" in report["markdown_content"]
    assert "no se ejecutan escaneos reales" in report["markdown_content"]
    pdf_text = _pdf_text(client, admin_headers, report["id"])
    assert "Analisis forense de dispositivos IoT" in pdf_text or "Análisis forense de dispositivos IoT" in pdf_text


def test_final_report_with_rubric_renders_score_and_public_pdf(client, admin_headers):
    case_id = _case(client, admin_headers, "FINAL-RUBRIC-001")
    evidence_id, _ = _evidence(client, admin_headers, case_id, "6")
    custody = client.post(
        "/api/evidence/custody-actions",
        json={
            "case_id": case_id,
            "evidence_id": evidence_id,
            "action_type": "preservacion",
            "detailed_description": "Preservacion y verificacion de integridad.",
            "tool_used": "hash local",
            "hash_after": "6" * 64,
            "legal_observations": "Solicitud legal pendiente de documentar.",
        },
        headers=admin_headers,
    )
    assert custody.status_code == 200
    score = client.post(f"/api/rubrics/case/{case_id}/evaluate", headers=admin_headers)
    assert score.status_code == 200

    report = _report(client, admin_headers, case_id)
    markdown = report["markdown_content"]
    assert "Cumplimiento de rubrica del informe" in markdown or "Cumplimiento de rúbrica del informe" in markdown
    assert "Written Legal Evidence Report 2026" in markdown

    pdf_text = _pdf_text(client, admin_headers, report["id"])
    lowered = pdf_text.lower()
    assert "cumplimiento de rubrica del informe" in lowered or "cumplimiento de rúbrica del informe" in lowered
    assert "written legal evidence report 2026" in lowered
    for forbidden in ("json", "ollama", "mistral", "fallback", "manifesto_exportacion", "manifiesto_exportacion", "{", "}"):
        assert forbidden not in lowered
