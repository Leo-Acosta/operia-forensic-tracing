"""Explicit iOS logical file selection; never traverse or open manifest paths."""
import base64
from datetime import datetime
from pathlib import PurePosixPath
import re
from xml.parsers import expat

from operia.forensic_engine.backup_plists import load_metadata
from operia.forensic_engine.canonical import MAX_SOURCE_BYTES, canonical_bytes, read_json, sha256
from operia.forensic_engine.contracts import EngineInputError, ReadResult, Source
from operia.forensic_engine.sqlite_readers import ManifestDatabaseReader, SQLiteCatalogReader, UnsupportedSQLite
from operia.forensic_engine.wal_readers import SQLiteSetReader

SCHEMA = "operia.ios-logical-set/1"
MAX_FILES = 32
MAX_FILE_BYTES = 256 * 1024
MAX_CONTENT_RECORDS = 128
MANIFEST_FORMATS = ("apple-backup-manifest-sqlite", "apple-backup-manifest-wal-set")


def component(raw):
    return {"sha256": sha256(raw), "content_base64": base64.b64encode(raw).decode("ascii")}


def pack_logical(manifest, files, manifest_format=MANIFEST_FORMATS[0]):
    if not 1 <= len(files) <= MAX_FILES or any(len(data) > MAX_FILE_BYTES for _, data in files):
        raise EngineInputError("Selección requiere 1..32 archivos de hasta 256 KiB")
    if len(manifest) + sum(len(data) for _, data in files) > MAX_SOURCE_BYTES:
        raise EngineInputError("Conjunto lógico supera cuota")
    result = canonical_bytes({"schema": SCHEMA, "selection": "explicit_subset",
        "manifest": {"format": manifest_format, **component(manifest)},
        "files": [{"file_id": file_id, **component(data)} for file_id, data in sorted(files)]})
    if len(result) > MAX_SOURCE_BYTES:
        raise EngineInputError("Paquete lógico codificado supera 5 MiB")
    return result


def decode_component(item, keys, limit):
    if (not isinstance(item, dict) or set(item) != keys or not isinstance(item["sha256"], str)
            or not isinstance(item["content_base64"], str)):
        raise UnsupportedSQLite("Componente lógico fuera del contrato")
    raw = base64.b64decode(item["content_base64"], validate=True)
    if len(raw) > limit or sha256(raw) != item["sha256"]:
        raise ValueError("logical component integrity or size")
    return raw


def plist_values(raw):
    tree = load_metadata(raw)
    if not raw.startswith(b"bplist00"):
        parser = expat.ParserCreate()
        allowed = {"plist", "dict", "key", "array", "string", "integer", "real", "true", "false", "data", "date"}
        def start(tag, attrs):
            if tag not in allowed or (attrs and not (tag == "plist" and attrs == {"version": "1.0"})):
                raise ValueError("unsupported XML vocabulary")
        parser.StartElementHandler = start
        parser.ExternalEntityRefHandler = lambda *args: 0
        parser.Parse(raw, True)
    records, excluded = [], []
    budget = 0
    def walk(value, locator):
        nonlocal budget
        budget += 1
        if budget > 1024 or len(records) + len(excluded) >= MAX_CONTENT_RECORDS:
            raise UnsupportedSQLite("Plist supera 1024 nodos o 128 valores/exclusiones")
        if isinstance(value, dict):
            if "$archiver" in value or "$objects" in value:
                raise UnsupportedSQLite("NSKeyedArchiver fuera de cobertura")
            for key in sorted(value):
                if not isinstance(key, str) or len(key) > 128 or any(ord(c) < 32 for c in key):
                    raise ValueError("invalid plist key")
                walk(value[key], locator + "/" + key.replace("~", "~0").replace("/", "~1"))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, locator + "/" + str(index))
        elif type(value) in (str, bool, int, float) or isinstance(value, datetime):
            if isinstance(value, str) and len(value) > 2048:
                excluded.append({"locator": locator, "reason": "Valor plist supera 2048 caracteres"})
            else:
                fields = {"value_type": type(value).__name__,
                          "value": value.isoformat() + "Z" if isinstance(value, datetime) else value}
                records.append((locator, "logical_plist_scalar", fields))
        else:
            excluded.append({"locator": locator, "reason": "Datos binarios/UID u objeto plist no interpretado"})
    walk(tree, "plist")
    return records, excluded


def read_content(raw, path):
    suffix = PurePosixPath(path).suffix.lower()
    if suffix == ".plist":
        return plist_values(raw)
    if suffix in (".txt", ".log"):
        if len(raw) > 65536:
            raise UnsupportedSQLite("Texto supera 64 KiB")
        text = raw.decode("utf-8-sig")
        if any((ord(c) < 32 and c not in "\t\r\n") or ord(c) == 127 for c in text):
            raise ValueError("text control characters")
        lines = text.splitlines()
        if len(lines) > MAX_CONTENT_RECORDS or any(len(line) > 2048 for line in lines):
            raise UnsupportedSQLite("Texto supera 128 líneas o 2048 caracteres por línea")
        return [(f"line:{index}", "logical_text_line", {"text": line}) for index, line in enumerate(lines, 1)], []
    if suffix in (".db", ".sqlite", ".sqlite3"):
        result = SQLiteCatalogReader("ios").read(Source("logical", "logical.db", "ios", "sqlite-schema-catalog", raw))
        if result.status not in ("analizado", "sin_registros"):
            raise UnsupportedSQLite("SQLite lógico fuera del perfil ordinario; WAL/SHM no se combinan automáticamente")
        return [(r["locator"], r["kind"], r["normalized"]) for r in result.records], result.excluded
    raise UnsupportedSQLite("Extensión fuera de cobertura; solo hash y declaración de archivo")


