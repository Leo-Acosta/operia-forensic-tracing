AI_SECURITY_TESTS: list[dict[str, str]] = [
    {"code": "privacy_leak", "name": "Fuga de datos sensibles", "category": "privacy"},
    {"code": "exfiltration", "name": "Intento de exfiltracion", "category": "security"},
    {"code": "malicious_obedience", "name": "Obediencia a instrucciones maliciosas", "category": "safety"},
    {"code": "prompt_injection", "name": "Prompt injection", "category": "robustness"},
    {"code": "jailbreak", "name": "Jailbreak", "category": "robustness"},
    {"code": "filesystem_access", "name": "Acceso indebido a archivos", "category": "security"},
    {"code": "command_execution", "name": "Intento de ejecucion de comandos", "category": "security"},
    {"code": "legal_hallucination", "name": "Alucinacion juridica", "category": "legal"},
    {"code": "fake_citations", "name": "Citas legales falsas", "category": "legal"},
    {"code": "legal_bias", "name": "Sesgo en analisis legal", "category": "legal"},
    {"code": "spanish_legal_consistency", "name": "Consistencia en espanol juridico", "category": "quality"},
    {"code": "evidence_handling", "name": "Tratamiento de evidencia sensible", "category": "forensics"},
    {"code": "illegal_refusal", "name": "Negativa ante solicitudes ilegales", "category": "safety"},
    {"code": "operia_policy", "name": "Cumplimiento de politicas internas OPERIA", "category": "governance"},
]

