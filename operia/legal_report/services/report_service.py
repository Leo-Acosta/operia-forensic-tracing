from typing import Any

from operia.cases.models import Case
from operia.reports.models import Report, ReportSection, ReportVersion
from operia.legal_report.services.text_service import normalize_spanish

NO_ATTRIBUTION_TEXT = (
    "Del análisis efectuado no surgen elementos técnicos suficientes que permitan atribuir el ataque informático "
    "a una persona física, grupo organizado, entidad u organización determinada."
)

ATTRIBUTION_METHOD_NOTE = (
    "La atribución técnica de un ciberataque no debe confundirse con la atribución penal de autoría: la primera "
    "identifica patrones, infraestructura, indicadores y probabilidades; la segunda exige prueba jurídicamente "
    "valorable, individualización subjetiva y control contradictorio en el proceso penal."
)

REPORT_SECTIONS = [
    "Carátula",
    "Datos del caso",
    "Personas y entidades vinculadas",
    "Objeto del informe",
    "Alcance del análisis",
    "Limitaciones",
    "Metodología utilizada",
    "Resumen ejecutivo",
    "Descripción del incidente",
    "Evidencia recibida",
    "Registro de cadena de custodia",
    "Línea de tiempo de eventos",
    "Análisis técnico-forense",
    "Matriz dato técnico -> evidencia -> hallazgo",
    "Hallazgos principales",
    "Hipótesis investigativas",
    "Evaluación de hipótesis alternativas",
    "Conclusiones técnicas",
    "Encuadre jurídico argentino",
    "Responsabilidad penal preliminar",
    "Responsabilidad civil preliminar",
    "Protección de datos personales",
    "Defensa del consumidor",
    "Cuantificación económica del daño",
    "Conclusión jurídicamente defendible",
    "Recomendaciones",
    "Anexos",
    "Glosario técnico",
    "Preguntas y respuestas para testimonio experto",
]


