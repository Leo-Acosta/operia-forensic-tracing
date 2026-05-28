from operia.legal_report.models import Case, Report, ReportSection, ReportVersion
from operia.legal_report.services.text_service import normalize_spanish

REPORT_SECTIONS = [
    "CarÃ¡tula",
    "Datos del caso",
    "Objeto del informe",
    "Alcance del anÃ¡lisis",
    "Limitaciones",
    "MetodologÃ­a utilizada",
    "Resumen ejecutivo",
    "DescripciÃ³n del incidente",
    "Evidencia recibida",
    "Registro de cadena de custodia",
    "LÃ­nea de tiempo de eventos",
    "AnÃ¡lisis tÃ©cnico-forense",
    "Matriz dato tÃ©cnico -> evidencia -> hallazgo",
    "Hallazgos principales",
    "HipÃ³tesis investigativas",
    "EvaluaciÃ³n de hipÃ³tesis alternativas",
    "Conclusiones tÃ©cnicas",
    "Encuadre jurÃ­dico argentino",
    "Responsabilidad penal preliminar",
    "Responsabilidad civil preliminar",
    "ProtecciÃ³n de datos personales",
    "Defensa del consumidor",
    "CuantificaciÃ³n econÃ³mica del daÃ±o",
    "ConclusiÃ³n jurÃ­dicamente defendible",
    "Recomendaciones",
    "Anexos",
    "Glosario tÃ©cnico",
    "Preguntas y respuestas para testimonio experto",
]


