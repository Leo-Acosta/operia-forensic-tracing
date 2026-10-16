"""Verified request grants; organization policy is an additional deny-by-default gate."""
from contextvars import ContextVar
from dataclasses import dataclass, field
import json
import time

@dataclass(frozen=True)
class ConnectorScope:
    actor_id: int
    organization_id: int
    case_id: int | None
    grants: frozenset[tuple[str, str]] = frozenset()
    local_ai: bool = False
    deadline: float = field(default_factory=lambda: time.monotonic() + 12)
    request_id: str = ""

connector_scope: ContextVar[ConnectorScope | None] = ContextVar("operia_connector_scope", default=None)


def organization_scope(user, case_id, policy_json, request_id=""):
    grants = set()
    local_ai = False
    try:
        if len(policy_json) > 32768:
            raise ValueError()
        from operia.forensic_engine.canonical import read_json
        policy = read_json(policy_json.encode(), limit=32768).get("connectors", {})
        for purpose in ("geo_ip", "legal_source"):
            rule = policy.get(purpose, {})
            if rule.get("enabled") is True and isinstance(rule.get("hosts"), list):
                grants.update((purpose, host) for host in rule["hosts"][:20] if isinstance(host, str))
        from operia.identity.permissions import has_permission
        local_ai = policy.get("local_ai", {}).get("enabled") is True and has_permission(user.role, "ai:use")
    except (ValueError, TypeError, AttributeError):
        grants.clear()
        local_ai = False
    return ConnectorScope(user.id, user.organization_id, case_id, frozenset(grants), local_ai, request_id=request_id)
