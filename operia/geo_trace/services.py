import hashlib
import ipaddress
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from operia.security.outbound import fetch_json
from html import escape
from uuid import uuid4
import math

from operia.core.config import settings

IPINFO_TOKEN = ""

CLOUD_KEYWORDS = [
    "cloudflare",
    "google",
    "amazon",
    "aws",
    "microsoft",
    "azure",
    "digitalocean",
    "akamai",
    "fastly",
    "linode",
    "ovh",
    "oracle",
    "cdn",
    "hosting",
    "datacenter",
    "server",
    "vps",
    "colo",
    "colocation",
]

VPN_PROXY_KEYWORDS = [
    "proxy",
    "vpn",
    "tunnel",
    "anonym",
    "anonymous",
    "residential proxy",
    "exit node",
    "tor",
    "relay",
]

MOBILE_ISP_KEYWORDS = ["mobile", "movistar", "claro", "personal", "telecom", "telefonica"]
URL_REGEX = re.compile(r"(https?://[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}|[a-z2-7]{56}\.onion)")


def extract_ips(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", text)))


def extract_urls(text: str) -> list[str]:
    urls: list[str] = []
    for raw in URL_REGEX.findall(text):
        value = raw.strip().rstrip(".,;)")
        if not value.startswith(("http://", "https://")):
            value = "http://" + value
        urls.append(value)
    return list(dict.fromkeys(urls))


def economic_metrics(score: int) -> dict[str, float]:
    fraud_probability = round(score / 100, 2)
    return {
        "fraud_probability": fraud_probability,
        "expected_cost": round(fraud_probability * 2500, 2),
        "economic_impact": round(fraud_probability * 10000, 2),
    }


def detect_network_category(isp: str = "", org: str = "", asn: str = "") -> str:
    text = f"{isp} {org} {asn}".lower()
    if any(word in text for word in VPN_PROXY_KEYWORDS):
        return "vpn/proxy"
    if any(word in text for word in CLOUD_KEYWORDS):
        return "cloud/proxy"
    if any(word in text for word in MOBILE_ISP_KEYWORDS):
        return "mobile"
    return "residencial"


def classify_forensic_risk(kind: str, isp: str = "", org: str = "", asn: str = "", country: str = "", confidence: str = "media") -> dict[str, object]:
    if kind == "privada":
        return {"category": "local", "network_category": "local", "risk": "bajo", "score": 10, "indicators": ["ip_privada"]}
    if kind == "loopback":
        return {"category": "loopback", "network_category": "local", "risk": "bajo", "score": 5, "indicators": ["loopback"]}
    if kind == "reservada":
        return {"category": "reservada", "network_category": "especial", "risk": "medio", "score": 40, "indicators": ["ip_reservada"]}

    network_category = detect_network_category(isp, org, asn)
    score = 10
    indicators: list[str] = []
    if network_category == "vpn/proxy":
        score += 55
        indicators.append("vpn_proxy_detectado")
    elif network_category == "cloud/proxy":
        score += 40
        indicators.append("infraestructura_cloud_proxy")
    elif network_category == "mobile":
        score += 20
        indicators.append("red_movil")
    else:
        score += 10
        indicators.append("red_residencial_o_estandar")
    if country and country.lower() != "argentina":
        score += 15
        indicators.append("pais_extranjero")
    elif country and country.lower() == "argentina":
        indicators.append("pais_local")
    if confidence == "baja":
        score += 10
        indicators.append("baja_confianza_geo")
    elif confidence == "alta":
        score -= 5
        indicators.append("alta_confianza_geo")
    if any(word in f"{isp} {org} {asn}".lower() for word in VPN_PROXY_KEYWORDS):
        score += 10
        indicators.append("keyword_vpn_proxy")
    score = max(0, min(score, 100))
    risk = "alto" if score >= 75 else "medio" if score >= 45 else "bajo"
    category = "infraestructura_sospechosa" if score >= 75 else network_category if score >= 45 else "publica_normal"
    return {"category": category, "network_category": network_category, "risk": risk, "score": score, "indicators": indicators}


def _ip_kind(ip_obj: ipaddress._BaseAddress) -> str:
    if ip_obj.is_loopback:
        return "loopback"
    if ip_obj.is_private:
        return "privada"
    if ip_obj.is_multicast or ip_obj.is_reserved or ip_obj.is_unspecified:
        return "reservada"
    return "publica"


def _query_ipapi(ip: str) -> dict[str, object] | None:
    # Legacy cleartext provider is retired; records previously obtained are retained.
    return None


def _query_ipinfo(ip: str) -> dict[str, object] | None:
    try:
        data = fetch_json(f"https://ipinfo.io/{ip}/json", timeout=5)
        lat = lon = None
        if data.get("loc") and "," in data["loc"]:
            lat_raw, lon_raw = data["loc"].split(",", 1)
            lat = float(lat_raw)
            lon = float(lon_raw)
        return {
            "country": data.get("country"),
            "city": data.get("city"),
            "isp": data.get("org"),
            "org": data.get("org"),
            "asn": data.get("org"),
            "lat": lat,
            "lon": lon,
            "geo_source": "ipinfo",
            "confidence": "media" if lat is not None and lon is not None else "baja",
        }
    except Exception:
        return None


def geolocate_ip(ip: str) -> dict[str, object]:
    try:
        ip_obj = ipaddress.ip_address(ip)
        kind = _ip_kind(ip_obj)
        if kind != "publica":
            risk = classify_forensic_risk(kind)
            metrics = economic_metrics(int(risk["score"]))
            return {"ip": ip, "target_type": kind, "message": f"IP {kind}", "geo_source": "local", "confidence": "alta", **risk, **metrics}
        geo = _query_ipapi(ip) or _query_ipinfo(ip)
        if not geo:
            risk = classify_forensic_risk("publica", confidence="baja")
            metrics = economic_metrics(int(risk["score"]))
            return {"ip": ip, "target_type": "publica", "message": "No se pudo geolocalizar con ninguna fuente", "confidence": "baja", "geo_source": "ninguna", **risk, **metrics}
        risk = classify_forensic_risk(
            "publica",
            isp=str(geo.get("isp") or ""),
            org=str(geo.get("org") or ""),
            asn=str(geo.get("asn") or ""),
            country=str(geo.get("country") or ""),
            confidence=str(geo.get("confidence") or "media"),
        )
        metrics = economic_metrics(int(risk["score"]))
        return {"ip": ip, "target_type": "publica", "message": "IP analizada correctamente", **geo, **risk, **metrics}
    except Exception as exc:
        risk = classify_forensic_risk("publica", confidence="baja")
        risk["score"] = 85
        risk["risk"] = "alto"
        metrics = economic_metrics(85)
        return {"ip": ip, "target_type": "desconocida", "message": f"Error tecnico: {exc}", "confidence": "baja", "geo_source": "error", **risk, **metrics}


def analyze_url(url: str) -> dict[str, object]:
    # Evidence URLs are observations, never instructions to contact the destination.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or any(ord(c) < 32 for c in url):
            raise ValueError()
        host = parsed.hostname.encode("idna").decode("ascii")
        parsed.port
        return {"url": url, "host": host, "ip": None, "geo": None, "target_type": "observado_no_enriquecido",
                "confidence": "no_evaluada", "risk": "no_evaluado", "score": 0, "message": "Referencia pasiva: sin DNS, conexion ni geolocalizacion."}
    except (ValueError, UnicodeError):
        return {"url": url, "target_type": "url_invalida", "message": "Referencia URL invalida"}


def evidence_hash(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def color_by_risk(risk: str) -> str:
    return "red" if risk == "alto" else "orange" if risk == "medio" else "green"


def create_target_map(targets: list[dict[str, object]], filename: str) -> Path:
    # A passive coordinate plot has no scripts, external tiles, fonts or CDN requests.
    settings.maps_dir.mkdir(parents=True, exist_ok=True)
    output_path = settings.maps_dir / (uuid4().hex + ".html")
    points, rows = [], []
    for target in targets:
        try:
            lat, lon = float(target["lat"]), float(target["lon"])
            if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
                continue
        except (KeyError, TypeError, ValueError):
            continue
        label = escape(str(target.get("ip") or target.get("host") or "Referencia"), quote=True)
        points.append(f'<circle cx="{(lon+180)*2.5}" cy="{(90-lat)*2.5}" r="4" fill="blue"><title>{label}</title></circle>')
        rows.append(f"<li>{label}: {lat}, {lon}. Coordenadas de proveedor, no ubicacion de una persona.</li>")
    html = '<!doctype html><meta charset="utf-8"><h2>Referencias geograficas pasivas</h2><svg viewBox="0 0 900 450" xmlns="http://www.w3.org/2000/svg"><rect width="900" height="450" fill="#edf2f7"/>' + ''.join(points) + '</svg><ul>' + ''.join(rows) + '</ul>'
    with output_path.open("x", encoding="utf-8") as stream:
        stream.write(html)
    return output_path