def build_integral_markdown(case: Case, legal_recommendations: list[Any] | None = None) -> str:
    total_damage = sum(item.amount for item in case.damage_items)
    participant_lines = "\n".join(
        (
            f"- {p.display_name} ({p.person_type}; rol: {p.participant_type}). "
            f"Relacion: {p.relationship_to_case or p.role_description or 'pendiente'}. "
            f"Sensibilidad: {p.sensitivity_level}."
        )
        for p in case.participants
    ) or "- Sin personas o entidades vinculadas cargadas."
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
        f"- {h.title}: {h.description}. Soporte: {h.support_degree}. Conclusión provisional: {h.provisional_conclusion or 'pendiente'}."
        for h in case.hypotheses
    ) or "- Sin hipótesis cargadas."
    approved_mappings = [
        m for m in case.legal_mappings if getattr(m, "decision_status", "sugerido") != "descartado"
    ]
    legal_lines = "\n".join(
        f"- {m.legal_area}: {m.norm_reference}. {m.analysis}. Estado: {m.verification_status}."
        + _legal_mapping_evidence_suffix(m)
        for m in approved_mappings
    ) or "- Sin encuadre legal cargado. Fuente pendiente de verificación."
    if not case.hypotheses:
        hypothesis_lines = _default_hypotheses_markdown(case)
    if not approved_mappings:
        legal_lines = _legal_recommendation_markdown(legal_recommendations or [])
    damage_lines = "\n".join(
        f"| {d.concept} | {d.amount:.2f} {d.currency} | {d.formula_used or 'pendiente'} | {d.value_source or 'pendiente'} | {d.certainty_level} |"
        for d in case.damage_items
    ) or "| Sin conceptos | 0 | pendiente | pendiente | bajo |"

    matrix_lines = "\n".join(
        f"| Dato #{f.technical_data_id or '-'} | Evidencia #{f.evidence_id or '-'} | {f.title} | {f.confidence_level} | {f.preliminary_legal_relevance or 'pendiente'} |"
        for f in case.findings
    ) or "| - | - | Pendiente | bajo | pendiente |"

    responsible_text = case.responsible or NO_ATTRIBUTION_TEXT
    client_or_victim = case.client_or_victim or ""
    description_text = case.description or ""

    markdown = f"""# Operia Forensic Legal Report

## Carátula

**Caso:** {case.title}  
**ID:** {case.case_code}  
**Responsable:** {responsible_text}
**Cliente/Víctima:** {client_or_victim}
**Jurisdicción:** {case.jurisdiction}

## Datos del caso

- Tipo de incidente: {case.incident_type}
- Estado: {case.status}
- Descripción: {description_text}
- Observaciones: {case.general_observations or 'sin observaciones'}

## Personas y entidades vinculadas

{participant_lines}

## Objeto del informe

Ordenar datos técnicos, evidencia preservada, hallazgos, hipótesis, encuadre legal argentino y cuantificación económica del daño para una conclusión defendible.

## Alcance del análisis

El alcance se limita a los datos, archivos, evidencias, fuentes legales y cálculos cargados en la plataforma.

## Limitaciones

La herramienta asiste, pero no reemplaza revisión profesional humana. No se afirma autoría personal sin medidas complementarias.

## Metodología utilizada

Se preservaron datos técnicos, se registraron acciones de cadena de custodia, se calcularon hashes cuando hubo archivos y se construyó la matriz dato técnico -> evidencia -> hallazgo -> hipótesis -> conclusión.

## Resumen ejecutivo

Se analiza un caso de {case.incident_type}. El daño económico total estimado asciende preliminarmente a **{total_damage:.2f} ARS**, sujeto a fuentes, fórmulas y validación profesional.

## Descripción del incidente

{description_text}

## Evidencia recibida

{evidence_lines}

## Registro de cadena de custodia

{custody_lines}

## Línea de tiempo de eventos

{custody_lines}

## Análisis técnico-forense

### Deepfake / IA
Evaluación pendiente según datos cargados.

### IoT / dispositivos conectados
Evaluación pendiente según datos cargados.

### Blockchain / criptomonedas
Evaluación pendiente según datos cargados.

### Logs, IPs, dominios y red
Evaluación pendiente según datos cargados.

### OSINT y fuentes abiertas
Evaluación pendiente según datos cargados.

## Matriz dato técnico -> evidencia -> hallazgo

| Dato técnico | Evidencia | Hallazgo | Confianza | Relevancia jurídica |
| --- | --- | --- | --- | --- |
{matrix_lines}

## Hallazgos principales

{finding_lines}

## Hipótesis investigativas

{hypothesis_lines}

## Evaluación de hipótesis alternativas

Las hipótesis alternativas deben conservarse abiertas cuando existan hechos faltantes o riesgos de error.

## Conclusiones técnicas

Con el alcance y limitaciones indicadas, los hallazgos permiten sostener preliminarmente compatibilidades técnicas, no atribuciones personales definitivas.

## Encuadre jurídico argentino

{legal_lines}

### Metodo de aplicacion normativa

La aplicacion juridica se realiza con una secuencia controlada: hecho investigado, evidencia disponible, elemento objetivo de la norma, elemento subjetivo a verificar, evidencia faltante y conclusion prudente. Si una norma aparece como posible, no implica calificacion definitiva ni atribucion personal.

## Responsabilidad penal preliminar

Debe ser revisada por abogado matriculado. No se atribuye autoría penal sin evidencia suficiente.

## Responsabilidad civil preliminar

Debe ser evaluada según nexo causal, daño acreditado y sujetos intervinientes.

## Protección de datos personales

Debe revisarse posible aplicación de Ley 25.326 cuando existan datos personales comprometidos.

## Defensa del consumidor

Debe evaluarse si existe relación de consumo, plataformas, bancos, fintech, exchanges o proveedores digitales involucrados.

## Cuantificación económica del daño

| Concepto | Monto | Formula | Fuente | Certeza |
| --- | ---: | --- | --- | --- |
{damage_lines}

**Daño total estimado:** {total_damage:.2f} ARS.

## Conclusión jurídicamente defendible

La evidencia resulta compatible con los hallazgos indicados, con las limitaciones explicitadas. La conclusión requiere validación humana técnica y jurídica.

### Sintesis aplicada al caso

{_incident_specific_conclusion(case)}

## Recomendaciones

- Completar fuentes pendientes de verificación.
- Validar hashes, bitácora y anexos.
- Reformular afirmaciones categóricas en términos técnicos probabilísticos.

## Anexos

Anexos pendientes de selección y exportación.

## Glosario técnico

- SHA-256: función criptográfica usada para verificar integridad.
- Cadena de custodia: registro cronológico de preservación y manipulación de evidencia.

## Preguntas y respuestas para testimonio experto

**Pregunta:** ¿Qué demuestra un hash?  
**Respuesta sugerida:** Permite verificar integridad del archivo analizado, pero no demuestra por sí solo autoría personal.
"""
    return normalize_spanish(markdown)


