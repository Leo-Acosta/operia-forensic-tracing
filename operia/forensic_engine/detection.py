"""Explicit equality/label-boundary comparisons; no feeds or executable rules."""
import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit

from operia.forensic_engine.canonical import canonical_bytes, read_json, sha256
from operia.forensic_engine.contracts import EngineInputError

DEMO_RULES = (
    {"id": "operia.demo.package", "version": "1.0.0", "author": "OPERIA project implementation",
     "provenance": "Original synthetic demonstration", "kind": "package_inventory", "field": "package",
     "equals": "invalid.operia.synthetic", "severity": "informativa", "synthetic": True,
     "explanation": "Paquete sintético reservado para verificar la regla; no es una firma de malware.",
     "benign_alternatives": "Fixture de prueba o paquete con nombre coincidente.",
     "limitations": "No valida spyware ni compromiso; exige un registro de inventario."},
    {"id": "operia.demo.profile", "version": "1.0.0", "author": "OPERIA project implementation",
     "provenance": "Original synthetic demonstration", "kind": "configuration_payload", "field": "profile_identifier",
     "equals": "invalid.operia.synthetic", "severity": "informativa", "synthetic": True,
     "explanation": "Identificador de perfil sintético; demuestra comparación exacta únicamente.",
     "benign_alternatives": "Perfil de pruebas o coincidencia nominal.",
     "limitations": "El archivo no demuestra instalación ni actividad."},
)


def domain(value):
    if not isinstance(value, str) or not value or len(value) > 253:
        raise EngineInputError("Dominio inválido")
    try:
        value = value.removesuffix(".").encode("idna").decode("ascii").lower()
    except UnicodeError as error:
        raise EngineInputError("Dominio IDNA inválido") from error
    if not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in value.split(".")):
        raise EngineInputError("Etiquetas de dominio inválidas")
    return value


def normalize(kind, value):
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise EngineInputError("Indicador vacío o demasiado largo")
    if kind == "domain":
        return domain(value)
    if kind == "ip":
        try:
            return str(ipaddress.ip_address(value))
        except ValueError as error:
            raise EngineInputError("IP inválida") from error
    if kind == "sha256":
        if not re.fullmatch(r"[0-9a-fA-F]{64}", value):
            raise EngineInputError("SHA-256 inválido")
        return value.lower()
    if kind == "url":
        try:
            parts = urlsplit(value)
            if parts.scheme.lower() not in ("https", "http") or not parts.hostname or parts.username or parts.password:
                raise EngineInputError("URL HTTP(S) sin credenciales requerida")
            try:
                host = str(ipaddress.ip_address(parts.hostname))
                if ":" in host:
                    host = f"[{host}]"
            except ValueError:
                host = domain(parts.hostname)
            port = parts.port
            if port is not None and not ((parts.scheme.lower() == "http" and port == 80) or (parts.scheme.lower() == "https" and port == 443)):
                host += f":{port}"
            return urlunsplit((parts.scheme.lower(), host, parts.path or "/", parts.query, parts.fragment))
        except ValueError as error:
            raise EngineInputError("URL inválida") from error
    if kind in ("package", "profile_identifier", "path"):
        return value  # Deliberately case sensitive, with no filesystem resolution.
    raise EngineInputError("Tipo de indicador no soportado")


def validate_indicators(raw):
    value = read_json(raw, limit=256 * 1024)
    required = {"schema", "source", "terms", "version", "limitations", "items"}
    if not isinstance(value, dict) or set(value) != required or value["schema"] != "operia.indicators/1":
        raise EngineInputError("Esquema de indicadores incompatible")
    if not all(isinstance(value[key], str) and 1 <= len(value[key]) <= 4000 for key in required - {"items"}):
        raise EngineInputError("Fuente, condiciones, versión y limitaciones requeridas")
    if not isinstance(value["items"], list) or not 1 <= len(value["items"]) <= 500:
        raise EngineInputError("Se requieren entre 1 y 500 indicadores; para omitirlos no selecciones conjunto")
    if len(value["version"]) > 160:
        raise EngineInputError("Versión de indicadores demasiado larga")
    identifiers = set()
    for item in value["items"]:
        if not isinstance(item, dict) or set(item) != {"id", "type", "value", "match"}:
            raise EngineInputError("Indicador incompatible")
        if not isinstance(item["id"], str) or not 1 <= len(item["id"]) <= 100 or item["id"] in identifiers:
            raise EngineInputError("Identificador vacío, duplicado o demasiado largo")
        identifiers.add(item["id"])
        if item["match"] not in ("exact", "subdomains") or (item["match"] == "subdomains" and item["type"] != "domain"):
            raise EngineInputError("Semántica de coincidencia no soportada")
        if not isinstance(item["type"], str):
            raise EngineInputError("Tipo de indicador inválido")
        normalize(item["type"], item["value"])
    return value


def candidates(artifact, kind):
    fields = artifact["normalized"]
    if kind == "sha256":
        return [artifact["source"]["sha256"]]
    if kind in ("package", "profile_identifier", "path"):
        return [fields[kind]] if fields.get(kind) else []
    urls = fields.get("urls", [])
    if kind == "url":
        return urls
    if kind in ("domain", "ip"):
        result = []
        for url in urls:
            try:
                host = urlsplit(url).hostname
                if host:
                    result.append(host)
            except ValueError:
                continue
        return result
    return []


def evaluate(artifacts, indicator_bytes=None, demo=False):
    dataset = validate_indicators(indicator_bytes) if indicator_bytes is not None else None
    alerts = []
    for artifact in artifacts:
        if demo:
            for rule in DEMO_RULES:
                if artifact["kind"] == rule["kind"] and artifact["normalized"].get(rule["field"]) == rule["equals"]:
                    alerts.append({"rule_id": rule["id"], "rule_version": rule["version"], "indicator_id": None,
                        "artifact_ids": [artifact["id"]], "severity": rule["severity"], "synthetic": True,
                        "explanation": rule["explanation"], "limitations": rule["limitations"], "review_status": "pendiente"})
        if dataset:
            for item in dataset["items"]:
                target = normalize(item["type"], item["value"])
                for observed in candidates(artifact, item["type"]):
                    try:
                        normalized = normalize(item["type"], observed)
                    except EngineInputError:
                        continue
                    if normalized == target or (item["match"] == "subdomains" and normalized.endswith("." + target)):
                        alerts.append({"rule_id": "operia.indicator.compare", "rule_version": "1.0.0",
                            "indicator_id": item["id"], "indicator_set_sha256": sha256(indicator_bytes),
                            "indicator_type": item["type"],
                            "artifact_ids": [artifact["id"]], "severity": "informativa", "synthetic": False,
                            "observed": observed, "normalized": normalized, "semantics": item["match"],
                            "explanation": "Coincidencia con indicador aportado por el operador; requiere corroboración.",
                            "limitations": dataset["limitations"], "review_status": "pendiente"})
                        break
    # A source-file hash is one observation of that file, even if many extracted
    # records point to it. Group its references instead of inflating alert counts.
    grouped, file_hash_matches = [], {}
    for alert in alerts:
        if alert.get("indicator_type") == "sha256":
            key = (alert["indicator_set_sha256"], alert["indicator_id"], alert["normalized"])
            if key in file_hash_matches:
                file_hash_matches[key]["artifact_ids"].extend(alert["artifact_ids"])
                continue
            file_hash_matches[key] = alert
        grouped.append(alert)
    unique = {sha256(canonical_bytes(alert)): alert for alert in grouped}
    return [{"id": identifier, **alert} for identifier, alert in sorted(unique.items())]
