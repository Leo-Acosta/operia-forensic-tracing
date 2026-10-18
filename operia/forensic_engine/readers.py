"""Original bounded readers, based on public Apple/Android format descriptions.

Reads provided files only. Never connects to or changes a device.
"""
import plistlib
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from operia.forensic_engine.canonical import MAX_RECORDS, checked_tree
from operia.forensic_engine.contracts import EngineInputError, ReadResult, Source


def record(source, locator, kind, original, normalized, observed_time=None):
    return {"locator": locator, "kind": kind, "original": original,
            "normalized": normalized, "time": observed_time}


class UniquePlistKeys(dict):
    def __setitem__(self, key, value):
        if key in self:
            raise EngineInputError("Clave plist duplicada")
        super().__setitem__(key, value)


class ProfilePlistReader:
    identifier = "operia.ios.configuration-profile"
    version = "1.0.0"
    platform = "ios"
    format = "apple-profile-plist"
    dependencies = ()

    def read(self, source: Source) -> ReadResult:
        raw = source.raw
        if not raw.strip():
            return ReadResult("sin_registros", warnings=["Archivo vacío; no acredita ausencia de perfiles"])
        if raw.startswith(b"PK") or raw.startswith(b"\x1f\x8b"):
            return ReadResult("no_compatible", warnings=["Archivos comprimidos no admitidos"])
        if not (raw.startswith(b"bplist00") or raw.lstrip().startswith((b"<?xml", b"<plist"))):
            return ReadResult("no_compatible", warnings=["Se requiere plist sin firma CMS ni cifrado"])
        # plistlib rejects entity declarations too; reject explicitly before parsing.
        if b"<!ENTITY" in raw.upper():
            return ReadResult("no_compatible", warnings=["Declaraciones de entidades XML rechazadas"])
        try:
            tree = plistlib.loads(raw, dict_type=UniquePlistKeys)
            checked_tree(tree)
        except Exception:
            # The core reports a bounded error; no untrusted parser exception text.
            return ReadResult("corrupto", warnings=["plist inválido o estructura fuera de límites"])
        if not isinstance(tree, dict) or tree.get("PayloadType") != "Configuration":
            return ReadResult("no_compatible", warnings=["No es un perfil de configuración de nivel superior"])
        payloads = tree.get("PayloadContent")
        if not isinstance(payloads, list):
            return ReadResult("corrupto", warnings=["PayloadContent debe ser una lista"])
        if len(payloads) > MAX_RECORDS:
            raise EngineInputError("Demasiados payloads")
        result = ReadResult("analizado" if payloads else "sin_registros", warnings=[
            "El archivo exportado no demuestra que el perfil esté instalado ni activo; no se verificó firma."])
        identifiers = set()
        for index, payload in enumerate(payloads):
            if not isinstance(payload, dict) or not all(isinstance(payload.get(key), str) and payload[key]
                for key in ("PayloadType", "PayloadIdentifier", "PayloadUUID")):
                result.excluded.append({"locator": f"/PayloadContent/{index}", "reason": "claves obligatorias inválidas"})
                continue
            if payload["PayloadIdentifier"] in identifiers:
                result.warnings.append("Identificador de payload duplicado; no representa dos indicios independientes")
            identifiers.add(payload["PayloadIdentifier"])
            # Only these fields are interpreted. Secrets/other fields remain in the
            # preserved original and are not replicated into result records.
            fields = {key: payload[key] for key in ("PayloadType", "PayloadIdentifier", "PayloadUUID")}
            if isinstance(payload.get("PayloadDisplayName"), str):
                fields["PayloadDisplayName"] = payload["PayloadDisplayName"]
            result.records.append(record(source, f"/PayloadContent/{index}", "configuration_payload", fields,
                {"payload_type": payload["PayloadType"], "profile_identifier": payload["PayloadIdentifier"]}))
        if result.excluded:
            result.status = "analizado" if result.records else "corrupto"
        return result


