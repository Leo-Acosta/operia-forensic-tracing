import base64
import csv
import io
import re

from operia.forensic_engine import ENGINE_NAME, ENGINE_VERSION, SCHEMA_VERSION
from operia.forensic_engine.canonical import MAX_OUTPUT_BYTES, MAX_SOURCE_BYTES, canonical_bytes, sha256
from operia.forensic_engine.contracts import EngineInputError, Source
from operia.forensic_engine.detection import DEMO_RULES, evaluate
from operia.forensic_engine.readers import reader_order


def capabilities():
    return {"engine": ENGINE_NAME, "version": ENGINE_VERSION, "schema": SCHEMA_VERSION,
        "validation": "synthetic_only", "network_access": "no_network_operations_implemented",
        "readers": [{"id": reader.identifier, "version": reader.version, "platform": reader.platform,
                     "format": reader.format} for reader in reader_order()],
        "limits": {"source_bytes": MAX_SOURCE_BYTES, "output_bytes": MAX_OUTPUT_BYTES},
        "message": f"Motor propio {ENGINE_VERSION} · {len(reader_order())} lectores acotados · validación sintética; sin certificación de spyware."}


def analyze(source: Source, indicator_bytes=None, demo=False):
    if len(source.raw) > MAX_SOURCE_BYTES:
        raise EngineInputError("Fuente supera 5 MiB")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}", source.filename):
        raise EngineInputError("Nombre de archivo no seguro")
    reader = next((reader for reader in reader_order() if (reader.platform, reader.format) == (source.platform, source.format)), None)
    if reader is None:
        raise EngineInputError("Formato/plataforma sin lector instalado")
    raw_hash = sha256(source.raw)
    result = reader.read(source)
    artifacts = []
    identities = set()
    record_fingerprints = {}
    for item in result.records:
        identity = sha256(canonical_bytes({"source_hash": raw_hash, "locator": item["locator"], "reader": reader.identifier}))
        if identity in identities:
            raise EngineInputError("Lector emitió un localizador duplicado")
        identities.add(identity)
        fingerprint = sha256(canonical_bytes({key: item[key] for key in ("kind", "original", "normalized", "time")}))
        duplicate_of = record_fingerprints.get(fingerprint)
        record_fingerprints.setdefault(fingerprint, identity)
        artifacts.append({"id": identity, "source": {"filename": source.filename, "sha256": raw_hash},
            "reader_id": reader.identifier, "reader_version": reader.version, "duplicate_of": duplicate_of, **item})
    independent = [artifact for artifact in artifacts if artifact["duplicate_of"] is None]
    alerts = evaluate(independent, indicator_bytes, demo)
    events = [{"id": "event:" + artifact["id"], "artifact_id": artifact["id"],
        "event_type": "fecha_de_backup_declarada" if artifact["kind"] == "backup_declared_date" else "registro_de_log_observado", **artifact["time"],
        "interpretation": "Evento registrado; no se infiere intento, ejecución maliciosa ni inicio de ataque."}
        for artifact in independent if artifact["time"]]
    events.sort(key=lambda event: (event["normalized_utc"], event["id"]))
    limitations = ["Alcance limitado al archivo aportado, no al dispositivo completo.",
        "Sin contraste con adquisiciones reales; ausencia de alertas no significa dispositivo limpio."]
    detection = "sin_datos_analizables" if not artifacts else "coincidencias_pendientes" if alerts else (
        "sin_coincidencias_en_reglas_aplicadas" if indicator_bytes is not None or demo else "sin_indicadores_ni_reglas_activas")
    output = {"schema": SCHEMA_VERSION, "engine": {"name": ENGINE_NAME, "version": ENGINE_VERSION},
        "origin": "operia_native", "source_manifest": [{"filename": source.filename, "sha256": raw_hash,
            "size_bytes": len(source.raw), "platform": source.platform, "format": source.format}],
        "configuration": {"reader_id": reader.identifier, "reader_version": reader.version, "demo_rules": demo,
            "rules_sha256": sha256(canonical_bytes(DEMO_RULES if demo else [])),
            "indicator_set_sha256": sha256(indicator_bytes) if indicator_bytes is not None else None},
        "coverage": {"state": "parcial" if artifacts else "sin_datos", "sources": [{
            "filename": source.filename, "reader_id": reader.identifier, "status": result.status,
            "records": len(artifacts), "excluded": result.excluded, "warnings": result.warnings}],
            "limitations": limitations}, "detection_status": detection, "forensic_conclusion": "requiere_revision",
        "artifacts": artifacts, "observations": [{"id": "obs:" + item["id"], "artifact_ids": [item["id"]],
            "statement": "Registro extraído del archivo preservado; no constituye una conclusión de compromiso."} for item in artifacts],
        "alerts": alerts, "timeline": events,
        "correlations": [{"type": "duplicate_record", "artifact_id": item["id"], "duplicate_of": item["duplicate_of"],
            "basis": "Registro idéntico dentro de la misma fuente; no constituye evidencia independiente."}
            for item in artifacts if item["duplicate_of"]], "rules": list(DEMO_RULES) if demo else []}
    if len(canonical_bytes(output)) > MAX_OUTPUT_BYTES:
        raise EngineInputError("Salida supera cuota de 16 MiB")
    return output


def timeline_csv(result):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    columns = ("id", "artifact_id", "original", "format", "unit", "timezone", "normalized_utc", "precision", "uncertainty")
    writer.writerow(columns)
    for event in result["timeline"]:
        # Formula-neutral output for spreadsheet software; JSON retains originals.
        writer.writerow([("'" + str(event[key])) if str(event[key]).startswith(("=", "+", "-", "@", "\t", "\r")) else event[key] for key in columns])
    return stream.getvalue().encode("utf-8")
