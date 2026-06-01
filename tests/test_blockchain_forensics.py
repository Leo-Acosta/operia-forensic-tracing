from io import BytesIO

from pypdf import PdfReader


def test_blockchain_forensics_registers_finding_legal_mapping_and_report(client, admin_headers):
    case = client.post(
        "/api/cases",
        json={
            "case_code": "CHAIN-001",
            "title": "Trazabilidad cripto",
            "description": "Fraude con transferencia cripto posterior a comunicaciones engañosas.",
            "incident_type": "blockchain / criptoactivos",
        },
        headers=admin_headers,
    )
    assert case.status_code == 200
    case_id = case.json()["id"]

    evidence = client.post(
        "/api/evidence",
        json={
            "case_id": case_id,
            "evidence_type": "captura blockchain",
            "description": "Captura preservada del explorador y chat de pago",
            "source": "Explorador consultado manualmente",
            "sha256_hash": "e" * 64,
            "tool_used": "navegador + hash local",
            "preservation_method": "captura con timestamp y hash",
        },
        headers=admin_headers,
    )
    assert evidence.status_code == 200
    evidence_id = evidence.json()["id"]

    tx = client.post(
        "/api/cybercrime/blockchain",
        json={
            "case_id": case_id,
            "evidence_id": evidence_id,
            "source_wallet": "bc1qsourcewallet",
            "destination_wallet": "bc1qdestinationwallet",
            "tx_hash": "f" * 64,
            "blockchain": "Bitcoin",
            "token": "BTC",
            "amount": 0.25,
            "approximate_value": 25000,
            "tx_datetime": "2026-05-20T14:30:00Z",
            "explorer_url": "https://example.invalid/tx/" + "f" * 64,
            "route_hypothesis": "Estafa con pago a wallet receptora; posible exchange indicado por comunicación posterior.",
            "wallet_classification": "wallet receptora",
            "tool_used": "OPERIA Blockchain Forensics",
            "limitations": "No hay titularidad de wallet ni KYC de plataforma; requiere oficio y correlación externa.",
        },
        headers=admin_headers,
    )
    assert tx.status_code == 200
    body = tx.json()
    assert body["case_id"] == case_id
    assert body["evidence_id"] == evidence_id
    assert body["evidence_hash"] == "e" * 64
    assert body["wallet_classification"] == "wallet receptora"
    assert "no identifica por sí sola" in body["warning"]

    listing = client.get(f"/api/cybercrime/blockchain/case/{case_id}", headers=admin_headers)
    assert listing.status_code == 200
    assert listing.json()[0]["tx_hash"] == "f" * 64
    assert any("Evitar atribución personal solo por wallet" in item for item in listing.json()[0]["recommended_measures"])

    finding = client.post(f"/api/cybercrime/blockchain/{body['id']}/finding", headers=admin_headers)
    assert finding.status_code == 200
    assert "limites de atribucion" in finding.json()["message"]

    legal = client.post(
        f"/api/cybercrime/blockchain/{body['id']}/apply-legal",
        json={"fraud": True, "computer_manipulation": True, "extortion": True, "blackmail": True, "personal_data": True},
        headers=admin_headers,
    )
    assert legal.status_code == 200
    applied = {item["norm_reference"] for item in legal.json()["applied"]}
    assert any(ref.startswith("CP art. 172") for ref in applied)
    assert any(ref.startswith("CP art. 173 inc. 16") for ref in applied)
    assert any(ref.startswith("CP art. 168") for ref in applied)
    assert any(ref.startswith("CP art. 169") for ref in applied)
    assert any(ref.startswith("LPDP art. 5") for ref in applied)

    report = client.post(f"/api/reports/case/{case_id}/generate?author=Analista%20Blockchain", headers=admin_headers)
    assert report.status_code == 200
    markdown = report.json()["markdown_content"]
    assert "Análisis forense de blockchain" in markdown
    assert "no identifica por sí sola a una persona" in markdown
    assert "identifica al autor" not in markdown.lower()

    pdf = client.get(f"/api/exports/reports/{report.json()['id']}/pdf", headers=admin_headers)
    assert pdf.status_code == 200
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf.content)).pages)
    assert "Análisis forense de blockchain" in pdf_text
    assert "no identifica por sí sola" in pdf_text