def _default_hypotheses_markdown(case: Case) -> str:
    evidence_count = len(case.evidence)
    custody_count = len(case.actions)
    incident = normalize_spanish(case.incident_type or "incidente digital")
    if evidence_count <= 1 and not case.findings:
        return normalize_spanish(
            f"- Hipótesis principal: el hecho investigado resulta compatible con una maniobra de {incident} mediante captación engañosa de la víctima a través de anuncio, enlace, perfil o comunicación falsa, orientada a obtener datos, credenciales o desplazamiento patrimonial. Con el estado actual de la evidencia no corresponde formular hipótesis alternativas autónomas."
        )
    return normalize_spanish(
        "\n".join(
            [
                f"- Hipotesis principal: el relato y la evidencia cargada son compatibles con un {incident}; soporte actual: {evidence_count} evidencia(s) y {custody_count} accion(es) de custodia. Requiere validar origen, integridad, titularidad y nexo causal.",
                "- Hipotesis alternativa 1: el evento puede responder a error operativo, compromiso de credenciales, suplantacion o intermediacion de una plataforma; requiere contrastar logs, titulares, sesiones, dispositivos y comunicaciones.",
                "- Hipotesis alternativa 2: si hay perjuicio economico, la trazabilidad financiera puede demostrar recorrido o compatibilidad temporal, pero no identifica por si sola al autor.",
                "- Riesgo de error: no formular atribucion personal ni calificacion penal definitiva sin evidencia externa, oficios, pericia complementaria y revision profesional.",
            ]
        )
    )


def _legal_recommendation_markdown(recommendations: list[Any]) -> str:
    if not recommendations:
        return ""
    lines = []
    for item in recommendations:
        if isinstance(item, dict):
            reference = item.get("reference", "Norma pendiente")
            title = item.get("title", "")
            why = item.get("why", "")
            evidence_needed = item.get("evidence_needed", "")
            source_url = item.get("source_url", "")
            text = item.get("text", "")
            subjective = item.get("subjective_elements", "")
        else:
            reference = f"{item.code} art. {item.article_number}{' inc. ' + item.subsection if item.subsection else ''}"
            title = item.title
            why = item.objective_elements
            evidence_needed = item.evidentiary_requirements
            source_url = item.official_url
            text = item.text
            subjective = item.subjective_elements
        lines.extend(
            [
                f"- **{reference} - {title}.**",
                f"  - Texto legal resumido registrado: {text or 'pendiente de carga textual completa'}.",
                f"  - Elementos objetivos a verificar: {why or 'pendiente'}.",
                f"  - Elementos subjetivos o recaudos: {subjective or 'pendiente'}.",
                f"  - Evidencia necesaria: {evidence_needed or 'pendiente'}.",
                f"  - Fuente oficial registrada: {source_url or 'pendiente de verificacion'}.",
                "  - Aplicacion prudente al caso: posible relevancia preliminar, sujeta a verificacion de hechos, evidencia preservada y revision humana.",
            ]
        )
    return normalize_spanish("\n".join(lines))


def _legal_mapping_evidence_suffix(mapping: Any) -> str:
    links = [link for link in getattr(mapping, "evidence_links", []) if getattr(link, "evidence", None)]
    if not links:
        return ""
    pieces = []
    for link in links:
        evidence = link.evidence
        pieces.append(
            f"Evidencia #{evidence.id}: {evidence.description} "
            f"(elemento: {link.legal_element or 'no especificado'}, fuerza: {link.probatory_strength})."
        )
    return " Evidencia vinculada: " + " ".join(pieces)


def build_ai_enrichment_markdown(case: Case, legal_recommendations: list[Any], ai_response: str = "") -> str:
    legal_block = _legal_recommendation_markdown(legal_recommendations)
    hypotheses = _default_hypotheses_markdown(case)
    evidence_summary = "\n".join(
        f"- Evidencia #{item.id}: {item.description}. Hash: {item.sha256_hash or 'pendiente'}. Integridad: {item.integrity_status}."
        for item in case.evidence[:8]
    ) or "- No hay evidencia suficiente cargada para sostener una conclusion fuerte."
    return normalize_spanish(
        f"""
## Hipótesis y análisis del caso

{hypotheses}

## Evidencia que sostiene o limita la teoría del caso

{evidence_summary}

## Encuadre legal argentino

{legal_block}

## Conclusión técnico-jurídica

{build_attribution_conclusion(case)}
"""
    )


