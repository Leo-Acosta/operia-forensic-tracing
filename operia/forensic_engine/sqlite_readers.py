"""Bounded reads from a private deserialized copy, never from an evidence path."""
from contextlib import contextmanager
import re
import sqlite3

from operia.forensic_engine.canonical import MAX_RECORDS, MAX_SOURCE_BYTES
from operia.forensic_engine.contracts import EngineInputError, ReadResult

MAX_SCHEMA_OBJECTS = 128
MAX_VM_STEPS = 100000
IDENTIFIER = r'(?:"(?:[^"]|"")+"|\[[^\]]+\]|`[^`]+`|[A-Za-z_][A-Za-z0-9_]*)'
PLAIN_INDEX = re.compile(r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+' + IDENTIFIER + r'\s+ON\s+' + IDENTIFIER
                         + r'\s*\(\s*' + IDENTIFIER + r'(?:\s*,\s*' + IDENTIFIER + r')*\s*\)\s*;?', re.I)


class UnsupportedSQLite(ValueError):
    pass


def check_header(raw):
    if len(raw) > MAX_SOURCE_BYTES:
        raise EngineInputError("SQLite supera 5 MiB")
    if len(raw) < 100 or raw[:16] != b"SQLite format 3\x00":
        raise UnsupportedSQLite("Se requiere una imagen SQLite 3 sin cifrado")
    if raw[18:20] != b"\x01\x01":
        raise UnsupportedSQLite("WAL u otra versión de archivo no admitidos; no se modifica la cabecera")
    page_size = int.from_bytes(raw[16:18], "big")
    page_size = 65536 if page_size == 1 else page_size
    if page_size < 512 or page_size > 65536 or page_size & (page_size - 1):
        raise ValueError("invalid page size")
    if len(raw) % page_size or int.from_bytes(raw[28:32], "big") != len(raw) // page_size:
        raise ValueError("incomplete or trailing pages")
    if raw[20] != 0 or int.from_bytes(raw[56:60], "big") != 1:
        raise UnsupportedSQLite("Solo SQLite 3 UTF-8 sin bytes reservados de extensiones")


def authorize(action, first, second, database, origin):
    if origin is not None or database not in (None, "main"):
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_SELECT:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ and (first in ("sqlite_master", "sqlite_schema") or
            (first == "Files" and second in ("fileID", "domain", "relativePath", "flags"))):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_PRAGMA and (first, second) in (("quick_check", None), ("table_xinfo", "Files")):
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


@contextmanager
def preserved_copy(raw, *, authorizer=authorize):
    check_header(raw)
    db = sqlite3.connect(":memory:", timeout=0, cached_statements=0)
    try:
        # Require the controls; never fall back to opening a source on disk.
        for option, value in ((sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True),
                              (sqlite3.SQLITE_DBCONFIG_TRUSTED_SCHEMA, False),
                              (sqlite3.SQLITE_DBCONFIG_ENABLE_LOAD_EXTENSION, False),
                              (sqlite3.SQLITE_DBCONFIG_ENABLE_TRIGGER, False),
                              (sqlite3.SQLITE_DBCONFIG_ENABLE_VIEW, False)):
            db.setconfig(option, value)
            if db.getconfig(option) != value:
                raise EngineInputError("Controles SQLite requeridos no disponibles")
        for category, value in ((sqlite3.SQLITE_LIMIT_LENGTH, 262144),
                                (sqlite3.SQLITE_LIMIT_SQL_LENGTH, 8192),
                                (sqlite3.SQLITE_LIMIT_COLUMN, 64),
                                (sqlite3.SQLITE_LIMIT_EXPR_DEPTH, 10),
                                (sqlite3.SQLITE_LIMIT_VDBE_OP, 25000),
                                (sqlite3.SQLITE_LIMIT_FUNCTION_ARG, 4),
                                (sqlite3.SQLITE_LIMIT_ATTACHED, 0),
                                (sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER, 8),
                                (sqlite3.SQLITE_LIMIT_TRIGGER_DEPTH, 0),
                                (sqlite3.SQLITE_LIMIT_WORKER_THREADS, 0)):
            db.setlimit(category, value)
        db.execute("PRAGMA temp_store=MEMORY")
        db.execute("PRAGMA cache_size=-1024")
        db.execute("PRAGMA query_only=ON")
        ticks = 0

        def progress():
            nonlocal ticks
            ticks += 1000
            return int(ticks > MAX_VM_STEPS)

        db.set_progress_handler(progress, 1000)
        db.deserialize(raw)
        # deserialize uses internal attachment operations; install the SQL
        # allowlist immediately afterwards, before preparing any source query.
        db.set_authorizer(authorizer)
        yield db
    finally:
        db.close()


def safe_schema(db):
    objects = db.execute("SELECT type,name,tbl_name,sql FROM main.sqlite_schema ORDER BY type,name LIMIT 129").fetchall()
    if len(objects) > MAX_SCHEMA_OBJECTS:
        raise UnsupportedSQLite("Esquema supera 128 objetos")
    for kind, name, table, sql in objects:
        if kind not in ("table", "index") or (sql and re.search(r"\b(VIRTUAL|GENERATED|AS|CHECK|DEFAULT|COLLATE|REFERENCES|FOREIGN)\b", sql, re.IGNORECASE)):
            raise UnsupportedSQLite("Esquemas activos, restricciones calculadas y colaciones fuera del perfil admitido")
        if kind == "index" and sql and not PLAIN_INDEX.fullmatch(sql):
            raise UnsupportedSQLite("Solo índices ordinarios de columnas; sin expresiones ni predicados")
        if any(not isinstance(value, str) or not value or len(value) > 256 or any(ord(c) < 32 for c in value)
               for value in (kind, name, table)):
            raise ValueError("schema metadata invalid")
    if db.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
        raise ValueError("integrity check failed")
    return objects