def build_integral_markdown(case: Case) -> str:
    total_damage = sum(item.amount for item in case.damage_items)
    evidence_lines = "\n".join(
        f"- Evidencia #{e.id}: {e.description}. SHA-256: `{e.sha256_hash or 'pendiente'}`. Integridad: {e.integrity_status}."
        for e in case.evidence
    ) or "- Sin evidencia cargada."
    custody_lines = "\n".join(
        f"- {a.action_at}: {a.action_type} - {a.detailed_description}."
        for a in sorted(case.actions, key=lambda action: action.action_at)
    ) or "- Sin acciones registradas."
    finding_lines = "\n".join(
        f"- {f.title}: {f.technical_finding}. Confianza: {f.confidence_level}. Limitaciones: {f.weaknesses_or_limitations or 'no indicadas'}."
        for f in case.findings
    ) or "- Sin hallazgos cargados."
    hypothesis_lines = "\n".join(
        f"- {h.title}: {h.description}. Soporte: {h.support_degree}. ConclusiÃ³n provisional: {h.provisional_conclusion or 'pendiente'}."
        for h in case.hypotheses
    ) or "- Sin hipÃ³tesis cargadas."
    legal_lines = "\n".join(
        f"- {m.legal_area}: {m.norm_reference}. {m.analysis}. Estado: {m.verification_status}."
        for m in case.legal_mappings
    ) or "- Sin encuadre legal cargado. Fuente pendiente de verificaciÃ³n."
    damage_lines = "\n".join(
        f"| {d.concept} | {d.amount:.2f} {d.currency} | {d.formula_used or 'pendiente'} | {d.value_source or 'pendiente'} | {d.certainty_level} |"
        for d in case.damage_items
    ) or "| Sin conceptos | 0 | pendiente | pendiente | bajo |"

    matrix_lines = "\n".join(
        f"| Dato #{f.technical_data_id or '-'} | Evidencia #{f.evidence_id or '-'} | {f.title} | {f.confidence_level} | {f.preliminary_legal_relevance or 'pendiente'} |"
        for f in case.findings
    ) or "| - | - | Pendiente | bajo | pendiente |"

    markdown = f"""# Operia Forensic Legal Report

## CarÃ¡tula

**Caso:** {case.title}  
**ID:** {case.case_code}  
**Responsable:** {case.responsible or 'pendiente'}  
**Cliente/VÃ­ctima:** {case.client_or_victim or 'pendiente'}  
**JurisdicciÃ³n:** {case.jurisdiction}

## Datos del caso

- Tipo de incidente: {case.incident_type}
- Estado: {case.status}
- DescripciÃ³n: {case.description or 'pendiente'}
- Observaciones: {case.general_observations or 'sin observaciones'}

## Objeto del informe

Ordenar datos tÃ©cnicos, evidencia preservada, hallazgos, hipÃ³tesis, encuadre legal argentino y cuantificaciÃ³n econÃ³mica del daÃ±o para una conclusiÃ³n defendible.

## Alcance del anÃ¡lisis

El alcance se limita a los datos, archivos, evidencias, fuentes legales y cÃ¡lculos cargados en la plataforma.

## Limitaciones

La herramienta asiste, pero no reemplaza revisiÃ³n profesional humana. No se afirma autorÃ­a personal sin medidas complementarias.

## MetodologÃ­a utilizada

Se preservaron datos tÃ©cnicos, se registraron acciones de cadena de custodia, se calcularon hashes cuando hubo archivos y se construyÃ³ la matriz dato tÃ©cnico -> evidencia -> hallazgo -> hipÃ³tesis -> conclusiÃ³n.

## Resumen ejecutivo

Se analiza un caso de {case.incident_type}. El daÃ±o econÃ³mico total estimado asciende preliminarmente a **{total_damage:.2f} ARS**, sujeto a fuentes, fÃ³rmulas y validaciÃ³n profesional.

## DescripciÃ³n del incidente

{case.description or 'DescripciÃ³n pendiente de ampliaciÃ³n.'}

## Evidencia recibida

{evidence_lines}

## Registro de cadena de custodia

{custody_lines}

## LÃ­nea de tiempo de eventos

{custody_lines}

## AnÃ¡lisis tÃ©cnico-forense

### Deepfake / IA
EvaluaciÃ³n pendiente segÃºn datos cargados.

### IoT / dispositivos conectados
EvaluaciÃ³n pendiente segÃºn datos cargados.

### Blockchain / criptomonedas
EvaluaciÃ³n pendiente segÃºn datos cargados.

### Logs, IPs, dominios y red
EvaluaciÃ³n pendiente segÃºn datos cargados.

### OSINT y fuentes abiertas
EvaluaciÃ³n pendiente segÃºn datos cargados.

## Matriz dato tÃ©cnico -> evidencia -> hallazgo

| Dato tÃ©cnico | Evidencia | Hallazgo | Confianza | Relevancia jurÃ­dica |
| --- | --- | --- | --- | --- |
{matrix_lines}

## Hallazgos principales

{finding_lines}

## HipÃ³tesis investigativas

{hypothesis_lines}

## EvaluaciÃ³n de hipÃ³tesis alternativas

Las hipÃ³tesis alternativas deben conservarse abiertas cuando existan hechos faltantes o riesgos de error.

## Conclusiones tÃ©cnicas

Con el alcance y limitaciones indicadas, los hallazgos permiten sostener preliminarmente compatibilidades tÃ©cnicas, no atribuciones personales definitivas.

## Encuadre jurÃ­dico argentino

{legal_lines}

## Responsabilidad penal preliminar

Debe ser revisada por abogado matriculado. No se atribuye autorÃ­a penal sin evidencia suficiente.

## Responsabilidad civil preliminar

Debe ser evaluada segÃºn nexo causal, daÃ±o acreditado y sujetos intervinientes.

## ProtecciÃ³n de datos personales

Debe revisarse posible aplicaciÃ³n de Ley 25.326 cuando existan datos personales comprometidos.

## Defensa del consumidor

Debe evaluarse si existe relaciÃ³n de consumo, plataformas, bancos, fintech, exchanges o proveedores digitales involucrados.

## CuantificaciÃ³n econÃ³mica del daÃ±o

| Concepto | Monto | Formula | Fuente | Certeza |
| --- | ---: | --- | --- | --- |
{damage_lines}

**DaÃ±o total estimado:** {total_damage:.2f} ARS.

## ConclusiÃ³n jurÃ­dicamente defendible

La evidencia resulta compatible con los hallazgos indicados, con las limitaciones explicitadas. La conclusiÃ³n requiere validaciÃ³n humana tÃ©cnica y jurÃ­dica.

## Recomendaciones

- Completar fuentes pendientes de verificaciÃ³n.
- Validar hashes, bitÃ¡cora y anexos.
- Reformular afirmaciones categÃ³ricas en tÃ©rminos tÃ©cnicos probabilÃ­sticos.

## Anexos

Anexos pendientes de selecciÃ³n y exportaciÃ³n.

## Glosario tÃ©cnico

- SHA-256: funciÃ³n criptogrÃ¡fica usada para verificar integridad.
- Cadena de custodia: registro cronolÃ³gico de preservaciÃ³n y manipulaciÃ³n de evidencia.

## Preguntas y respuestas para testimonio experto

**Pregunta:** Â¿QuÃ© demuestra un hash?  
**Respuesta sugerida:** Permite verificar integridad del archivo analizado, pero no demuestra por sÃ­ solo autorÃ­a personal.
"""
    return normalize_spanish(markdown)