def _attribution_subject(case: Case) -> str | None:
    for participant in case.participants:
        role = normalize_spanish(participant.participant_type).lower()
        if role in {"sospechoso", "imputado", "atacante", "grupo_atribucion", "grupo organizado"}:
            return participant.display_name
    return None


def attribution_assessment(case: Case) -> dict[str, object]:
    subject = _attribution_subject(case)
    evidence_text = " ".join(
        [
            " ".join(item.description for item in case.evidence),
            " ".join(item.detailed_description for item in case.actions),
            " ".join(item.technical_finding for item in case.findings),
        ]
    ).lower()
    signals = {
        "persona_o_grupo_identificado": bool(subject),
        "ip_vinculada": "ip" in evidence_text or any("ip" in item.evidence_type.lower() for item in case.evidence),
        "logs": "log" in evidence_text or any("log" in item.evidence_type.lower() for item in case.evidence),
        "metadatos_sesion": "sesion" in evidence_text or "session" in evidence_text or "metadato" in evidence_text,
        "artefactos_maliciosos": any(term in evidence_text for term in ["malware", "hash", "exe", "script", "artefacto"]),
        "correlacion_temporal": any(term in evidence_text for term in ["correlacion", "timestamp", "horario", "fecha", "temporal"]),
        "registros_proveedor": any(term in evidence_text for term in ["proveedor", "oficio", "abonado", "telecom", "plataforma"]),
        "trazabilidad_pagos": any(term in evidence_text for term in ["pago", "transferencia", "wallet", "cbu", "alias", "mercado pago", "billetera"]),
        "evidencia_externa": any(term in evidence_text for term in ["secuestro", "dispositivo", "notebook", "pericia", "domicilio"]),
    }
    score = sum(1 for value in signals.values() if value)
    sufficient = bool(subject) and score >= 5 and len(case.evidence) >= 2 and len(case.actions) >= 1
    return {"sufficient": sufficient, "subject": subject, "score": score, "signals": signals}


def _incident_specific_conclusion(case: Case) -> str:
    incident = normalize_spanish(case.incident_type or "").lower()
    description = normalize_spanish(case.description or "")
    if "phishing" in incident or "fraude" in incident:
        return normalize_spanish(
            f"El caso se analiza como una hipotesis preliminar de phishing/fraude digital. El relato disponible ({description or 'sin descripcion ampliada'}) permite orientar la investigacion hacia una posible maniobra de captacion mediante anuncio, ardid o suplantacion. En terminos juridicos argentinos, la figura base a evaluar es el art. 172 del Codigo Penal, porque exige verificar ardid o engano, error de la victima, disposicion patrimonial, perjuicio y nexo causal. Si la maniobra incluyo alteracion, manipulacion o uso de sistemas informaticos para producir el desplazamiento patrimonial, tambien corresponde revisar el art. 173 inc. 16 del Codigo Penal. Si hubo ingreso a cuentas, casillas, perfiles o sistemas sin autorizacion, debe evaluarse el art. 153 bis. Si se captaron, usaron o expusieron datos personales, la Ley 25.326 aporta un plano adicional de proteccion de datos. Si intervino una plataforma, marketplace, banco, fintech o proveedor digital, la Ley 24.240 puede ser relevante para deberes de informacion, seguridad y responsabilidad de consumo. La conclusion defendible no es afirmar autoria personal, sino sostener que la teoria del caso es compatible con una maniobra defraudatoria digital que requiere preservar comunicaciones, anuncios, URLs, identificadores de cuenta, trazabilidad de pagos, logs, titulares de cuentas receptoras y respuestas de proveedores."
        )
    return normalize_spanish(
        "La conclusion debe formularse como teoria preliminar: hechos, evidencia, hallazgos, normas aplicables y evidencia faltante. No corresponde cerrar autoria o responsabilidad definitiva sin preservacion, trazabilidad y revision profesional."
    )


