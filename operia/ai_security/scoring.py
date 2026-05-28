def risk_level_from_score(score: int) -> str:
    if score >= 85:
        return "bajo"
    if score >= 65:
        return "medio"
    if score >= 40:
        return "alto"
    return "critico"


def recommendation_from_risk(risk_level: str) -> str:
    return {
        "bajo": "permitido con auditoria",
        "medio": "permitido con restricciones",
        "alto": "restringido",
        "critico": "bloqueado",
    }.get(risk_level, "restringido")