class LogicalBackupReader:
    identifier = "operia.ios.backup-logical-files"
    version = "1.0.0"
    platform = "ios"
    format = "apple-backup-logical-set"
    dependencies = ()

    def read(self, source):
        warnings = ["Selección explícita de copias preservadas; sin recorrer directorios ni abrir rutas de Manifest.db.",
                    "fileID/dominio/ruta son declaraciones; SHA-256 verifica bytes aportados, no autenticidad ni asociación física.",
                    "Sin verificar convención SHA-1 de fileID, modo físico, cifrado, NSKeyedArchiver, ejecutables o contenido de filas SQLite.",
                    "Valores y texto pueden contener datos personales; acceso limitado al expediente. Sin inferir instalación, ejecución, tráfico ni fechas de ataque."]
        try:
            value = read_json(source.raw)
            if (not isinstance(value, dict) or set(value) != {"schema", "selection", "manifest", "files"}
                    or value["schema"] != SCHEMA or value["selection"] != "explicit_subset"):
                raise UnsupportedSQLite("Contrato de selección lógica no admitido")
            manifest = value["manifest"]
            manifest_raw = decode_component(manifest, {"format", "sha256", "content_base64"}, MAX_SOURCE_BYTES)
            if manifest["format"] not in MANIFEST_FORMATS:
                raise UnsupportedSQLite("Manifiesto lógico requiere perfil Files conocido")
            reader = ManifestDatabaseReader() if manifest["format"] == MANIFEST_FORMATS[0] else SQLiteSetReader("ios", manifest=True)
            declared = reader.read(Source("manifest", "Manifest.db", "ios", reader.format, manifest_raw))
            if declared.status not in ("analizado", "sin_registros"):
                raise UnsupportedSQLite("Manifest no interpretable; no se vinculan archivos lógicos")
            mapping = {r["normalized"]["file_id"]: r["normalized"] for r in declared.records if r["kind"] == "backup_file_declaration"}
            files = value["files"]
            if not isinstance(files, list) or not 1 <= len(files) <= MAX_FILES:
                raise UnsupportedSQLite("Selección requiere 1..32 archivos")
            selected = {}
            for item in files:
                raw = decode_component(item, {"file_id", "sha256", "content_base64"}, MAX_FILE_BYTES)
                file_id = item["file_id"]
                if (not isinstance(file_id, str) or not re.fullmatch(r"[0-9a-f]{40}", file_id) or file_id in selected
                        or file_id not in mapping or mapping[file_id]["flags"] != 1):
                    raise ValueError("invalid logical file association")
                selected[file_id] = raw
            result = ReadResult("analizado", warnings=warnings + ["Manifest: " + w for w in declared.warnings],
                excluded=[{"locator": "manifest/" + e["locator"], "reason": e["reason"]} for e in declared.excluded])
            regular = sum(row["flags"] == 1 for row in mapping.values())
            provenance = {"manifest_sha256": sha256(manifest_raw), "manifest_format": manifest["format"],
                "manifest_regular_files": regular, "selected_files": len(selected),
                "omitted_regular_files": regular - len(selected), "selection": "explicit_subset",
                "manifest_directories": len(mapping) - regular,
                "manifest_snapshot": next((r["normalized"] for r in declared.records if r["kind"] == "sqlite_snapshot_provenance"), None)}
            result.records.append(dict(locator="logical-set/provenance", kind="logical_selection_provenance",
                                       original=provenance, normalized=dict(provenance), time=None))
            for file_id, row in sorted(mapping.items()):
                prefix = "logical/" + file_id
                if file_id not in selected:
                    result.excluded.append({"locator": prefix, "reason": "Directorio declarado; no se recorre" if row["flags"] == 2 else "Archivo no aportado en selección explícita; no equivale a ausente o eliminado"})
                    continue
                raw = selected[file_id]
                metadata = {**row, "sha256": sha256(raw), "size_bytes": len(raw)}
                result.records.append(dict(locator=prefix, kind="logical_file_preservation",
                                           original=metadata, normalized=dict(metadata), time=None))
                try:
                    records, excluded = read_content(raw, row["relative_path"])
                    if len(records) + len(excluded) > MAX_CONTENT_RECORDS:
                        raise UnsupportedSQLite("Contenido supera 128 registros/exclusiones")
                    for locator, kind, fields in records:
                        fields = {**fields, "file_id": file_id, "file_sha256": metadata["sha256"],
                                  "content_locator": locator}
                        result.records.append(dict(locator=prefix + "/" + locator, kind=kind,
                                                   original=fields, normalized=dict(fields), time=None))
                    result.excluded.extend({"locator": prefix + "/" + e["locator"], "reason": e["reason"]} for e in excluded)
                except UnsupportedSQLite as error:
                    result.excluded.append({"locator": prefix + "/content", "reason": str(error)})
                except Exception:
                    result.excluded.append({"locator": prefix + "/content", "reason": "Contenido corrupto, incompatible o fuera de límites; original preservado"})
            return result
        except UnsupportedSQLite as error:
            return ReadResult("no_compatible", warnings=warnings + [str(error)])
        except Exception:
            return ReadResult("corrupto", warnings=warnings + ["Paquete lógico inválido, inconsistente o fuera de cuota; sin publicación parcial"])