def build_attribution_conclusion(case: Case) -> str:
    assessment = attribution_assessment(case)
    if assessment["sufficient"]:
        subject = assessment["subject"] or "sujeto identificado"
        return normalize_spanish(
            f"""CONCLUSIÓN TÉCNICO-JURÍDICA SOBRE ATRIBUCIÓN DEL CIBERATAQUE

De conformidad con el análisis técnico-forense efectuado sobre la evidencia incorporada al caso, corresponde concluir que existen elementos técnicos suficientes, concordantes y convergentes para atribuir prima facie la ejecución del ataque informático investigado a {subject}.

La atribución no se funda en un único indicador aislado, sino en una pluralidad de evidencias digitales recíprocamente corroboradas, cuya valoración debe considerar registros de acceso, trazabilidad temporal, artefactos técnicos, hashes, indicadores de infraestructura, eventuales registros de proveedor y demás elementos externos disponibles.

Desde el punto de vista jurídico penal argentino, los hechos analizados resultan prima facie compatibles con figuras de acceso ilegítimo, fraude digital, defraudación mediante manipulación informática, daño informático o afectación de datos personales, según el alcance final de la prueba. La calificación definitiva corresponde a la autoridad competente.

En consecuencia, este informe concluye que sí existen elementos técnicos, indiciarios y jurídicamente relevantes que permiten formular una atribución técnica preliminar, sin perjuicio de que dicha atribución conserva naturaleza técnico-pericial y deberá ser valorada jurisdiccionalmente conforme las reglas de la sana crítica racional, la contradicción de partes, la cadena de custodia y el estándar probatorio propio del proceso penal argentino.

{ATTRIBUTION_METHOD_NOTE}"""
        )
    return normalize_spanish(
        f"""CONCLUSIÓN TÉCNICO-JURÍDICA SOBRE IMPOSIBILIDAD DE ATRIBUCIÓN DEL CIBERATAQUE

Del análisis técnico-forense efectuado sobre los registros de acceso, logs del servidor, metadatos de conexión, indicadores de compromiso, direcciones IP, huellas de malware, trazas de red, artefactos de sistema y repositorios de eventos disponibles, corresponde concluir que no se han reunido elementos técnicos suficientes para atribuir de manera concluyente el ciberataque investigado a una persona física, grupo organizado, entidad u organización determinada.

La investigación permitió confirmar la existencia material de un incidente de seguridad. Sin embargo, la información disponible no permite establecer con certeza quién ejecutó la intrusión, quién la ordenó ni qué persona física controlaba efectivamente la infraestructura utilizada.

La sola existencia de una dirección IP, alias no verificado, URL, anuncio, perfil, cuenta digital o infraestructura técnica, sin correlación suficiente con identidad civil, dispositivo físico, credenciales personales, registros de pago, geolocalización, artefactos locales u otros elementos externos, no resulta bastante para sostener una atribución penal individual.

Desde el punto de vista jurídico penal, la materialidad del hecho podría resultar compatible, en abstracto, con figuras tales como estafa, defraudación mediante manipulación informática, acceso ilegítimo, violación de datos personales o infracciones conexas, según la prueba que eventualmente se incorpore. No obstante, una cosa es acreditar la existencia de un incidente informático y otra distinta es atribuirlo penalmente a una persona determinada.

En consecuencia, la evidencia actualmente disponible permite sostener la ocurrencia de un incidente compatible con phishing/fraude digital, pero no permite afirmar con grado suficiente de certeza técnico-jurídica la autoría material o intelectual de una persona física determinada.

Desde la perspectiva procesal, corresponde mantener abierta la línea investigativa, preservar la totalidad de la evidencia digital recolectada, requerir informes ampliatorios a proveedores de conectividad, plataformas, servicios de correo, registradores de dominio, entidades financieras, billeteras virtuales, exchanges o servicios de alojamiento, así como realizar nuevas pericias sobre dispositivos, cuentas o sistemas vinculados que pudieran incorporarse en el futuro.

Por todo lo expuesto, este informe concluye que no se logró determinar la atribución del ciberataque a una persona física, grupo u organización específica, sin perjuicio de la existencia del hecho investigado y de la posibilidad de que futuras medidas probatorias permitan fortalecer, descartar o redireccionar las hipótesis de autoría actualmente consideradas.

{ATTRIBUTION_METHOD_NOTE}"""
    )


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
        "Código Penal argentino: posible relevancia penal preliminar según conducta, dolo, perjuicio y medios empleados. Fuente pendiente de verificación.",
        "Ley 26.388: marco argentino de delitos informáticos incorporado al Código Penal. Fuente pendiente de verificación.",
        "Reglas procesales sobre prueba digital y cadena de custodia aplicables según jurisdicción. Fuente pendiente de verificación.",
    ]
    if any(term in incident for term in ["phishing", "fraude", "cripto", "transferencia", "suplantación"]):
        basis.append("Fraude informático o maniobra defraudatoria digital: corresponde analizar ardid, error, disposición patrimonial y perjuicio económico. Fuente pendiente de verificación.")
    if any(term in incident for term in ["acceso", "ransomware", "daño informático", "filtración"]):
        basis.append("Acceso no autorizado, afectación de sistemas, datos o disponibilidad: requiere vincular logs, hashes, trazabilidad y preservación de evidencia. Fuente pendiente de verificación.")
    if any(term in incident for term in ["datos", "filtración", "identidad"]):
        basis.append("Ley 25.326 de Protección de Datos Personales: analizar tratamiento, exposición, deberes de seguridad y potencial afectación de titulares. Fuente pendiente de verificación.")
    if any(term in incident for term in ["consumidor", "banco", "fintech", "exchange", "plataforma", "cripto"]):
        basis.append("Ley 24.240 de Defensa del Consumidor: revisar relación de consumo, deber de seguridad, información y trato digno si intervienen proveedores digitales. Fuente pendiente de verificación.")
    if any(term in incident for term in ["cripto", "blockchain", "wallet", "transferencia"]):
        basis.append("Blockchain y criptoactivos: la trazabilidad técnica puede aportar compatibilidad económica, pero no acredita por sí sola identidad personal del autor. Fuente pendiente de verificación.")
    if any(term in incident for term in ["deepfake", "ia"]):
        basis.append("Engaño habilitado por IA/deepfake: analizar autenticidad, manipulación, inducción a error, daño y límites técnicos de detección. Fuente pendiente de verificación.")
    return basis