def populate_report_sections(report: Report, markdown: str) -> list[ReportSection]:
    sections: list[ReportSection] = []
    for index, title in enumerate(REPORT_SECTIONS, start=1):
        marker = f"## {title}"
        next_content = markdown.split(marker, 1)[1] if marker in markdown else ""
        if "## " in next_content:
            next_content = next_content.split("\n## ", 1)[0]
        sections.append(ReportSection(report=report, order_index=index, title=title, content=next_content.strip()))
    return sections


def snapshot_report(report: Report, user: str, summary: str) -> ReportVersion:
    return ReportVersion(
        report=report,
        version_number=report.version,
        user=user,
        change_summary=summary,
        review_score=report.review_score,
        markdown_snapshot=report.markdown_content,
    )


def _incident_legal_basis(incident_type: str) -> list[str]:
    incident = incident_type.lower()
    basis = [
        "CÃ³digo Penal argentino: posible relevancia penal preliminar segÃºn conducta, dolo, perjuicio y medios empleados. Fuente pendiente de verificaciÃ³n.",
        "Ley 26.388: marco argentino de delitos informÃ¡ticos incorporado al CÃ³digo Penal. Fuente pendiente de verificaciÃ³n.",
        "Reglas procesales sobre prueba digital y cadena de custodia aplicables segÃºn jurisdicciÃ³n. Fuente pendiente de verificaciÃ³n.",
    ]
    if any(term in incident for term in ["phishing", "fraude", "cripto", "transferencia", "suplantaciÃ³n"]):
        basis.append("Fraude informÃ¡tico o maniobra defraudatoria digital: corresponde analizar ardid, error, disposiciÃ³n patrimonial y perjuicio econÃ³mico. Fuente pendiente de verificaciÃ³n.")
    if any(term in incident for term in ["acceso", "ransomware", "daÃ±o informÃ¡tico", "filtraciÃ³n"]):
        basis.append("Acceso no autorizado, afectaciÃ³n de sistemas, datos o disponibilidad: requiere vincular logs, hashes, trazabilidad y preservaciÃ³n de evidencia. Fuente pendiente de verificaciÃ³n.")
    if any(term in incident for term in ["datos", "filtraciÃ³n", "identidad"]):
        basis.append("Ley 25.326 de ProtecciÃ³n de Datos Personales: analizar tratamiento, exposiciÃ³n, deberes de seguridad y potencial afectaciÃ³n de titulares. Fuente pendiente de verificaciÃ³n.")
    if any(term in incident for term in ["consumidor", "banco", "fintech", "exchange", "plataforma", "cripto"]):
        basis.append("Ley 24.240 de Defensa del Consumidor: revisar relaciÃ³n de consumo, deber de seguridad, informaciÃ³n y trato digno si intervienen proveedores digitales. Fuente pendiente de verificaciÃ³n.")
    if any(term in incident for term in ["cripto", "blockchain", "wallet", "transferencia"]):
        basis.append("Blockchain y criptoactivos: la trazabilidad tÃ©cnica puede aportar compatibilidad econÃ³mica, pero no acredita por sÃ­ sola identidad personal del autor. Fuente pendiente de verificaciÃ³n.")
    if any(term in incident for term in ["deepfake", "ia"]):
        basis.append("EngaÃ±o habilitado por IA/deepfake: analizar autenticidad, manipulaciÃ³n, inducciÃ³n a error, daÃ±o y lÃ­mites tÃ©cnicos de detecciÃ³n. Fuente pendiente de verificaciÃ³n.")
    return basis


