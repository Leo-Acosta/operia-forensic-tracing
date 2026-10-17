"""Explicit opt-in: real fixed-loopback provider, synthetic temporary database only."""
import http.client
import json
import os
from pathlib import Path
import time

import pytest

from operia.core.config import settings
from operia.security import ai_gateway as gateway, outbound
from operia.security.sandbox_runtime import prepare
from test_native_mobile_workflow import database_factory
from test_security_audit import second_tenant

pytestmark = pytest.mark.skipif(os.environ.get("OPERIA_TEST_REAL_OLLAMA") != "1", reason="Real Ollama requires explicit operator opt-in")


def test_real_ollama_case_and_tenant_isolation(client, admin_headers, monkeypatch):
    from operia.ai_assistant.models import AIInteraction
    from operia.identity.models import Organization
    from operia.cases.models import Case

    model = os.environ.get("OPERIA_TEST_OLLAMA_MODEL", "qwen2.5:0.5b")
    prepare()
    monkeypatch.setattr(settings, "local_ai_enabled", True)
    monkeypatch.setattr(settings, "local_ai_gateway_enabled", True)
    monkeypatch.setattr(settings, "local_ai_allowed_models", [model])
    with outbound._lock:
        outbound._calls.clear(); outbound._active.clear()
    org, _, other_headers = second_tenant(client)

    def grant(org_id):
        with database_factory()() as db:
            db.get(Organization, org_id).settings_json = json.dumps({"connectors": {"local_ai": {"enabled": True, "models": [model]}}})
            db.commit()

    def case(headers, code, marker):
        response = client.post("/api/cases", headers=headers, json={"case_code": code, "title": "Synthetic connectivity only", "description": marker})
        assert response.status_code == 200
        return response.json()["id"]

    first = case(admin_headers, "REAL-A", "SYNTHETIC_ALPHA_731")
    second = case(admin_headers, "REAL-B", "SYNTHETIC_BETA_842")
    foreign = case(other_headers, "REAL-C", "SYNTHETIC_GAMMA_953")
    grant(1)
    calls = []
    exchange = gateway._exchange

    def observe(body, deadline):
        request = json.loads(body)
        started = time.monotonic()
        raw = exchange(body, deadline)  # Real connection, endpoint and transport unchanged.
        result = json.loads(raw)
        calls.append({"request": request, "done": result["done"], "seconds": round(time.monotonic() - started, 3),
                      "eval_count": result.get("eval_count"), "load_duration_ns": result.get("load_duration")})
        return raw

    monkeypatch.setattr(gateway, "_exchange", observe)
    prompt = "Synthetic connectivity check. Use null for every requested field except requiere_revision_humana=true. No explanations. Keep the whole reply below 60 words."

    def ask(headers, case_id):
        return client.post("/api/ai/assist", headers=headers, json={"case_id": case_id, "model_name": model, "prompt": prompt, "include_case_context": True})

    initial = ask(admin_headers, first)
    assert initial.status_code == 200 and initial.json()["status"] == "completed", initial.json().get("safety_notes")
    saved = initial.json()
    assert ask(admin_headers, foreign).status_code == 404
    assert ask(other_headers, foreign).json()["status"] == "ollama_unavailable"
    assert len(calls) == 1
    assert ask(admin_headers, second).json()["status"] == "completed"
    grant(org)
    assert ask(other_headers, foreign).json()["status"] == "completed"
    markers = ("SYNTHETIC_ALPHA_731", "SYNTHETIC_BETA_842", "SYNTHETIC_GAMMA_953")
    for index, call in enumerate(calls):
        request = call["request"]
        assert markers[index] in request["prompt"]
        assert all(marker not in request["prompt"] for position, marker in enumerate(markers) if position != index)
        assert set(request) == {"model", "prompt", "stream", "keep_alive", "options"}
        assert request["keep_alive"] == 0 and request["stream"] is False and call["done"] is True
    with database_factory()() as db:
        historical = db.get(AIInteraction, saved["id"])
        assert historical.response == saved["response"] and historical.case_id == first and historical.organization_id == 1
        assert historical.requires_human_review
        assert db.get(Case, first).description == markers[0]
    def metadata(path):
        connection = http.client.HTTPConnection("127.0.0.1", 11434, timeout=2)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            assert response.status == 200
            return json.loads(response.read(256 * 1024))
        finally:
            connection.close()
    tags = metadata("/api/tags")
    version = metadata("/api/version")["version"]
    assert all(item["name"] != model for item in metadata("/api/ps")["models"])
    selected = next(item for item in tags["models"] if item["name"] == model)
    report = {"schema": "operia-real-ollama-validation/1", "synthetic_only": True, "model": model,
              "ollama_version": version, "model_unloaded_after_response": True,
              "digest": selected["digest"], "size_bytes": selected["size"], "generations": [
                  {key: value for key, value in call.items() if key != "request"} for call in calls],
              "cross_tenant_denied": True, "disabled_tenant_denied": True, "case_context_isolated": True,
              "historical_interaction_unchanged": True, "transport_mocked": False}
    if os.environ.get("OPERIA_TEST_OLLAMA_REPORT"):
        Path(os.environ["OPERIA_TEST_OLLAMA_REPORT"]).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
