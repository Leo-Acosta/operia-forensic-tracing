from dataclasses import dataclass
from datetime import date

import requests
from sqlalchemy.orm import Session

from operia.legal_knowledge.models import LegalArticle, LegalSource


@dataclass(frozen=True)
class LegalArticleSeed:
    source_title: str
    code: str
    article_number: str
    subsection: str
    title: str
    text: str
    objective_elements: str
    subjective_elements: str
    evidentiary_requirements: str
    official_url: str


LEGAL_ARTICLE_SEEDS = [
    LegalArticleSeed(
        "Codigo Penal argentino",
        "CP",
        "172",
        "",
        "Estafa",
        "Figura base de defraudacion mediante ardid o engano con perjuicio patrimonial.",
        "Ardid o engano, error, disposicion patrimonial, perjuicio y nexo causal.",
        "Dolo defraudatorio y finalidad patrimonial.",
        "Comunicaciones, trazabilidad de pagos, registros bancarios, capturas, identidad digital, timeline del engano.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11179-16546/actualizacion",
    ),
    LegalArticleSeed(
        "Codigo Penal argentino",
        "CP",
        "153 bis",
        "",
        "Acceso ilegitimo a sistema o dato informatico",
        "Acceso sin debida autorizacion a un sistema o dato informatico de acceso restringido.",
        "Acceso, ausencia de autorizacion, sistema o dato informatico, restriccion de acceso.",
        "Conocimiento de la falta de autorizacion y voluntad de acceder.",
        "Logs, IPs, usuarios, timestamps, permisos, trazabilidad de sesion, preservacion de integridad.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11179-16546/actualizacion",
    ),
    LegalArticleSeed(
        "Codigo Penal argentino",
        "CP",
        "155",
        "",
        "Publicacion indebida de comunicaciones privadas",
        "Publicacion indebida de correspondencia o comunicacion no destinada a publicidad con posible perjuicio.",
        "Posesion o acceso a comunicacion privada, publicacion indebida, perjuicio real o potencial.",
        "Conocimiento de privacidad y voluntad de publicar indebidamente.",
        "Capturas, URLs, timestamps, preservacion de contenido, origen de publicacion, hash y contexto de privacidad.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11179-16546/actualizacion",
    ),
    LegalArticleSeed(
        "Codigo Penal argentino",
        "CP",
        "173",
        "16",
        "Defraudacion mediante manipulacion informatica",
        "Defraudacion mediante tecnica de manipulacion informatica que altere el normal funcionamiento de un sistema o transmision de datos.",
        "Manipulacion informatica, alteracion funcional, perjuicio patrimonial o disposicion economica.",
        "Dolo de defraudar y obtener beneficio o causar perjuicio.",
        "Trazabilidad de transacciones, logs de sistema, evidencia de manipulacion, nexo causal y cuantificacion.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11179-16546/actualizacion",
    ),
    LegalArticleSeed(
        "Codigo Penal argentino",
        "CP",
        "183",
        "",
        "Dano informatico",
        "Alteracion, destruccion o inutilizacion de datos, documentos, programas o sistemas informaticos.",
        "Dano, alteracion, destruccion, inutilizacion o introduccion/distribucion de programa danino.",
        "Voluntad de danar, alterar, inutilizar o introducir elementos lesivos.",
        "Hashes antes/despues, imagen forense, logs, malware, indicadores, backups, indisponibilidad y pericia tecnica.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11179-16546/actualizacion",
    ),
    LegalArticleSeed(
        "Codigo Penal argentino",
        "CP",
        "184",
        "5/6",
        "Dano agravado sobre sistemas o datos publicos/servicios",
        "Agravantes cuando el dano informatico afecta datos, documentos, programas o sistemas publicos o servicios relevantes.",
        "Dano informatico agravado por objeto protegido, servicio publico o infraestructura critica.",
        "Dolo de danar con conocimiento del objeto o contexto afectado.",
        "Impacto operativo, criticidad del sistema, logs, continuidad del servicio, reportes de indisponibilidad y pericia.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11179-16546/actualizacion",
    ),
    LegalArticleSeed(
        "Codigo Penal argentino",
        "CP",
        "197",
        "",
        "Interrupcion o entorpecimiento de comunicaciones",
        "Interrupcion o entorpecimiento de comunicacion telegrafica, telefonica o de otra naturaleza.",
        "Interrupcion o entorpecimiento de comunicacion, impacto y nexo con conducta investigada.",
        "Voluntad de interrumpir o entorpecer la comunicacion.",
        "Registros de red, monitoreo, logs, eventos de indisponibilidad, trazabilidad tecnica y alcance del impacto.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11179-16546/actualizacion",
    ),
    LegalArticleSeed(
        "Codigo Penal argentino",
        "CP",
        "153",
        "",
        "Violacion de comunicaciones privadas",
        "Tutela de comunicaciones privadas frente a acceso, apertura, apoderamiento o supresion indebida segun el supuesto.",
        "Comunicacion privada, acceso o interferencia indebida, falta de autorizacion.",
        "Conocimiento del caracter privado e intencion de acceder o interferir.",
        "Capturas, metadatos, registros de acceso, preservacion de mensajes y pericia de dispositivos.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11179-16546/actualizacion",
    ),
    LegalArticleSeed(
        "Codigo Penal argentino",
        "CP",
        "157 bis",
        "",
        "Acceso, revelacion o alteracion de datos personales",
        "Conductas indebidas sobre bancos de datos personales o informacion protegida.",
        "Datos personales, archivo o banco de datos, acceso/revelacion/alteracion indebida.",
        "Conocimiento de la ajenidad o restriccion y voluntad de acceder, revelar o alterar.",
        "Origen de datos, titularidad, autorizaciones, logs, alcance de filtracion, resguardo de muestras.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11179-16546/actualizacion",
    ),
    LegalArticleSeed(
        "Codigo Penal argentino",
        "CP",
        "168",
        "",
        "Extorsion",
        "Exigencia mediante intimidacion para obligar a entregar, enviar, depositar o poner a disposicion bienes o valores.",
        "Intimidacion, exigencia, disposicion patrimonial o conducta forzada.",
        "Finalidad de obtener disposicion patrimonial mediante intimidacion.",
        "Mensajes extorsivos, wallets/cuentas receptoras, timeline, preservacion de comunicaciones, trazabilidad financiera.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11179-16546/actualizacion",
    ),
    LegalArticleSeed(
        "Ley 25.326 de Proteccion de Datos Personales",
        "LPDP",
        "5",
        "",
        "Consentimiento para tratamiento de datos",
        "Tratamiento de datos personales sujeto a consentimiento informado salvo excepciones legales.",
        "Dato personal, tratamiento, base legal o consentimiento, finalidad y alcance.",
        "No es una figura penal por si sola; evaluar responsabilidad administrativa/civil o relacion con delitos.",
        "Politicas de privacidad, formularios, logs de consentimiento, finalidad declarada, base de datos y acceso.",
        "https://www.argentina.gob.ar/normativa/nacional/64790/actualizacion",
    ),
    LegalArticleSeed(
        "Ley 25.326 de Proteccion de Datos Personales",
        "LPDP",
        "9",
        "",
        "Seguridad de los datos",
        "Responsables o usuarios de archivos, registros, bases o bancos de datos deben adoptar medidas tecnicas y organizativas de seguridad.",
        "Existencia de datos personales, responsable o usuario, medidas de seguridad insuficientes o incumplidas.",
        "No siempre requiere dolo penal; evaluar responsabilidad administrativa/civil segun el caso.",
        "Inventario de datos, medidas de seguridad, registros de acceso, impacto, notificaciones, contratos y politicas.",
        "https://www.argentina.gob.ar/normativa/nacional/64790/actualizacion",
    ),
    LegalArticleSeed(
        "Ley 25.326 de Proteccion de Datos Personales",
        "LPDP",
        "10",
        "",
        "Deber de confidencialidad",
        "Quienes intervienen en tratamiento de datos personales deben guardar secreto profesional incluso despues de finalizada la relacion.",
        "Intervencion en tratamiento, acceso a datos, revelacion o uso indebido, ausencia de habilitacion.",
        "Conocimiento del deber de confidencialidad y conducta de revelacion o uso indebido.",
        "Roles de acceso, contratos, politicas internas, logs, destinatarios, evidencia de divulgacion.",
        "https://www.argentina.gob.ar/normativa/nacional/64790/actualizacion",
    ),
    LegalArticleSeed(
        "Ley 25.326 de Proteccion de Datos Personales",
        "LPDP",
        "11",
        "",
        "Cesion de datos",
        "Cesion de datos personales condicionada a interes legitimo, consentimiento y finalidad compatible segun corresponda.",
        "Cesion, destinatario, finalidad, consentimiento/base legal y compatibilidad.",
        "Evaluacion de responsabilidad por transferencia indebida, sin inferir delito penal automaticamente.",
        "Contratos, consentimientos, logs de transferencia, destinatarios, finalidad declarada y medidas de seguridad.",
        "https://www.argentina.gob.ar/normativa/nacional/64790/actualizacion",
    ),
    LegalArticleSeed(
        "Ley 24.240 de Defensa del Consumidor",
        "LDC",
        "4",
        "",
        "Deber de informacion",
        "El proveedor debe suministrar informacion cierta, clara y detallada sobre bienes y servicios.",
        "Relacion de consumo, proveedor, informacion deficiente, impacto en decision o reclamo.",
        "Responsabilidad de consumo segun incumplimiento, sin necesidad de tipicidad penal.",
        "Contratos, terminos, reclamos, comunicaciones, capturas, tickets, respuesta del proveedor.",
        "https://www.argentina.gob.ar/normativa/nacional/638/actualizacion",
    ),
    LegalArticleSeed(
        "Ley 24.240 de Defensa del Consumidor",
        "LDC",
        "5",
        "",
        "Proteccion de salud y seguridad del consumidor",
        "Servicios y cosas deben ser suministrados de modo que no presenten peligro para salud o integridad en condiciones previsibles.",
        "Relacion de consumo, riesgo o inseguridad del servicio, previsibilidad, dano o exposicion a dano.",
        "Responsabilidad de consumo; no requiere tipicidad penal para activar deberes de seguridad.",
        "Contratos, medidas de seguridad, incidentes previos, reclamos, respuesta del proveedor y evidencia tecnica.",
        "https://www.argentina.gob.ar/normativa/nacional/638/actualizacion",
    ),
    LegalArticleSeed(
        "Ley 24.240 de Defensa del Consumidor",
        "LDC",
        "40",
        "",
        "Responsabilidad solidaria en relacion de consumo",
        "Regimen de responsabilidad por dano al consumidor derivado del riesgo o vicio de la cosa o prestacion del servicio.",
        "Relacion de consumo, dano, proveedor/es intervinientes, nexo con servicio o cosa.",
        "Responsabilidad objetiva de consumo segun supuesto; separar de responsabilidad penal.",
        "Cadena de proveedores, reclamos, terminos de servicio, evidencias del dano, nexo tecnico y medidas de mitigacion.",
        "https://www.argentina.gob.ar/normativa/nacional/638/actualizacion",
    ),
    LegalArticleSeed(
        "Codigo Civil y Comercial de la Nacion",
        "CCCN",
        "1710",
        "",
        "Deber de prevencion del dano",
        "Deber general de evitar causar dano y adoptar medidas razonables para evitar o disminuir danos.",
        "Riesgo previsible, posibilidad de prevencion, omision o insuficiencia de medidas razonables.",
        "Regimen civil preventivo; evaluar previsibilidad, razonabilidad y nexo causal.",
        "Alertas previas, controles, politicas, logs, medidas de mitigacion, respuesta al incidente.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-26994-235975/actualizacion",
    ),
    LegalArticleSeed(
        "Codigo Civil y Comercial de la Nacion",
        "CCCN",
        "1716",
        "",
        "Deber de reparar",
        "La violacion del deber de no danar o incumplimiento obligacional da lugar a reparacion.",
        "Dano, antijuridicidad o incumplimiento, factor de atribucion, nexo causal.",
        "Responsabilidad civil; no implica automaticamente responsabilidad penal.",
        "Documentacion de dano, trazabilidad del hecho, contratos, pericias, cuantificacion y causalidad.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-26994-235975/actualizacion",
    ),
    LegalArticleSeed(
        "Codigo Civil y Comercial de la Nacion",
        "CCCN",
        "1726",
        "",
        "Relacion causal",
        "Son reparables las consecuencias que tienen nexo adecuado de causalidad con el hecho productor del dano.",
        "Hecho, dano, causalidad adecuada, consecuencias inmediatas o mediatas previsibles.",
        "Evaluacion civil de causalidad; exige prudencia probatoria.",
        "Timeline, logs, pericias, documentos economicos, hipotesis alternativas y descarte de causas ajenas.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-26994-235975/actualizacion",
    ),
    LegalArticleSeed(
        "Codigo Civil y Comercial de la Nacion",
        "CCCN",
        "1737",
        "",
        "Concepto de dano",
        "Hay dano cuando se lesiona un derecho o interes no reprobado por el ordenamiento juridico.",
        "Lesion a derecho o interes legitimo, afectacion patrimonial o extrapatrimonial.",
        "Base civil para cuantificar perjuicio; requiere prueba y relacion causal.",
        "Comprobantes, valuaciones, impactos operativos, perdida de chance, costos de respuesta y pericias.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-26994-235975/actualizacion",
    ),
    LegalArticleSeed(
        "Codigo Civil y Comercial de la Nacion",
        "CCCN",
        "1740",
        "",
        "Reparacion plena",
        "La reparacion del dano debe ser plena segun alcance juridico aplicable.",
        "Dano probado, extension, rubros, causalidad y razonabilidad.",
        "Cuantificacion civil sujeta a prueba, no a estimacion automatica de IA.",
        "Rubros, facturas, costos, informes contables, evidencia tecnica y criterios de valuacion.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-26994-235975/actualizacion",
    ),
    LegalArticleSeed(
        "Ley 27.411 - Convenio de Budapest sobre Ciberdelito",
        "BUDAPEST",
        "16",
        "",
        "Conservacion rapida de datos informaticos almacenados",
        "Marco de cooperacion para preservacion rapida de datos informaticos almacenados.",
        "Necesidad de preservacion, datos informaticos almacenados, urgencia y cooperacion aplicable.",
        "Medida procesal/cooperacion; no atribuye autoria por si sola.",
        "Solicitud de preservacion, proveedor, alcance temporal, logs, identificadores, cadena de custodia.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-27411-304798/texto",
    ),
    LegalArticleSeed(
        "Ley 27.411 - Convenio de Budapest sobre Ciberdelito",
        "BUDAPEST",
        "18",
        "",
        "Orden de presentacion",
        "Marco para requerir presentacion de datos informaticos o informacion de abonado bajo condiciones legales.",
        "Dato requerido, autoridad competente, proveedor o persona obligada, necesidad y proporcionalidad.",
        "Medida procesal/cooperacion; requiere control legal de competencia y alcance.",
        "Oficios, identificadores, cuentas, IPs, logs, datos de abonado, trazabilidad y plazos de retencion.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-27411-304798/texto",
    ),
    LegalArticleSeed(
        "Codigo Procesal Penal Federal",
        "CPPF",
        "129",
        "",
        "Libertad probatoria y utilidad de prueba",
        "Referencia funcional para orientar produccion de prueba pertinente, util y controlable.",
        "Pertinencia, utilidad, legalidad, control de partes y finalidad procesal.",
        "No aplica tipicidad penal; ordena metodologia probatoria.",
        "Cadena de custodia, autorizaciones, oficios, actas, pericias, control de integridad.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-27063-239340/actualizacion",
    ),
]