def polish_report_markdown(report: Report) -> str:
    case = report.case
    markdown = report.markdown_content or ""
    replacements = {
        "queda probado": "la evidencia disponible permite sostener preliminarmente",
        "sin dudas": "con el alcance y limitaciones indicadas",
        "el atacante fue": "el acceso o conducta analizada resulta compatible con",
        "demuestra que": "resulta compatible con",
        "fue culpable": "podrÃ­a tener relevancia jurÃ­dica, sujeto a validaciÃ³n profesional",
    }
    polished = markdown
    for source, target in replacements.items():
        polished = polished.replace(source, target).replace(source.capitalize(), target.capitalize())

    evidence_count = len(case.evidence)
    finding_count = len(case.findings)
    damage_total = sum(item.amount for item in case.damage_items)
    legal_basis = "\n".join(f"- {item}" for item in _incident_legal_basis(case.incident_type))
    legal_loaded = "\n".join(
        f"- {mapping.legal_area}: {mapping.norm_reference}. {mapping.analysis}. Estado: {mapping.verification_status}."
        for mapping in case.legal_mappings
    ) or "- No hay fuentes legales manuales cargadas. Toda cita queda como fuente pendiente de verificaciÃ³n."

    automatic_block = f"""
## Encuadre automÃ¡tico IA para revisiÃ³n humana

### Tipo de cibercrimen analizado

El caso se encuadra preliminarmente como **{case.incident_type}**. Esta clasificaciÃ³n se justifica por la descripciÃ³n del caso, los datos tÃ©cnicos cargados, la evidencia preservada y los hallazgos registrados. Al momento de esta revisiÃ³n existen {evidence_count} evidencias y {finding_count} hallazgos vinculados al caso.

### JustificaciÃ³n tÃ©cnico-jurÃ­dica

La lÃ­nea argumental defendible no salta de dato tÃ©cnico a conclusiÃ³n jurÃ­dica. Primero identifica datos tÃ©cnicos, luego evidencia preservada, despuÃ©s hallazgos verificables, hipÃ³tesis investigativas y finalmente conclusiones preliminares. Con ese alcance, la evidencia resulta compatible con un incidente digital que podrÃ­a tener relevancia penal, civil, probatoria, econÃ³mica y, segÃºn el caso, de consumo o protecciÃ³n de datos personales.

### Normativa argentina orientativa

{legal_basis}

### Fuentes legales cargadas manualmente

{legal_loaded}

### Enfoque para competencia o exposiciÃ³n acadÃ©mica

Para una competencia, jurado o audiencia simulada, la teorÃ­a del caso debe presentarse asÃ­: el incidente se describe de forma cronolÃ³gica; la evidencia clave se muestra con su hash o estado de integridad; los hallazgos se expresan en lenguaje probabilÃ­stico; las hipÃ³tesis alternativas se reconocen; el daÃ±o econÃ³mico estimado se informa como **{damage_total:.2f} ARS** sujeto a fÃ³rmula, fuente y validaciÃ³n; y la conclusiÃ³n se formula como jurÃ­dicamente defendible, no como atribuciÃ³n penal definitiva.

### Advertencia de no invenciÃ³n

Este encuadre automÃ¡tico no inventa jurisprudencia, doctrina ni citas. Cuando no hay fuente cargada o verificada, se conserva la leyenda **Fuente pendiente de verificaciÃ³n**.
"""

    marker = "## Encuadre automÃ¡tico IA para revisiÃ³n humana"
    if marker in polished:
        polished = polished.split(marker)[0].rstrip() + "\n\n" + automatic_block.strip() + "\n"
    else:
        polished = polished.rstrip() + "\n\n" + automatic_block.strip() + "\n"

    return normalize_spanish(polished)