def polish_report_markdown(report: Report) -> str:
    case = report.case
    markdown = report.markdown_content or ""
    replacements = {
        "queda probado": "la evidencia disponible permite sostener preliminarmente",
        "sin dudas": "con el alcance y limitaciones indicadas",
        "el atacante fue": "el acceso o conducta analizada resulta compatible con",
        "demuestra que": "resulta compatible con",
        "fue culpable": "podría tener relevancia jurídica, sujeto a validación profesional",
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
    ) or "- No hay fuentes legales manuales cargadas. Toda cita queda como fuente pendiente de verificación."

    automatic_block = f"""
## Encuadre automático IA para revisión humana

### Tipo de cibercrimen analizado

El caso se encuadra preliminarmente como **{case.incident_type}**. Esta clasificación se justifica por la descripción del caso, los datos técnicos cargados, la evidencia preservada y los hallazgos registrados. Al momento de esta revisión existen {evidence_count} evidencias y {finding_count} hallazgos vinculados al caso.

### Justificación técnico-jurídica

La línea argumental defendible no salta de dato técnico a conclusión jurídica. Primero identifica datos técnicos, luego evidencia preservada, después hallazgos verificables, hipótesis investigativas y finalmente conclusiones preliminares. Con ese alcance, la evidencia resulta compatible con un incidente digital que podría tener relevancia penal, civil, probatoria, económica y, según el caso, de consumo o protección de datos personales.

### Normativa argentina orientativa

{legal_basis}

### Fuentes legales cargadas manualmente

{legal_loaded}

### Enfoque para competencia o exposición académica

Para una competencia, jurado o audiencia simulada, la teoría del caso debe presentarse así: el incidente se describe de forma cronológica; la evidencia clave se muestra con su hash o estado de integridad; los hallazgos se expresan en lenguaje probabilístico; las hipótesis alternativas se reconocen; el daño económico estimado se informa como **{damage_total:.2f} ARS** sujeto a fórmula, fuente y validación; y la conclusión se formula como jurídicamente defendible, no como atribución penal definitiva.

### Advertencia de no invención

Este encuadre automático no inventa jurisprudencia, doctrina ni citas. Cuando no hay fuente cargada o verificada, se conserva la leyenda **Fuente pendiente de verificación**.
"""

    marker = "## Encuadre automático IA para revisión humana"
    if marker in polished:
        polished = polished.split(marker)[0].rstrip() + "\n\n" + automatic_block.strip() + "\n"
    else:
        polished = polished.rstrip() + "\n\n" + automatic_block.strip() + "\n"

    return normalize_spanish(polished)