class PackageInventoryReader:
    identifier = "operia.android.package-inventory"
    version = "1.0.0"
    platform = "android"
    format = "android-pm-packages"
    dependencies = ()
    line = re.compile(r"package:(?:(/[^\r\n]+)=)?([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+)\Z")

    def read(self, source: Source) -> ReadResult:
        try:
            text = source.raw.decode("utf-8-sig")
        except UnicodeError:
            return ReadResult("corrupto", warnings=["Se requiere texto UTF-8"])
        result = ReadResult("sin_registros", warnings=[
            "Inventario declarado; no prueba instalación actual, ejecución, permisos ni carácter malicioso."])
        for number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            if len(line) > 8192:
                raise EngineInputError("Línea de inventario demasiado larga")
            match = self.line.fullmatch(line)
            if not match:
                result.excluded.append({"locator": f"line:{number}", "reason": "variante no admitida"})
                continue
            result.records.append(record(source, f"line:{number}", "package_inventory", {"line": line},
                {"package": match.group(2), "path": match.group(1)}))
            if len(result.records) > MAX_RECORDS:
                raise EngineInputError("Demasiados paquetes")
        result.status = "analizado" if result.records else "no_compatible" if result.excluded else "sin_registros"
        return result


class EpochLogReader:
    identifier = "operia.android.logcat-epoch"
    version = "1.0.0"
    platform = "android"
    format = "android-logcat-epoch"
    dependencies = ()
    line = re.compile(r"\s*(\d{1,11}\.\d{3,6})\s+(\d{1,8})\s+(\d{1,8})\s+([VDIWEFA])\s+([^:]{1,128}): ?(.*)\Z")
    urls = re.compile(r"https?://[^\s<>\"']+")

    def read(self, source: Source) -> ReadResult:
        try:
            text = source.raw.decode("utf-8-sig")
        except UnicodeError:
            return ReadResult("corrupto", warnings=["Se requiere texto UTF-8"])
        result = ReadResult("sin_registros", warnings=[
            "Texto de log declarado; una URL mencionada no demuestra comunicación. Reloj del dispositivo no contrastado."])
        for number, line in enumerate(text.splitlines(), 1):
            if not line.strip() or line.startswith("--------- beginning of "):
                continue
            if len(line) > 8192:
                raise EngineInputError("Línea de log demasiado larga")
            match = self.line.fullmatch(line)
            if not match:
                result.excluded.append({"locator": f"line:{number}", "reason": "requiere epoch con PID/TID, prioridad y tag"})
                continue
            epoch, pid, tid, priority, tag, message = match.groups()
            try:
                micros = int(Decimal(epoch) * 1000000)
                stamp = (datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=micros)).isoformat(timespec="microseconds").replace("+00:00", "Z")
            except (ValueError, OverflowError, InvalidOperation):
                result.excluded.append({"locator": f"line:{number}", "reason": "epoch fuera de rango"})
                continue
            result.records.append(record(source, f"line:{number}", "log_entry", {"line": line},
                {"pid": int(pid), "tid": int(tid), "priority": priority, "tag": tag.strip(),
                 "message": message, "urls": [url for url in self.urls.findall(message) if len(url) <= 2048]},
                {"original": epoch, "format": "unix_epoch_seconds", "unit": "seconds", "timezone": "UTC",
                 "normalized_utc": stamp, "precision": f"{len(epoch.split('.')[1])} decimales",
                 "uncertainty": "reloj_no_contrastado", "clock_suspect": "desconocido"}))
            if len(result.records) > MAX_RECORDS:
                raise EngineInputError("Demasiados registros de log")
        result.status = "analizado" if result.records else "no_compatible" if result.excluded else "sin_registros"
        return result


from operia.forensic_engine.backup_plists import BackupInfoReader, BackupManifestReader
from operia.forensic_engine.sqlite_readers import ManifestDatabaseReader, SQLiteCatalogReader

READERS = (ProfilePlistReader(), PackageInventoryReader(), EpochLogReader(), BackupInfoReader(), BackupManifestReader(),
           ManifestDatabaseReader(), SQLiteCatalogReader("ios"), SQLiteCatalogReader("android"))


def reader_order(readers=READERS):
    by_id = {}
    by_format = {}
    for reader in readers:
        if reader.identifier in by_id or (reader.platform, reader.format) in by_format:
            raise EngineInputError("Lector o salida duplicada")
        by_id[reader.identifier] = reader
        by_format[(reader.platform, reader.format)] = reader
    result, visiting, done = [], set(), set()

    def visit(identifier):
        if identifier in visiting:
            raise EngineInputError("Dependencia circular")
        if identifier in done:
            return
        if identifier not in by_id:
            raise EngineInputError("Dependencia de lector ausente")
        visiting.add(identifier)
        for dependency in by_id[identifier].dependencies:
            visit(dependency)
        visiting.remove(identifier)
        done.add(identifier)
        result.append(by_id[identifier])
    for identifier in sorted(by_id):
        visit(identifier)
    return result