INCIDENT_KEYWORDS: dict[str, list[str]] = {
    "phishing": ["172", "173", "153 bis", "4", "5"],
    "fraude": ["172", "173", "40", "1716", "1726"],
    "acceso": ["153 bis", "153", "157 bis"],
    "datos personales": ["157 bis", "5", "9", "10", "11"],
    "filtracion": ["157 bis", "9", "10", "1737"],
    "ransomware": ["168", "183", "184", "16", "18"],
    "extorsion": ["168", "16", "18"],
    "dano informatico": ["183", "184", "197"],
    "consumidor": ["4", "5", "40"],
    "cripto": ["172", "173", "16", "18"],
    "preservacion": ["16", "18", "129"],
}


def ensure_legal_articles(db: Session) -> int:
    created = 0
    updated = 0
    source_cache = {source.title: source for source in db.query(LegalSource).all()}
    for seed in LEGAL_ARTICLE_SEEDS:
        source = source_cache.get(seed.source_title)
        if not source:
            source = LegalSource(
                title=seed.source_title,
                source_type="norma",
                citation="Fuente oficial pendiente de sincronizacion",
                url=seed.official_url,
                verified=False,
            )
            db.add(source)
            db.flush()
            source_cache[source.title] = source
        exists = (
            db.query(LegalArticle)
            .filter_by(source_id=source.id, code=seed.code, article_number=seed.article_number, subsection=seed.subsection)
            .first()
        )
        if exists:
            changed = False
            for field in (
                "title",
                "text",
                "objective_elements",
                "subjective_elements",
                "evidentiary_requirements",
                "official_url",
            ):
                value = getattr(seed, field)
                if getattr(exists, field) != value:
                    setattr(exists, field, value)
                    changed = True
            if changed:
                exists.version_label = "seed-actualizado"
                exists.last_checked_at = date.today().isoformat()
                updated += 1
            continue
        db.add(
            LegalArticle(
                source_id=source.id,
                code=seed.code,
                article_number=seed.article_number,
                subsection=seed.subsection,
                title=seed.title,
                text=seed.text,
                objective_elements=seed.objective_elements,
                subjective_elements=seed.subjective_elements,
                evidentiary_requirements=seed.evidentiary_requirements,
                official_url=seed.official_url,
                version_label="seed-inicial",
                last_checked_at=date.today().isoformat(),
                active=True,
            )
        )
        created += 1
    return created + updated