WARNINGS = [
    "Solo imagen principal SQLite preservada y copia privada en memoria; no se verifica ausencia de WAL/journal externos.",
    "Sin reparación, recuperación de borrados, descifrado, extensiones, vistas, triggers ni consultas de usuario.",
    "La consistencia interna no autentica el contenido ni el dispositivo; cobertura parcial y revisión requerida."]


class ManifestDatabaseReader:
    identifier = "operia.ios.backup-manifest-db"
    version = "1.0.0"
    platform = "ios"
    format = "apple-backup-manifest-sqlite"
    dependencies = ()

    def read(self, source):
        if not source.raw:
            return ReadResult("sin_registros", warnings=["Imagen vacía; no acredita ausencia de archivos"])
        try:
            with preserved_copy(source.raw) as db:
                objects = safe_schema(db)
                if not any(kind == "table" and name == "Files" for kind, name, _, _ in objects):
                    raise UnsupportedSQLite("Manifest.db requiere tabla ordinaria Files")
                columns = db.execute("PRAGMA table_xinfo(Files)").fetchall()
                expected = [("fileID", "TEXT", 1), ("domain", "TEXT", 0), ("relativePath", "TEXT", 0),
                            ("flags", "INTEGER", 0), ("file", "BLOB", 0)]
                if [(c[1], c[2].upper(), c[5]) for c in columns] != expected or any(c[6] for c in columns):
                    raise UnsupportedSQLite("Variante de Files fuera del contrato de cinco columnas")
                rows = db.execute("SELECT fileID,domain,relativePath,flags FROM main.Files ORDER BY fileID COLLATE BINARY LIMIT 5001").fetchall()
                if len(rows) > MAX_RECORDS:
                    raise UnsupportedSQLite("Files supera 5000 filas; no se publica truncamiento silencioso")
                result = ReadResult("analizado" if rows else "sin_registros", warnings=WARNINGS + [
                    "fileID, dominio, ruta y flags son declaraciones; no se abren archivos ni se interpreta el BLOB file.",
                    "Otras tablas y columnas BLOB, fechas NSKeyedArchiver, permisos y contenidos lógicos quedan fuera del alcance."])
                seen = set()
                for file_id, domain, path, flags in rows:
                    if not isinstance(file_id, str) or not re.fullmatch(r"[0-9a-f]{40}", file_id) or file_id in seen:
                        raise ValueError("invalid or duplicate fileID")
                    seen.add(file_id)
                    locator = "Files/fileID:" + file_id
                    if (not isinstance(domain, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,256}", domain)
                            or not isinstance(path, str) or len(path) > 2048 or path.startswith("/")
                            or any(ord(c) < 32 for c in path) or "\\" in path or ":" in path
                            or any(part in (".", "..") for part in path.split("/")) or type(flags) is not int or flags not in (1, 2)):
                        result.excluded.append(dict(locator=locator, reason="Dominio, ruta o flags fuera del perfil admitido"))
                        continue
                    fields = dict(file_id=file_id, domain=domain, relative_path=path, flags=flags)
                    result.records.append(dict(locator=locator, kind="backup_file_declaration", original=fields,
                                               normalized=dict(fields), time=None))
                if rows and not result.records:
                    result.status = "no_compatible"
                return result
        except UnsupportedSQLite as error:
            return ReadResult("no_compatible", warnings=WARNINGS + [str(error)])
        except EngineInputError:
            raise
        except (sqlite3.Error, ValueError, UnicodeError, OverflowError, MemoryError):
            return ReadResult("corrupto", warnings=WARNINGS + ["Imagen inválida, alterada o presupuesto SQLite excedido"])


class SQLiteCatalogReader:
    version = "1.0.0"
    format = "sqlite-schema-catalog"
    dependencies = ()

    def __init__(self, platform):
        self.platform = platform
        self.identifier = "operia." + platform + ".sqlite-catalog"

    def read(self, source):
        if not source.raw:
            return ReadResult("sin_registros", warnings=["Imagen vacía; no acredita ausencia de tablas"])
        try:
            with preserved_copy(source.raw) as db:
                objects = safe_schema(db)
                records = []
                for kind, name, table, _ in objects:
                    if name.startswith("sqlite_"):
                        continue
                    pointer = name.replace("~", "~0").replace("/", "~1")
                    fields = dict(object_type=kind, name=name, table=table)
                    records.append(dict(locator=f"sqlite_schema/{kind}/{pointer}", kind="sqlite_schema_metadata",
                                        original=fields, normalized=dict(fields), time=None))
                return ReadResult("analizado" if records else "sin_registros", records=records,
                                  warnings=WARNINGS + ["Solo nombres y tipos de tablas/índices; sin DDL, columnas, filas, fechas ni recuperación de datos."])
        except UnsupportedSQLite as error:
            return ReadResult("no_compatible", warnings=WARNINGS + [str(error)])
        except EngineInputError:
            raise
        except (sqlite3.Error, ValueError, UnicodeError, OverflowError, MemoryError):
            return ReadResult("corrupto", warnings=WARNINGS + ["Imagen inválida, alterada o presupuesto SQLite excedido"])
