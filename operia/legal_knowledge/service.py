from dataclasses import dataclass
from datetime import date

import requests
from sqlalchemy.orm import Session

from operia.legal_knowledge.models import LegalArticle, LegalDoctrine, LegalMapping, LegalMappingEvidence, LegalPrecedent, LegalSource


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
    probatory_limits: str = "Requiere verificación humana de hechos, fuente oficial y nexo probatorio antes de aplicar la norma."
    incident_relations: str = "Incidente digital general"
    sensitive: bool = False
    warning: str = ""


@dataclass(frozen=True)
class LegalArticleRef:
    code: str
    article_number: str
    subsection: str = ""
    role: str = "conexa"
    applicability: str = ""
    limits: str = ""
    confidence: str = "medio"


@dataclass(frozen=True)
class AttackLegalProfile:
    key: str
    label: str
    query: str
    legal_theory: str
    required_evidence: tuple[str, ...]
    recommended_measures: tuple[str, ...]
    article_refs: tuple[LegalArticleRef, ...]


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
        "Codigo Penal argentino",
        "CP",
        "169",
        "",
        "Chantaje",
        "Figura vinculada a amenazas de imputaciones, revelaciones o difusión lesiva para obtener una prestación o ventaja.",
        "Amenaza de imputación o revelación, exigencia o ventaja buscada, idoneidad intimidatoria y nexo con la conducta exigida.",
        "Voluntad de constreñir mediante amenaza y finalidad de obtener la prestación, ventaja o conducta.",
        "Mensajes completos, capturas con metadatos, identificación del canal, exigencia formulada, destinatarios y preservación del contenido amenazado.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11179-16546/actualizacion",
        "No toda amenaza reputacional configura chantaje; debe probarse exigencia, idoneidad intimidatoria y nexo causal.",
        "ransomware/extorsión; deepfake/autenticación de medios; filtración de datos",
    ),
    LegalArticleSeed(
        "Codigo Penal argentino",
        "CP",
        "149 bis",
        "",
        "Amenazas y coacción",
        "Amenazas para alarmar o amedrentar y supuestos de coacción para obligar a hacer, no hacer o tolerar algo contra la voluntad.",
        "Amenaza idónea, destinatario determinado o determinable, contexto intimidatorio y eventual conducta exigida.",
        "Conocimiento del carácter intimidatorio y voluntad de amenazar o coaccionar.",
        "Comunicaciones completas, historial de interacción, perfiles, números o cuentas, timestamps, testigos y contexto de recepción.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11179-16546/actualizacion",
        "No atribuir autoría por número, alias o IP sin corroboración independiente; distinguir amenazas genéricas de coacción concreta.",
        "ransomware/extorsión; filtración de datos; deepfake/autenticación de medios",
    ),
    LegalArticleSeed(
        "Codigo Penal argentino",
        "CP",
        "128",
        "",
        "Representaciones sexuales de menores",
        "Norma penal sensible vinculada con producción, financiación, ofrecimiento, comercialización, publicación, facilitación, divulgación o tenencia de representaciones sexuales de menores según el supuesto legal.",
        "Material o representación alcanzada por la norma, intervención típica, sujeto menor de edad o apariencia normativa aplicable y soporte o medio utilizado.",
        "Dolo de producir, difundir, facilitar, comercializar, distribuir, adquirir o poseer según el supuesto.",
        "Preservación mínima y controlada, hash, ubicación, URL o identificador, acta de hallazgo, cadena de custodia y derivación a autoridad competente sin replicar ni exhibir material.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11179-16546/actualizacion",
        "Norma sensible: no descargar, reproducir, describir de modo innecesario ni mostrar material; activar preservación legal mínima y revisión profesional inmediata.",
        "norma sensible; deepfake/autenticación de medios; filtración de datos",
        True,
        "Contenido sensible con menores: OPERIA solo registra referencia normativa y medidas de preservación mínima. No debe exponerse material ni inferirse autoría sin intervención competente.",
    ),
    LegalArticleSeed(
        "Codigo Penal argentino",
        "CP",
        "131",
        "",
        "Contacto con menor por medios tecnológicos",
        "Contacto con persona menor de edad mediante comunicaciones electrónicas, telecomunicaciones o tecnologías de transmisión de datos con finalidad vinculada a delitos contra la integridad sexual.",
        "Contacto tecnológico con menor, canal utilizado, destinatario y finalidad típica que debe ser acreditada por el contexto.",
        "Finalidad específica exigida por la norma, además del conocimiento del carácter del contacto.",
        "Mensajes completos, perfiles, datos de cuenta, timestamps, preservación del dispositivo, denuncias, contexto conversacional y resguardo especializado.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11179-16546/actualizacion",
        "Norma sensible: requiere análisis especializado; no basta una conversación aislada sin finalidad típica y evidencia contextual suficiente.",
        "norma sensible; acceso ilegítimo; filtración de datos",
        True,
        "Contenido sensible con menores: evitar exposición de datos personales y derivar a autoridad competente o profesional especializado.",
    ),
    LegalArticleSeed(
        "Codigo Penal argentino",
        "CP",
        "293",
        "",
        "Falsedad documental",
        "Inserción o creación de declaraciones falsas en instrumento público o privado con aptitud para producir perjuicio según el supuesto legal.",
        "Documento o instrumento, falsedad material o ideológica según corresponda, aptitud probatoria o jurídica y perjuicio posible.",
        "Conocimiento de la falsedad y voluntad de documentar o insertar datos falsos con aptitud lesiva.",
        "Documento original o copia íntegra, metadatos, cadena de custodia, origen, firmas, certificados, logs de emisión y pericia documental/digital.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11179-16546/actualizacion",
        "La mera inconsistencia de metadatos no acredita falsedad; se requiere análisis del documento, autoría y aptitud jurídica.",
        "falsedad documental digital; deepfake/autenticación de medios; phishing/fraude digital",
    ),
    LegalArticleSeed(
        "Codigo Penal argentino",
        "CP",
        "296",
        "",
        "Uso de documento falso",
        "Uso de documento o certificado falso o adulterado, con remisión a la escala penal correspondiente según el documento.",
        "Documento falso o adulterado, uso concreto, conocimiento de la falsedad y aptitud para producir efectos jurídicos.",
        "Dolo de usar el documento con conocimiento de su falsedad.",
        "Registro del uso, destinatario, sistema o trámite, documento preservado, metadatos, firmas/certificados y trazabilidad de carga o envío.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11179-16546/actualizacion",
        "Debe probarse uso y conocimiento; recibir o almacenar un archivo falso no equivale automáticamente a usarlo.",
        "falsedad documental digital; phishing/fraude digital",
    ),
    LegalArticleSeed(
        "Codigo Penal argentino",
        "CP",
        "109",
        "",
        "Calumnias",
        "Imputación falsa a una persona determinada de la comisión de un delito concreto que dé lugar a acción pública.",
        "Imputación delictiva concreta, falsedad, persona determinada o determinable y difusión o comunicación atribuible.",
        "Conocimiento de la falsedad o desprecio por la verdad según evaluación jurídica aplicable.",
        "Publicación o mensaje completo, URL, fecha, autoría de cuenta, alcance, capturas certificables y contexto de la imputación.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11179-16546/actualizacion",
        "Distinguir opinión, crítica, sátira o denuncia de imputación delictiva falsa; no atribuir autoría por perfil sin corroboración.",
        "deepfake/autenticación de medios; filtración de datos",
    ),
    LegalArticleSeed(
        "Codigo Penal argentino",
        "CP",
        "110",
        "",
        "Injurias",
        "Deshonra o desacreditación de una persona mediante expresiones lesivas, con límites constitucionales y excepciones legales.",
        "Expresión lesiva, persona determinada o determinable, difusión o comunicación y afectación al honor.",
        "Voluntad de injuriar o conocimiento del carácter lesivo según el contexto.",
        "Contenido completo, contexto de publicación, alcance, autoría de cuenta, timestamps, preservación de URL y evidencia de impacto.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11179-16546/actualizacion",
        "No toda expresión ofensiva es típica; evaluar interés público, contexto, veracidad, opinión y estándares de libertad de expresión.",
        "deepfake/autenticación de medios; filtración de datos",
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
        "51-53",
        "",
        "Dignidad, imagen, voz e identidad",
        "Reglas civiles sobre inviolabilidad de la persona humana, afectaciones a la dignidad e imagen, voz o identidad.",
        "Persona identificada o identificable, captación/uso/exposición de imagen, voz o identidad, falta de consentimiento o causa de justificación y afectación dignitaria.",
        "No es tipo penal; evaluar conocimiento del uso no autorizado, finalidad lesiva o responsabilidad civil según el caso.",
        "Archivo original, metadatos, publicación, consentimiento o ausencia de este, alcance de difusión, comparación biométrica o técnica y registro de daños.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-26994-235975/actualizacion",
        "No permite atribuir autoría técnica; requiere demostrar uso, identificación, falta de autorización y daño o afectación.",
        "deepfake/autenticación de medios; filtración de datos; falsedad documental digital",
    ),
    LegalArticleSeed(
        "Ley 11.723 de Propiedad Intelectual",
        "LPI",
        "1",
        "",
        "Obras protegidas",
        "Reconoce protección sobre obras científicas, literarias y artísticas, incluyendo expresiones audiovisuales, fotográficas, fonográficas o digitales según corresponda.",
        "Obra protegida, titularidad o legitimación, reproducción/uso/comunicación y falta de autorización o licencia aplicable.",
        "No es tipo penal por sí sola en todo caso; evaluar conocimiento del uso y finalidad según reclamo civil o penal específico.",
        "Obra original, registro o prueba de titularidad, licencia, publicación impugnada, hashes, metadatos, URLs y alcance de uso.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11723-42755/actualizacion",
        "Distinguir infracción autoral de uso legítimo, cita, parodia, autorización o material no protegido; no atribuir autoría sin trazabilidad.",
        "deepfake/autenticación de medios; falsedad documental digital; phishing/fraude digital",
    ),
    LegalArticleSeed(
        "Ley 11.723 de Propiedad Intelectual",
        "LPI",
        "71",
        "",
        "Defraudación a derechos de propiedad intelectual",
        "Remisión penal para quien defraude derechos de propiedad intelectual reconocidos por la ley.",
        "Derecho de propiedad intelectual protegido, conducta defraudatoria, ausencia de autorización y perjuicio o afectación relevante.",
        "Dolo de defraudar derechos de propiedad intelectual.",
        "Titularidad, licencia, obra original, copias o publicaciones, trazabilidad de distribución, alcance y cuantificación del perjuicio.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11723-42755/actualizacion",
        "No convertir automáticamente todo uso de imagen, audio o contenido en delito; exige derecho protegido, defraudación y prueba suficiente.",
        "deepfake/autenticación de medios; falsedad documental digital",
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

ATTACK_PROFILES: dict[str, AttackLegalProfile] = {
    "phishing": AttackLegalProfile(
        key="phishing",
        label="Phishing / fraude digital",
        query="phishing fraude acceso datos consumidor",
        legal_theory=(
            "Maniobra defraudatoria digital basada en ardid, engaño o suplantación para captar datos, credenciales "
            "o provocar una disposición patrimonial perjudicial."
        ),
        required_evidence=(
            "Capturas del anuncio, perfil, enlace, correo, chat o comunicación falsa.",
            "URL, dominio, cuenta, alias, wallet, CBU/CVU o identificador receptor.",
            "Comprobantes de pago, transferencias, cargos o desplazamiento patrimonial.",
            "Logs de acceso, cabeceras, metadatos y timestamps preservados.",
            "Respuestas de plataformas, bancos, fintechs, registradores o proveedores.",
        ),
        recommended_measures=(
            "Preservar comunicaciones completas con fecha, hora, URL y usuario visible.",
            "Requerir información de titularidad y trazabilidad a plataformas y entidades financieras.",
            "Correlacionar pagos, sesiones, IPs, dispositivos y cuentas receptoras.",
            "Evitar atribución personal si solo existen URL, alias o IP sin corroboración externa.",
        ),
        article_refs=(
            LegalArticleRef(
                "CP",
                "172",
                role="principal",
                applicability="Figura base cuando el engaño produce error, disposición patrimonial y perjuicio.",
                limits="Requiere probar ardid, error, perjuicio y nexo causal; no basta la sospecha de cuenta falsa.",
                confidence="alto",
            ),
            LegalArticleRef(
                "CP",
                "173",
                "16",
                "conexa",
                "Relevante si la defraudación se ejecuta mediante manipulación informática o transmisión de datos.",
                "Debe acreditarse la manipulación o intervención informática concreta.",
                "medio",
            ),
            LegalArticleRef(
                "CP",
                "153 bis",
                role="conexa",
                applicability="Relevante si hubo acceso no autorizado a cuenta, sistema o dato de acceso restringido.",
                limits="No se configura por el mero contacto con la víctima sin acceso restringido probado.",
                confidence="medio",
            ),
            LegalArticleRef(
                "LPDP",
                "5",
                role="complementaria",
                applicability="Aplicable si se captaron o trataron datos personales sin base válida.",
                limits="Es un plano de protección de datos, no atribuye por sí solo autoría penal.",
            ),
            LegalArticleRef(
                "LDC",
                "4",
                role="complementaria",
                applicability="Útil si intervino una relación de consumo o plataforma con deber de información.",
                limits="No sustituye la calificación penal; orienta deberes de información y reclamos conexos.",
            ),
        ),
    ),
    "fraude digital": AttackLegalProfile(
        key="fraude digital",
        label="Fraude digital",
        query="fraude estafa manipulacion informatica consumidor",
        legal_theory="Defraudación patrimonial ejecutada o facilitada por medios digitales.",
        required_evidence=("Comprobantes de operación.", "Comunicaciones.", "Trazabilidad financiera.", "Identificadores técnicos."),
        recommended_measures=("Preservar pagos y comunicaciones.", "Solicitar titularidad de cuentas receptoras.", "Correlacionar timeline."),
        article_refs=(
            LegalArticleRef("CP", "172", role="principal", applicability="Base de estafa si hay ardid, error y perjuicio.", limits="Exige nexo causal probado.", confidence="alto"),
            LegalArticleRef("CP", "173", "16", "conexa", "Relevante por manipulación informática.", "Debe probarse intervención informática.", "medio"),
            LegalArticleRef("LDC", "40", role="complementaria", applicability="Responsabilidad de consumo si corresponde.", limits="Separar responsabilidad civil/consumo de autoría penal."),
            LegalArticleRef("CCCN", "1716", role="complementaria", applicability="Base civil de reparación si hay daño probado.", limits="Requiere causalidad y cuantificación."),
        ),
    ),
    "ransomware": AttackLegalProfile(
        key="ransomware",
        label="Ransomware",
        query="ransomware extorsion dano informatico preservacion",
        legal_theory="Bloqueo, cifrado, exfiltración o amenaza sobre sistemas/datos para exigir pago o causar daño.",
        required_evidence=("Muestra o hash del artefacto.", "Nota extorsiva.", "Wallet/cuenta exigida.", "Logs de ejecución.", "Backups e impacto."),
        recommended_measures=("Aislar sistemas.", "Preservar imagen forense.", "Registrar IOCs.", "Pedir preservación de datos a proveedores."),
        article_refs=(
            LegalArticleRef("CP", "168", role="principal", applicability="Principal si existe exigencia intimidatoria de pago o entrega.", limits="Requiere intimidación y exigencia verificable.", confidence="alto"),
            LegalArticleRef("CP", "183", role="conexa", applicability="Daño informático por alteración, inutilización o cifrado.", limits="Debe probarse afectación técnica concreta."),
            LegalArticleRef("CP", "184", "5/6", "conexa", "Agravantes si afecta sistemas públicos, servicios o datos especialmente protegidos.", "Depende del objeto afectado."),
            LegalArticleRef("BUDAPEST", "16", role="procesal", applicability="Preservación rápida de datos informáticos almacenados.", limits="Medida de cooperación, no tipo penal."),
            LegalArticleRef("BUDAPEST", "18", role="procesal", applicability="Orden de presentación de datos o información de abonado.", limits="Requiere autoridad competente y alcance definido."),
        ),
    ),
    "acceso ilegitimo": AttackLegalProfile(
        key="acceso ilegitimo",
        label="Acceso ilegítimo",
        query="acceso ilegitimo sistema dato informatico",
        legal_theory="Ingreso sin autorización a sistema, cuenta o dato informático de acceso restringido.",
        required_evidence=("Logs de autenticación.", "Timestamps.", "Usuarios afectados.", "IPs/sesiones.", "Política de permisos."),
        recommended_measures=("Preservar logs originales.", "Verificar permisos.", "Correlacionar IP, usuario y dispositivo.", "Solicitar datos de abonado si corresponde."),
        article_refs=(
            LegalArticleRef("CP", "153 bis", role="principal", applicability="Tipo central para acceso sin autorización a sistema o dato restringido.", limits="Exige restricción de acceso y falta de autorización.", confidence="alto"),
            LegalArticleRef("CP", "153", role="conexa", applicability="Puede aplicar si se afectan comunicaciones privadas.", limits="Depende del objeto comunicacional."),
            LegalArticleRef("CP", "157 bis", role="conexa", applicability="Relevante si se accede o altera banco de datos personales.", limits="Requiere banco/archivo de datos y conducta específica."),
        ),
    ),
    "dano informatico": AttackLegalProfile(
        key="dano informatico",
        label="Daño informático",
        query="dano informatico sistemas datos",
        legal_theory="Alteración, destrucción, inutilización o afectación de datos, programas o sistemas.",
        required_evidence=("Imagen forense.", "Hashes antes/después.", "Logs.", "Artefactos maliciosos.", "Impacto operativo."),
        recommended_measures=("Preservar estado afectado.", "Comparar integridad.", "Documentar indisponibilidad.", "Cuantificar daño."),
        article_refs=(
            LegalArticleRef("CP", "183", role="principal", applicability="Figura base de daño informático.", limits="Debe acreditarse daño o alteración concreta.", confidence="alto"),
            LegalArticleRef("CP", "184", "5/6", "conexa", "Agravantes por objeto o servicio afectado.", "Depende de infraestructura y consecuencias."),
            LegalArticleRef("CP", "197", role="conexa", applicability="Si hay interrupción o entorpecimiento de comunicaciones.", limits="Requiere impacto comunicacional probado."),
        ),
    ),
    "filtracion de datos": AttackLegalProfile(
        key="filtracion de datos",
        label="Filtración de datos",
        query="filtracion datos personales confidencialidad",
        legal_theory="Acceso, exposición, revelación o tratamiento indebido de datos personales o información confidencial.",
        required_evidence=("Muestra de datos expuestos.", "Origen del repositorio.", "Logs de acceso.", "Titularidad de datos.", "Alcance de difusión."),
        recommended_measures=("Minimizar exposición de muestras.", "Preservar evidencia con hash.", "Notificar según política aplicable.", "Relevar titulares afectados."),
        article_refs=(
            LegalArticleRef("CP", "157 bis", role="principal", applicability="Relevante para acceso, revelación o alteración de datos personales.", limits="Exige banco/archivo o supuesto protegido.", confidence="alto"),
            LegalArticleRef("LPDP", "9", role="complementaria", applicability="Evalúa deberes de seguridad de datos.", limits="Plano administrativo/civil salvo conexión penal."),
            LegalArticleRef("LPDP", "10", role="complementaria", applicability="Deber de confidencialidad.", limits="Depende del rol de quien accedió o divulgó."),
            LegalArticleRef("LPDP", "11", role="complementaria", applicability="Cesión de datos.", limits="Requiere analizar destinatarios y base legal."),
        ),
    ),
    "extorsion": AttackLegalProfile(
        key="extorsion",
        label="Extorsión",
        query="extorsion intimidacion datos ransomware",
        legal_theory="Exigencia intimidatoria para obligar a entregar bienes, valores, datos o realizar una conducta.",
        required_evidence=("Mensaje extorsivo.", "Exigencia concreta.", "Cuenta/wallet destino.", "Plazos/amenazas.", "Canal de contacto."),
        recommended_measures=("Preservar mensajes completos.", "Documentar exigencias.", "Trazar cuentas receptoras.", "Evitar interacción no controlada."),
        article_refs=(
            LegalArticleRef("CP", "168", role="principal", applicability="Tipo central si existe intimidación y exigencia.", limits="Debe probarse la amenaza/exigencia y finalidad patrimonial.", confidence="alto"),
            LegalArticleRef("BUDAPEST", "16", role="procesal", applicability="Preservación rápida de datos.", limits="No atribuye autoría."),
            LegalArticleRef("BUDAPEST", "18", role="procesal", applicability="Orden de presentación.", limits="Requiere autoridad y alcance."),
        ),
    ),
    "otro": AttackLegalProfile(
        key="otro",
        label="Otro incidente informático",
        query="incidente informatico evidencia digital",
        legal_theory="Perfil general para incidentes informáticos que requieren clasificación jurídica posterior.",
        required_evidence=("Descripción del hecho.", "Evidencia digital preservada.", "Cadena de custodia.", "Timeline.", "Impacto."),
        recommended_measures=("Completar clasificación.", "Preservar evidencia.", "Evitar atribución prematura.", "Consultar normas por hechos concretos."),
        article_refs=(LegalArticleRef("CPPF", "129", role="procesal", applicability="Orienta pertinencia y utilidad probatoria.", limits="No define tipicidad penal."),),
    ),
}

ATTACK_PROFILES.update(
    {
        "deepfake": AttackLegalProfile(
            key="deepfake",
            label="Deepfake / autenticación de medios",
            query="deepfake autenticación medios imagen voz identidad propiedad intelectual",
            legal_theory="Uso, alteración o difusión de imagen, voz, identidad o contenido audiovisual sintético que puede afectar dignidad, honor, derechos personalísimos o propiedad intelectual.",
            required_evidence=("Archivo original o copia íntegra preservada con hash.", "Metadatos, plataforma, URL, fecha de publicación y alcance.", "Comparación técnica de autenticidad, edición, síntesis o manipulación.", "Consentimiento, licencia o evidencia de ausencia de autorización.", "Contexto de daño, suplantación, amenaza, imputación o uso económico."),
            recommended_measures=("Preservar archivo y publicación sin recomprimir.", "Documentar cadena de custodia y herramientas de autenticación usadas.", "Separar autenticidad técnica, afectación civil y eventual delito.", "No atribuir autoría por estilo, voz o similitud sin trazabilidad técnica y corroboración externa."),
            article_refs=(
                LegalArticleRef("CCCN", "51-53", role="principal", applicability="Base civil para imagen, voz, identidad, dignidad y consentimiento.", limits="No atribuye autoría; exige identificación, uso y afectación.", confidence="alto"),
                LegalArticleRef("LPI", "1", role="principal", applicability="Relevante si el deepfake usa obra protegida, audio, imagen o material audiovisual.", limits="Evaluar titularidad, licencia, excepción o autorización.", confidence="alto"),
                LegalArticleRef("LPI", "71", role="conexa", applicability="Puede aplicar si existe defraudación a derechos de propiedad intelectual.", limits="No todo uso no autorizado configura delito."),
                LegalArticleRef("CP", "109", role="conexa", applicability="Si el contenido imputa falsamente un delito concreto.", limits="Distinguir opinión, sátira, denuncia y falsedad atribuible."),
                LegalArticleRef("CP", "110", role="conexa", applicability="Si el contenido afecta honor o reputación.", limits="Requiere análisis de contexto y libertad de expresión."),
                LegalArticleRef("CP", "293", role="conexa", applicability="Si el medio falso se usa como documento con aptitud jurídica.", limits="No toda imagen manipulada es documento falso."),
            ),
        ),
        "blockchain": AttackLegalProfile(
            key="blockchain",
            label="Blockchain / criptoactivos",
            query="blockchain criptoactivos wallet fraude estafa extorsión manipulación informática",
            legal_theory="Incidentes con wallets, transacciones, smart contracts o criptoactivos que pueden involucrar estafa, manipulación informática o extorsión.",
            required_evidence=("TXID, address, red, fecha, monto y token involucrado.", "Wallets de origen/destino y trazabilidad on-chain.", "Comunicaciones, ofertas, promesas, notas extorsivas o instrucciones.", "Exchange, KYC, IPs, sesiones y datos de retiro cuando existan.", "Nexo entre engaño, manipulación, exigencia y pérdida patrimonial."),
            recommended_measures=("Preservar TXID y capturas del explorador con fecha.", "Solicitar datos a exchanges o custodios por vía formal.", "Separar atribución de wallet, titularidad KYC y control real.", "No atribuir autoría personal solo por una address, cluster o exchange."),
            article_refs=(
                LegalArticleRef("CP", "172", role="principal", applicability="Estafa si hubo ardid, error, disposición patrimonial y perjuicio.", limits="Requiere nexo entre engaño y transferencia.", confidence="alto"),
                LegalArticleRef("CP", "173", "16", "principal", "Aplica si hubo manipulación informática, smart contract o transmisión de datos con perjuicio.", "Debe probarse la manipulación técnica concreta.", "medio"),
                LegalArticleRef("CP", "168", role="principal", applicability="Aplica si se exigió transferencia bajo intimidación.", limits="Requiere amenaza/exigencia verificable.", confidence="medio"),
                LegalArticleRef("BUDAPEST", "18", role="procesal", applicability="Orientativo para requerir datos de abonado o registros a proveedores.", limits="Requiere autoridad competente."),
            ),
        ),
        "iot": AttackLegalProfile(
            key="iot",
            label="IoT / dispositivos conectados",
            query="iot dispositivos conectados acceso ilegítimo comunicaciones daño informático",
            legal_theory="Acceso, interferencia, control remoto o afectación de dispositivos conectados, redes, datos o comunicaciones.",
            required_evidence=("Identificación del dispositivo, firmware, cuenta asociada y red.", "Logs del equipo, router, cloud del fabricante y aplicación móvil.", "Capturas de comandos, cambios, alertas, tráfico o indisponibilidad.", "Permisos, credenciales, configuración previa y propietarios.", "Impacto en datos, comunicaciones, servicio o integridad del dispositivo."),
            recommended_measures=("Preservar configuración y logs antes de resetear.", "Aislar el dispositivo si hay riesgo operativo.", "Solicitar registros al fabricante o proveedor cloud.", "No atribuir por IP local, MAC o cuenta compartida sin corroboración."),
            article_refs=(
                LegalArticleRef("CP", "153 bis", role="principal", applicability="Tipo central si hubo acceso sin autorización a sistema o dato restringido.", limits="Exige restricción y falta de autorización.", confidence="alto"),
                LegalArticleRef("CP", "183", role="principal", applicability="Daño informático si hubo alteración, inutilización o afectación de datos/sistema.", limits="Debe probarse daño técnico concreto.", confidence="medio"),
                LegalArticleRef("CP", "197", role="conexa", applicability="Si la conducta interrumpe o entorpece comunicaciones.", limits="Requiere impacto comunicacional probado.", confidence="medio"),
                LegalArticleRef("CP", "153", role="conexa", applicability="Si se accedió o interceptó comunicación privada.", limits="Depende del objeto comunicacional."),
            ),
        ),
        "falsedad documental digital": AttackLegalProfile(
            key="falsedad documental digital",
            label="Falsedad documental digital",
            query="falsedad documental digital documento falso uso certificado firma",
            legal_theory="Creación, alteración o uso de documentos digitales falsos con aptitud probatoria o efectos jurídicos.",
            required_evidence=("Documento íntegro.", "Metadatos.", "Firmas o certificados.", "Origen y canal de envío.", "Registro de uso y destinatario."),
            recommended_measures=("Preservar original y hash.", "Verificar firma/certificado.", "Solicitar logs del sistema emisor.", "No concluir falsedad solo por metadatos incompletos."),
            article_refs=(
                LegalArticleRef("CP", "293", role="principal", applicability="Figura central ante falsedad documental.", limits="Requiere aptitud jurídica y falsedad probada.", confidence="alto"),
                LegalArticleRef("CP", "296", role="principal", applicability="Aplica si el documento falso fue usado.", limits="Requiere uso y conocimiento de falsedad.", confidence="alto"),
                LegalArticleRef("CCCN", "51-53", role="conexa", applicability="Si se afectó identidad o imagen en el documento.", limits="Plano civil/personalísimo."),
                LegalArticleRef("LPI", "1", role="conexa", applicability="Si se usaron obras o piezas protegidas.", limits="Evaluar titularidad y autorización."),
            ),
        ),
    }
)

ATTACK_PROFILES["acceso ilegítimo"] = ATTACK_PROFILES["acceso ilegitimo"]
ATTACK_PROFILES["daño informatico"] = ATTACK_PROFILES["dano informatico"]
ATTACK_PROFILES["daño informático"] = ATTACK_PROFILES["dano informatico"]
ATTACK_PROFILES["phishing / fraude digital"] = ATTACK_PROFILES["phishing"]
ATTACK_PROFILES["deepfake/autenticación de medios"] = ATTACK_PROFILES["deepfake"]
ATTACK_PROFILES["autenticación de medios"] = ATTACK_PROFILES["deepfake"]
ATTACK_PROFILES["blockchain/criptoactivos"] = ATTACK_PROFILES["blockchain"]
ATTACK_PROFILES["criptoactivos"] = ATTACK_PROFILES["blockchain"]
ATTACK_PROFILES["iot/dispositivos conectados"] = ATTACK_PROFILES["iot"]
ATTACK_PROFILES["filtración de datos"] = ATTACK_PROFILES["filtracion de datos"]

INCIDENT_KEYWORDS: dict[str, list[str]] = {
    "phishing": ["172", "173", "153 bis", "4", "5"],
    "fraude": ["172", "173", "40", "1716", "1726"],
    "acceso": ["153 bis", "153", "157 bis"],
    "datos personales": ["157 bis", "5", "9", "10", "11"],
    "filtracion": ["157 bis", "9", "10", "1737"],
    "ransomware": ["168", "183", "184", "16", "18"],
    "extorsion": ["168", "16", "18"],
    "dano informatico": ["183", "184", "197"],
    "daño informático": ["183", "184", "197"],
    "deepfake": ["51-53", "1", "71", "109", "110", "293"],
    "autenticacion": ["51-53", "1", "71", "109", "110", "293"],
    "autenticación": ["51-53", "1", "71", "109", "110", "293"],
    "blockchain": ["172", "173", "168", "18"],
    "criptoactivos": ["172", "173", "168", "18"],
    "iot": ["153 bis", "183", "197", "153"],
    "falsedad documental": ["293", "296", "51-53", "1"],
    "consumidor": ["4", "5", "40"],
    "cripto": ["172", "173", "16", "18"],
    "preservacion": ["16", "18", "129"],
}

LEGAL_ELEMENT_CHECKLISTS: dict[tuple[str, str, str], tuple[str, ...]] = {
    ("CP", "172", ""): (
        "Ardid o engaño",
        "Error de la víctima",
        "Disposición patrimonial",
        "Perjuicio patrimonial",
        "Nexo causal",
        "Dolo defraudatorio",
    ),
    ("CP", "173", "16"): (
        "Manipulación informática",
        "Alteración del funcionamiento o transmisión de datos",
        "Perjuicio patrimonial",
        "Nexo causal",
        "Dolo defraudatorio",
    ),
    ("CP", "153 bis", ""): (
        "Sistema o dato de acceso restringido",
        "Acceso técnico verificable",
        "Falta de autorización",
        "Dolo de acceso",
    ),
    ("CP", "157 bis", ""): (
        "Dato personal o banco de datos",
        "Acceso, revelación o alteración",
        "Falta de habilitación",
        "Dolo",
    ),
    ("CP", "168", ""): (
        "Intimidación",
        "Exigencia",
        "Disposición patrimonial o conducta forzada",
        "Finalidad patrimonial",
    ),
    ("CP", "169", ""): (
        "Amenaza de imputación o revelación",
        "Exigencia o ventaja buscada",
        "Idoneidad intimidatoria",
        "Finalidad de obtener prestación o ventaja",
    ),
    ("CP", "149 bis", ""): (
        "Amenaza idónea",
        "Destinatario determinado o determinable",
        "Contexto intimidatorio",
        "Voluntad de amenazar o coaccionar",
    ),
    ("CP", "293", ""): (
        "Documento o instrumento",
        "Falsedad material o ideológica",
        "Aptitud jurídica o probatoria",
        "Conocimiento de la falsedad",
    ),
    ("CP", "296", ""): (
        "Documento falso o adulterado",
        "Uso concreto",
        "Conocimiento de falsedad",
        "Aptitud para producir efectos jurídicos",
    ),
    ("CCCN", "51-53", ""): (
        "Persona identificada o identificable",
        "Imagen, voz, identidad o dignidad afectada",
        "Falta de consentimiento o habilitación",
        "Daño o afectación verificable",
    ),
    ("LPI", "1", ""): (
        "Obra protegida",
        "Titularidad o legitimación",
        "Uso, reproducción o comunicación",
        "Ausencia de autorización o licencia",
    ),
    ("CP", "183", ""): (
        "Alteración, destrucción o inutilización",
        "Dato, programa o sistema afectado",
        "Daño verificable",
        "Dolo de dañar o alterar",
    ),
    ("LPDP", "5", ""): (
        "Dato personal",
        "Tratamiento",
        "Consentimiento o base legal",
        "Finalidad y alcance",
    ),
    ("LPDP", "9", ""): (
        "Datos personales protegidos",
        "Responsable o usuario de base",
        "Medidas técnicas y organizativas",
        "Incumplimiento o insuficiencia verificable",
    ),
    ("LDC", "4", ""): (
        "Relación de consumo",
        "Proveedor",
        "Información cierta, clara y detallada",
        "Impacto en la decisión o reclamo",
    ),
    ("LDC", "40", ""): (
        "Relación de consumo",
        "Daño",
        "Proveedor interviniente",
        "Nexo con servicio o cosa",
    ),
}

LEGAL_SEED_BY_REF = {
    (seed.code, seed.article_number, seed.subsection): seed
    for seed in LEGAL_ARTICLE_SEEDS
}


def list_attack_profiles() -> list[dict]:
    unique: dict[str, AttackLegalProfile] = {}
    for profile in ATTACK_PROFILES.values():
        unique[profile.key] = profile
    return [
        {
            "value": profile.key,
            "label": profile.label,
            "query": profile.query,
            "legal_theory": profile.legal_theory,
            "required_evidence": list(profile.required_evidence),
            "recommended_measures": list(profile.recommended_measures),
        }
        for profile in sorted(unique.values(), key=lambda item: item.label)
    ]


def get_attack_profile(incident_text: str) -> AttackLegalProfile:
    text = (incident_text or "").lower()
    for key, profile in ATTACK_PROFILES.items():
        if key in text:
            return profile
    for keyword in INCIDENT_KEYWORDS:
        if keyword in text:
            if keyword in ATTACK_PROFILES:
                return ATTACK_PROFILES[keyword]
    return ATTACK_PROFILES["otro"]


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


def get_article_by_ref(db: Session, ref: LegalArticleRef) -> LegalArticle | None:
    return (
        db.query(LegalArticle)
        .filter_by(code=ref.code, article_number=ref.article_number, subsection=ref.subsection, active=True)
        .first()
    )


def article_context(db: Session, article: LegalArticle, crime_type: str = "") -> dict:
    source = db.get(LegalSource, article.source_id) if article.source_id else None
    precedents = [
        {
            "title": item.title,
            "court_or_authority": item.court_or_authority,
            "decision_date": item.decision_date,
            "source": item.source,
            "url": item.url,
            "summary": item.summary,
            "applicable_criterion": item.applicable_criterion,
        }
        for item in db.query(LegalPrecedent)
        .filter_by(article_id=article.id, verified=True)
        .all()
        if not crime_type or crime_type.lower() in (item.related_crime_type or "").lower()
    ]
    doctrine = [
        {
            "title": item.title,
            "author": item.author,
            "publication_date": item.publication_date,
            "source": item.source,
            "url": item.url,
            "summary": item.summary,
            "applicable_criterion": item.applicable_criterion,
        }
        for item in db.query(LegalDoctrine)
        .filter_by(article_id=article.id, verified=True)
        .all()
        if not crime_type or crime_type.lower() in (item.related_crime_type or "").lower()
    ]
    return {
        "source_title": source.title if source else "",
        "source_citation": source.citation if source else "",
        "source_verified": bool(source.verified) if source else False,
        "source_url": (source.url if source and source.url else article.official_url),
        "last_checked_at": article.last_checked_at,
        "precedents": precedents,
        "doctrine": doctrine,
    }


def recommend_articles_for_incident(db: Session, incident_text: str, limit: int = 12) -> list[dict]:
    text = incident_text.lower()
    profile = get_attack_profile(incident_text)
    wanted_numbers: set[str] = set()
    for keyword, article_numbers in INCIDENT_KEYWORDS.items():
        if keyword in text:
            wanted_numbers.update(article_numbers)
    candidates = []
    profile_refs: dict[tuple[str, str, str], LegalArticleRef] = {}
    for ref in profile.article_refs:
        article = get_article_by_ref(db, ref)
        if article:
            candidates.append(article)
            profile_refs[(article.code, article.article_number, article.subsection)] = ref
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
        ref = profile_refs.get((article.code, article.article_number, article.subsection))
        seed_meta = LEGAL_SEED_BY_REF.get((article.code, article.article_number, article.subsection))
        context = article_context(db, article, profile.key)
        recommendations.append(
            {
                "article_id": article.id,
                "reference": f"{article.code} art. {article.article_number}{' inc. ' + article.subsection if article.subsection else ''}",
                "title": article.title,
                "legal_role": ref.role if ref else "relacionada",
                "text": article.text,
                "why": article.objective_elements,
                "subjective_elements": article.subjective_elements,
                "evidence_needed": article.evidentiary_requirements,
                "applicability_to_case": ref.applicability if ref else "Relevancia preliminar según coincidencia con el texto del incidente.",
                "probatory_limits": ref.limits if ref else (seed_meta.probatory_limits if seed_meta else "Requiere verificación humana de hechos, fuente y nexo probatorio."),
                "incident_relations": seed_meta.incident_relations if seed_meta else profile.label,
                "sensitive": bool(seed_meta.sensitive) if seed_meta else False,
                "warning": seed_meta.warning if seed_meta else "",
                "confidence": ref.confidence if ref else "medio",
                "source_title": context["source_title"],
                "source_citation": context["source_citation"],
                "source_verified": context["source_verified"],
                "source_url": context["source_url"],
                "last_checked_at": context["last_checked_at"],
                "precedents": context["precedents"],
                "doctrine": context["doctrine"],
                "requires_human_review": True,
            }
        )
        if len(recommendations) >= limit:
            break
    return recommendations


def recommend_legal_profile(db: Session, incident_text: str, limit: int = 12) -> dict:
    profile = get_attack_profile(incident_text)
    return {
        "incident_text": incident_text,
        "profile": {
            "key": profile.key,
            "label": profile.label,
            "legal_theory": profile.legal_theory,
            "required_evidence": list(profile.required_evidence),
            "recommended_measures": list(profile.recommended_measures),
        },
        "recommendations": recommend_articles_for_incident(db, incident_text, limit=limit),
        "policy": {
            "registered_sources_only": True,
            "human_review_required": True,
            "no_unregistered_jurisprudence_or_doctrine": True,
        },
    }


def legal_article_checklist(article: LegalArticle) -> dict:
    key = (article.code, article.article_number, article.subsection or "")
    elements = list(LEGAL_ELEMENT_CHECKLISTS.get(key, ()))
    if not elements:
        raw_parts = [
            part.strip(" .")
            for block in (article.objective_elements, article.subjective_elements)
            for part in block.replace(" y ", ", ").split(",")
            if part.strip(" .")
        ]
        elements = raw_parts[:8] or ["Hecho relevante", "Evidencia disponible", "Nexo probatorio", "Elemento subjetivo"]
    return {
        "article_id": article.id,
        "reference": f"{article.code} art. {article.article_number}{' inc. ' + article.subsection if article.subsection else ''}",
        "title": article.title,
        "elements": elements,
        "evidentiary_requirements": article.evidentiary_requirements,
    }


def _element_matches(link_element: str, checklist_element: str) -> bool:
    left = (link_element or "").lower()
    right = (checklist_element or "").lower()
    if not left or not right:
        return False
    return left in right or right in left or any(token in left for token in right.split() if len(token) > 4)


def build_legal_probatory_matrix(db: Session, case_id: int) -> dict:
    mappings = (
        db.query(LegalMapping)
        .filter(LegalMapping.case_id == case_id, LegalMapping.decision_status != "descartado")
        .order_by(LegalMapping.legal_role.desc(), LegalMapping.created_at.desc())
        .all()
    )
    rows: list[dict] = []
    proved = weak = missing = high_risk = 0

    for mapping in mappings:
        article = db.get(LegalArticle, mapping.article_id) if mapping.article_id else None
        checklist = legal_article_checklist(article) if article else {"elements": []}
        links = db.query(LegalMappingEvidence).filter_by(legal_mapping_id=mapping.id).all()
        used_link_ids: set[int] = set()
        for element in checklist["elements"]:
            matched = [link for link in links if _element_matches(link.legal_element, element)]
            if not matched:
                missing += 1
                rows.append(
                    {
                        "mapping_id": mapping.id,
                        "article_id": mapping.article_id,
                        "norm_reference": mapping.norm_reference,
                        "legal_role": mapping.legal_role,
                        "legal_element": element,
                        "element_status": "faltante",
                        "evidence_id": None,
                        "evidence_description": "",
                        "evidence_hash": "",
                        "probatory_strength": "sin evidencia",
                        "missing_evidence": f"Falta evidencia especifica para acreditar: {element}.",
                        "contradiction_risk": "medio",
                        "recommended_measure": "Incorporar evidencia directa o corroborante antes de sostener atribucion o calificacion definitiva.",
                    }
                )
                continue
            for link in matched:
                used_link_ids.add(link.id)
                status = link.element_status or ("probado" if link.probatory_strength in {"alto", "medio"} else "debil")
                proved += 1 if status == "probado" else 0
                weak += 1 if status != "probado" else 0
                high_risk += 1 if link.contradiction_risk in {"alto", "critico"} else 0
                evidence = link.evidence
                rows.append(
                    {
                        "mapping_id": mapping.id,
                        "article_id": mapping.article_id,
                        "norm_reference": mapping.norm_reference,
                        "legal_role": mapping.legal_role,
                        "legal_element": element,
                        "element_status": status,
                        "evidence_id": evidence.id if evidence else None,
                        "evidence_description": evidence.description if evidence else "",
                        "evidence_hash": evidence.sha256_hash if evidence else "",
                        "probatory_strength": link.probatory_strength,
                        "missing_evidence": link.missing_evidence,
                        "contradiction_risk": link.contradiction_risk,
                        "recommended_measure": link.recommended_measure,
                    }
                )

        for link in links:
            if link.id in used_link_ids:
                continue
            status = link.element_status or ("probado" if link.probatory_strength in {"alto", "medio"} else "debil")
            proved += 1 if status == "probado" else 0
            weak += 1 if status != "probado" else 0
            high_risk += 1 if link.contradiction_risk in {"alto", "critico"} else 0
            evidence = link.evidence
            rows.append(
                {
                    "mapping_id": mapping.id,
                    "article_id": mapping.article_id,
                    "norm_reference": mapping.norm_reference,
                    "legal_role": mapping.legal_role,
                    "legal_element": link.legal_element or "Elemento no especificado",
                    "element_status": status,
                    "evidence_id": evidence.id if evidence else None,
                    "evidence_description": evidence.description if evidence else "",
                    "evidence_hash": evidence.sha256_hash if evidence else "",
                    "probatory_strength": link.probatory_strength,
                    "missing_evidence": link.missing_evidence,
                    "contradiction_risk": link.contradiction_risk,
                    "recommended_measure": link.recommended_measure,
                }
            )

    return {
        "case_id": case_id,
        "rows": rows,
        "summary": {
            "approved_or_suggested_mappings": len(mappings),
            "proved_elements": proved,
            "weak_elements": weak,
            "missing_elements": missing,
            "high_risk_elements": high_risk,
        },
    }


def legal_quality_control(db: Session, case_id: int) -> dict:
    matrix = build_legal_probatory_matrix(db, case_id)
    issues: list[dict] = []
    rows = matrix["rows"]
    mappings = db.query(LegalMapping).filter_by(case_id=case_id, decision_status="aprobado").all()
    link_counts = {
        mapping.id: db.query(LegalMappingEvidence).filter_by(legal_mapping_id=mapping.id).count()
        for mapping in mappings
    }
    for mapping in mappings:
        if link_counts.get(mapping.id, 0) == 0:
            issues.append(
                {
                    "severity": "alto",
                    "code": "approved_mapping_without_evidence",
                    "message": f"{mapping.norm_reference} fue aprobado pero no tiene evidencia vinculada.",
                    "recommended_action": "Vincular evidencia concreta o degradar la norma a hipotesis no validada.",
                }
            )
    for row in rows:
        if row["element_status"] == "faltante":
            issues.append(
                {
                    "severity": "medio",
                    "code": "missing_legal_element",
                    "message": f"Falta acreditar {row['legal_element']} para {row['norm_reference']}.",
                    "recommended_action": row["recommended_measure"],
                }
            )
        if row["element_status"] == "debil" or row["probatory_strength"] == "bajo":
            issues.append(
                {
                    "severity": "medio",
                    "code": "weak_probatory_support",
                    "message": f"Soporte probatorio debil en {row['legal_element']} ({row['norm_reference']}).",
                    "recommended_action": "Agregar evidencia corroborante, fuente externa o pericia complementaria.",
                }
            )
        if row["contradiction_risk"] in {"alto", "critico"}:
            issues.append(
                {
                    "severity": "alto",
                    "code": "contradiction_risk",
                    "message": f"Riesgo de contradiccion {row['contradiction_risk']} en {row['legal_element']}.",
                    "recommended_action": row["recommended_measure"] or "Resolver contradicciones antes de cerrar el informe.",
                }
            )

    penalties = {"bajo": 4, "medio": 9, "alto": 18, "critico": 30}
    score = max(0, 100 - sum(penalties.get(issue["severity"], 8) for issue in issues))
    risk_level = "bajo" if score >= 80 else "medio" if score >= 55 else "alto"
    conclusion_impact = "fortalecida" if score >= 80 else "prudente" if score >= 55 else "alta_prudencia"
    return {
        "case_id": case_id,
        "score": score,
        "risk_level": risk_level,
        "conclusion_impact": conclusion_impact,
        "issues": issues,
        "matrix_summary": matrix["summary"],
    }


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