def search_articles(db: Session, query: str, limit: int = 20) -> list[LegalArticle]:
    terms = [term.strip().lower() for term in query.split() if term.strip()]
    articles = db.query(LegalArticle).filter_by(active=True).all()
    if not terms:
        return articles[:limit]

    def score(article: LegalArticle) -> int:
        haystack = " ".join(
            [
                article.code,
                article.article_number,
                article.subsection,
                article.title,
                article.text,
                article.objective_elements,
                article.subjective_elements,
                article.evidentiary_requirements,
            ]
        ).lower()
        return sum(1 for term in terms if term in haystack)

    ranked = [(score(article), article) for article in articles]
    return [article for value, article in sorted(ranked, key=lambda item: item[0], reverse=True) if value > 0][:limit]


def recommend_articles_for_incident(db: Session, incident_text: str, limit: int = 12) -> list[dict]:
    text = incident_text.lower()
    wanted_numbers: set[str] = set()
    for keyword, article_numbers in INCIDENT_KEYWORDS.items():
        if keyword in text:
            wanted_numbers.update(article_numbers)
    candidates = []
    if wanted_numbers:
        candidates.extend(
            db.query(LegalArticle)
            .filter(LegalArticle.article_number.in_(wanted_numbers), LegalArticle.active.is_(True))
            .all()
        )
    candidates.extend(search_articles(db, incident_text, limit=limit * 2))
    seen: set[int] = set()
    recommendations = []
    for article in candidates:
        if article.id in seen:
            continue
        seen.add(article.id)
        recommendations.append(
            {
                "article_id": article.id,
                "reference": f"{article.code} art. {article.article_number}{' inc. ' + article.subsection if article.subsection else ''}",
                "title": article.title,
                "text": article.text,
                "why": article.objective_elements,
                "subjective_elements": article.subjective_elements,
                "evidence_needed": article.evidentiary_requirements,
                "source_url": article.official_url,
                "requires_human_review": True,
            }
        )
        if len(recommendations) >= limit:
            break
    return recommendations


def verify_source_url(url: str, timeout: int = 8) -> dict:
    if not url:
        return {"url": url, "reachable": False, "status_code": None, "error": "URL vacia"}
    try:
        response = requests.get(url, timeout=timeout)
        return {
            "url": url,
            "reachable": response.ok,
            "status_code": response.status_code,
            "content_length": len(response.text),
            "checked_at": date.today().isoformat(),
        }
    except requests.RequestException as exc:
        return {
            "url": url,
            "reachable": False,
            "status_code": None,
            "error": str(exc),
            "checked_at": date.today().isoformat(),
        }


def verify_registered_sources(db: Session, persist: bool = False) -> list[dict]:
    results = []
    sources = db.query(LegalSource).order_by(LegalSource.title).all()
    for source in sources:
        result = verify_source_url(source.url)
        result["source_id"] = source.id
        result["title"] = source.title
        if persist:
            source.verified = bool(result["reachable"])
            source.citation = "Fuente oficial verificada por URL" if source.verified else "Fuente pendiente de verificacion"
        results.append(result)
    return results
