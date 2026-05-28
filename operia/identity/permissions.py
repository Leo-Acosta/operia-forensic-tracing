ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {"*"},
    "coordinador": {
        "cases:read",
        "cases:write",
        "evidence:read",
        "evidence:write",
        "reports:read",
        "reports:write",
        "legal:read",
        "legal:write",
        "ai:use",
        "audit:read",
    },
    "analista": {
        "cases:read",
        "cases:write",
        "evidence:read",
        "evidence:write",
        "reports:read",
        "reports:write",
        "legal:read",
        "ai:use",
    },
    "legal": {
        "cases:read",
        "evidence:read",
        "reports:read",
        "reports:write",
        "legal:read",
        "legal:write",
        "ai:use",
    },
    "lector": {"cases:read", "evidence:read", "reports:read", "legal:read"},
}


def has_permission(role: str, permission: str) -> bool:
    permissions = ROLE_PERMISSIONS.get(role, set())
    return "*" in permissions or permission in permissions

