EXPECTED_ARTICLES = {
    ("CP", "172", ""),
    ("CP", "173", "16"),
    ("CP", "153", ""),
    ("CP", "153 bis", ""),
    ("CP", "155", ""),
    ("CP", "157 bis", ""),
    ("CP", "168", ""),
    ("CP", "169", ""),
    ("CP", "149 bis", ""),
    ("CP", "128", ""),
    ("CP", "131", ""),
    ("CP", "293", ""),
    ("CP", "296", ""),
    ("CP", "109", ""),
    ("CP", "110", ""),
    ("LPDP", "5", ""),
    ("LPDP", "9", ""),
    ("LPDP", "10", ""),
    ("LPDP", "11", ""),
    ("CCCN", "51-53", ""),
    ("LPI", "1", ""),
    ("LPI", "71", ""),
}


def _seed_and_articles(client):
    seed = client.post("/api/legal-knowledge/articles/seed")
    assert seed.status_code == 200
    response = client.get("/api/legal-knowledge/articles")
    assert response.status_code == 200
    return response.json()


def _recommend_refs(client, incident_text):
    response = client.post("/api/legal-knowledge/articles/recommend", json={"incident_text": incident_text})
    assert response.status_code == 200
    body = response.json()
    return body, {item["reference"] for item in body["recommendations"]}


def test_ctf_legal_articles_exist(client):
    articles = _seed_and_articles(client)
    present = {(item["code"], item["article_number"], item["subsection"] or "") for item in articles}
    assert EXPECTED_ARTICLES.issubset(present)


def test_ctf_profiles_return_expected_norms(client):
    _seed_and_articles(client)
    expectations = {
        "phishing fraude digital con pago y credenciales": {"CP art. 172", "CP art. 173 inc. 16"},
        "ransomware extorsión con cifrado y nota de rescate": {"CP art. 168", "CP art. 183"},
        "filtración de datos personales confidenciales": {"CP art. 157 bis", "LPDP art. 9"},
        "acceso ilegítimo a sistema de acceso restringido": {"CP art. 153 bis"},
        "falsedad documental digital con certificado falso": {"CP art. 293", "CP art. 296"},
    }
    for incident_text, expected_refs in expectations.items():
        _, refs = _recommend_refs(client, incident_text)
        assert expected_refs.issubset(refs)


def test_deepfake_returns_cccn_and_intellectual_property(client):
    _seed_and_articles(client)
    body, refs = _recommend_refs(client, "deepfake de voz e imagen para suplantar identidad")
    assert body["profile"]["key"] == "deepfake"
    assert {"CCCN art. 51-53", "LPI art. 1"}.issubset(refs)


def test_blockchain_returns_cp_172_173_168(client):
    _seed_and_articles(client)
    body, refs = _recommend_refs(client, "blockchain criptoactivos wallet estafa manipulación informática extorsión")
    assert body["profile"]["key"] == "blockchain"
    assert {"CP art. 172", "CP art. 173 inc. 16", "CP art. 168"}.issubset(refs)


def test_iot_returns_cp_153bis_183_197(client):
    _seed_and_articles(client)
    body, refs = _recommend_refs(client, "iot dispositivos conectados acceso ilegítimo daño informático comunicaciones")
    assert body["profile"]["key"] == "iot"
    assert {"CP art. 153 bis", "CP art. 183", "CP art. 197"}.issubset(refs)


def test_ctf_library_does_not_invent_sources(client):
    articles = _seed_and_articles(client)
    official_hosts = (
        "https://www.argentina.gob.ar/normativa/nacional/",
    )
    for item in articles:
        assert item["official_url"].startswith(official_hosts)

    body, _ = _recommend_refs(client, "deepfake blockchain iot phishing")
    assert body["policy"]["registered_sources_only"] is True
    assert body["policy"]["no_unregistered_jurisprudence_or_doctrine"] is True
    for item in body["recommendations"]:
        assert item["source_url"].startswith(official_hosts)
        assert item["precedents"] == []
        assert item["doctrine"] == []
