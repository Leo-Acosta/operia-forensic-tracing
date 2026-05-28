from operia.ai_security.models import AIModelEvaluation, AIModelTestRun


def evaluation_markdown(evaluation: AIModelEvaluation, tests: list[AIModelTestRun]) -> str:
    lines = [
        "# OPERIA AI Security Evaluation",
        "",
        "## Modelo",
        f"- Proveedor: {evaluation.provider}",
        f"- Modelo: {evaluation.model_name}",
        f"- Identificador: {evaluation.model_identifier or 'no informado'}",
        f"- Entorno: {evaluation.environment}",
        f"- Red bloqueada: {evaluation.network_blocked}",
        f"- Herramientas habilitadas: {evaluation.tools_enabled}",
        "",
        "## Resultado",
        f"- Score: {evaluation.overall_score}",
        f"- Riesgo observado: {evaluation.risk_level}",
        f"- Recomendacion: {evaluation.recommendation}",
        "",
        "## Conclusion",
        evaluation.conclusion,
        "",
        "## Pruebas",
    ]
    for test in tests:
        lines.append(f"- {test.test_code}: {test.severity} | passed={test.passed} | score={test.score}")
    lines.extend(
        [
            "",
            "## Limitaciones",
            "Este reporte no afirma que el modelo este libre de puertas traseras. Solo expresa el riesgo observado bajo condiciones locales, aisladas y auditadas.",
        ]
    )
    return "\n".join(lines)

