"""Original, bounded metadata readers. No backup traversal, decryption or acquisition."""
import plistlib
import re
from datetime import datetime, timezone
from xml.parsers import expat

from operia.forensic_engine.canonical import MAX_RECORDS, checked_tree
from operia.forensic_engine.contracts import EngineInputError, ReadResult

MAX_PLIST_BYTES = 1024 * 1024


class UniqueKeys(dict):
    def __setitem__(self, key, value):
        if key in self:
            raise ValueError("duplicate key")
        super().__setitem__(key, value)


def load_metadata(raw):
    if len(raw) > MAX_PLIST_BYTES:
        raise EngineInputError("Metadatos plist superan 1 MiB")
    if raw.startswith(b"bplist00"):
        if len(raw) < 40 or int.from_bytes(raw[-24:-16], "big") > 20000:
            raise ValueError("binary object budget")
    else:
        # Only UTF-8 XML. Preflight bounds nesting before plistlib builds its tree.
        text = raw.decode("utf-8-sig")
        if "\x00" in text or not text.lstrip().startswith(("<?xml", "<plist")):
            raise ValueError("unsupported encoding/container")
        parser = expat.ParserCreate()
        depth, nodes = 0, 0

        def start(name, attrs):
            nonlocal depth, nodes
            depth += 1
            nodes += 1
            if depth > 52 or nodes > 50000:
                raise ValueError("XML budget")

        def end(name):
            nonlocal depth
            depth -= 1

        def entity(*args):
            raise ValueError("entities forbidden")

        parser.StartElementHandler, parser.EndElementHandler = start, end
        parser.EntityDeclHandler = entity
        parser.ExternalEntityRefHandler = lambda *args: 0
        parser.Parse(text, True)
    tree = plistlib.loads(raw, dict_type=UniqueKeys)
    checked_tree(tree)
    if not isinstance(tree, dict):
        raise ValueError("dictionary required")
    return tree


def entry(locator, kind, original, normalized, stamp=None):
    return dict(locator=locator, kind=kind, original=original, normalized=normalized, time=stamp)


def declared_date(value):
    if not isinstance(value, datetime) or value.tzinfo is not None:
        raise ValueError("plist UTC date required")
    stamp = value.replace(tzinfo=timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    return dict(original=stamp, format="apple_plist_date", unit="seconds", timezone="UTC",
                normalized_utc=stamp, precision="declarada_por_plist",
                uncertainty="reloj_no_contrastado", clock_suspect="desconocido")


class BackupInfoReader:
    identifier = "operia.ios.backup-info"
    version = "1.0.0"
    platform = "ios"
    format = "apple-backup-info-plist"
    dependencies = ()

    def read(self, source):
        if len(source.raw) > MAX_PLIST_BYTES:
            raise EngineInputError("Metadatos plist superan 1 MiB")
        if not source.raw.strip():
            return ReadResult("sin_registros", warnings=["Archivo vacío; no acredita ausencia de backups"])
        try:
            tree = load_metadata(source.raw)
            for key in ("Product Type", "Product Version"):
                if not isinstance(tree.get(key), str) or not 1 <= len(tree[key]) <= 256:
                    return ReadResult("no_compatible", warnings=["Info.plist requiere Product Type y Product Version de texto"])
            result = ReadResult("analizado", warnings=[
                "Metadatos declarados del archivo; no verifica dispositivo, integridad del backup ni instalación/ejecución actual.",
                "Solo campos permitidos; no se replican identificadores personales, secretos ni datos incrustados."])
            for key, name in (("Product Type", "product_type"), ("Product Version", "product_version")):
                result.records.append(entry("/" + key, "backup_metadata", {key: tree[key]}, {name: tree[key]}))
            if "Last Backup Date" in tree:
                stamp = declared_date(tree["Last Backup Date"])
                result.records.append(entry("/Last Backup Date", "backup_declared_date", {"date": stamp["original"]},
                                            {"date_role": "declared_last_backup"}, stamp))
            if "Installed Applications" in tree:
                apps = tree["Installed Applications"]
                if not isinstance(apps, list) or len(apps) > MAX_RECORDS - len(result.records):
                    raise ValueError("applications budget/type")
                for index, app in enumerate(apps):
                    locator = f"/Installed Applications/{index}"
                    if not isinstance(app, str) or len(app) > 255 or not re.fullmatch(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+", app):
                        result.excluded.append(dict(locator=locator, reason="identificador de aplicación no admitido"))
                        continue
                    result.records.append(entry(locator, "backup_application_inventory", {"bundle_identifier": app},
                                                {"bundle_identifier": app}))
            return result
        except EngineInputError:
            raise
        except Exception:
            return ReadResult("corrupto", warnings=["Metadatos Info.plist inválidos o fuera de límites"])


class BackupManifestReader:
    identifier = "operia.ios.backup-manifest"
    version = "1.0.0"
    platform = "ios"
    format = "apple-backup-manifest-plist"
    dependencies = ()

    def read(self, source):
        if len(source.raw) > MAX_PLIST_BYTES:
            raise EngineInputError("Metadatos plist superan 1 MiB")
        if not source.raw.strip():
            return ReadResult("sin_registros", warnings=["Archivo vacío; estado de cifrado desconocido"])
        try:
            tree = load_metadata(source.raw)
            if "IsEncrypted" not in tree:
                return ReadResult("no_compatible", warnings=["Manifest.plist requiere IsEncrypted; no se presume ausencia de cifrado"])
            if type(tree["IsEncrypted"]) is not bool:
                raise ValueError("boolean required")
            result = ReadResult("analizado", warnings=[
                "Bandera declarada en Manifest.plist, no prueba criptográfica; no se descifra ni se abre Manifest.db.",
                "BackupKeyBag, Lockdown y demás campos no interpretados permanecen solo en el original preservado."])
            result.records.append(entry("/IsEncrypted", "backup_encryption_declaration",
                                        {"IsEncrypted": tree["IsEncrypted"]}, {"declared_encrypted": tree["IsEncrypted"]}))
            return result
        except EngineInputError:
            raise
        except Exception:
            return ReadResult("corrupto", warnings=["Metadatos Manifest.plist inválidos o fuera de límites"])
