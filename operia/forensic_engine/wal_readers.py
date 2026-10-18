"""Bounded offline WAL reconstruction; no source paths or SQLite disk access."""
import base64
import struct

from operia.forensic_engine.canonical import MAX_SOURCE_BYTES, canonical_bytes, read_json, sha256
from operia.forensic_engine.contracts import EngineInputError, ReadResult, Source
from operia.forensic_engine.sqlite_readers import (
    ManifestDatabaseReader, SQLiteCatalogReader, UnsupportedSQLite, check_header)

MAX_FRAMES = 1024
SET_SCHEMA = "operia.sqlite-set/1"


def checksum(raw, order, state=(0, 0)):
    """SQLite's documented rolling checksum, modulo 2**32."""
    a, b = state
    for x, y in struct.iter_unpack(order + "II", raw):
        a = (a + x + b) & 0xffffffff
        b = (b + y + a) & 0xffffffff
    return a, b


def pack_set(database, wal, shm=None):
    if sum(len(raw) for raw in (database, wal, shm) if raw is not None) > MAX_SOURCE_BYTES:
        raise EngineInputError("Componentes SQLite superan 5 MiB")
    parts = {role: None if raw is None else {
        "sha256": sha256(raw), "content_base64": base64.b64encode(raw).decode("ascii")}
        for role, raw in (("database", database), ("wal", wal), ("shm", shm))}
    raw = canonical_bytes({"schema": SET_SCHEMA, **parts})
    if len(raw) > MAX_SOURCE_BYTES:
        raise EngineInputError("Conjunto SQLite codificado supera 5 MiB")
    return raw


def unpack_set(raw):
    value = read_json(raw)
    if not isinstance(value, dict) or set(value) != {"schema", "database", "wal", "shm"} or value["schema"] != SET_SCHEMA:
        raise UnsupportedSQLite("Contrato de conjunto SQLite no admitido")
    parts = {}
    for role in ("database", "wal", "shm"):
        item = value[role]
        if role == "shm" and item is None:
            parts[role] = None
            continue
        if (not isinstance(item, dict) or set(item) != {"sha256", "content_base64"}
                or not isinstance(item["content_base64"], str) or not isinstance(item["sha256"], str)):
            raise UnsupportedSQLite("Componente SQLite fuera del contrato")
        data = base64.b64decode(item["content_base64"], validate=True)
        if sha256(data) != item["sha256"]:
            raise ValueError("component digest mismatch")
        parts[role] = data
    return parts


def check_shm(shm, wal, page_size, last, pages, frame_checksum):
    if shm is None:
        return {"status": "no_aportado"}
    # Only one native unix/win wal-index block, no mmap or index/lock use.
    if len(shm) != 32768 or shm[:48] != shm[48:96]:
        raise UnsupportedSQLite("SHM requiere un bloque de 32768 bytes con cabeceras idénticas")
    order = "<" if shm[:4] == struct.pack("<I", 3007000) else ">"
    word = lambda offset: struct.unpack_from(order + "I", shm, offset)[0]
    size = struct.unpack_from(order + "H", shm, 14)[0]
    if (word(0) != 3007000 or word(4) != 0 or shm[12] != 1 or shm[13] != (wal[3] & 1)
            or (65536 if size == 1 else size) != page_size
            or word(16) != last or word(20) != pages or shm[32:40] != wal[16:24]
            or (word(24), word(28)) != frame_checksum
            or (word(40), word(44)) != checksum(shm[:40], order)
            or word(96) > last or word(128) > last):
        raise ValueError("inconsistent shm header")
    return {"status": "cabeceras_contrastadas", "byte_order": "little" if order == "<" else "big",
            "mx_frame": last, "n_page": pages, "n_backfill": word(96),
            "index_hash_tables_and_locks": "no_interpretados"}


def reconstruct(parts):
    database, wal, shm = (parts[key] for key in ("database", "wal", "shm"))
    if len(database) < 100 or database[18:20] != b"\x02\x02":
        raise UnsupportedSQLite("Se requiere imagen principal en modo WAL")
    # Validate a private header copy only. Originals remain byte-identical.
    check_header(database[:18] + b"\x01\x01" + database[20:])
    page_size = int.from_bytes(database[16:18], "big")
    page_size = 65536 if page_size == 1 else page_size
    if len(wal) < 32:
        raise UnsupportedSQLite("WAL ausente o sin cabecera completa; no se supone estado actualizado")
    magic, version, size = struct.unpack_from(">III", wal)
    if magic not in (0x377f0682, 0x377f0683) or version != 3007000 or size != page_size:
        raise UnsupportedSQLite("Versión o tamaño de página WAL fuera del perfil")
    frame_size = 24 + page_size
    count, remainder = divmod(len(wal) - 32, frame_size)
    if remainder or not 1 <= count <= MAX_FRAMES:
        raise UnsupportedSQLite("WAL requiere 1..1024 frames completos; no se recorta corrupción")
    order = ">" if magic & 1 else "<"
    state = checksum(wal[:24], order)
    if state != struct.unpack_from(">II", wal, 24):
        raise ValueError("wal header checksum")
    pending, committed = {}, {}
    last, pages, commit_checksum, transactions = 0, 0, None, 0
    max_pages = MAX_SOURCE_BYTES // page_size
    for index in range(1, count + 1):
        offset = 32 + (index - 1) * frame_size
        header = wal[offset:offset + 24]
        page = wal[offset + 24:offset + frame_size]
        number, n_page = struct.unpack_from(">II", header)
        if not 1 <= number <= max_pages or n_page > max_pages or header[8:16] != wal[16:24]:
            raise ValueError("wal page or salt mismatch")
        state = checksum(page, order, checksum(header[:8], order, state))
        if state != struct.unpack_from(">II", header, 16):
            raise ValueError("wal frame checksum")
        pending[number] = page
        if n_page:
            committed.update(pending)
            committed = {p: data for p, data in committed.items() if p <= n_page}
            pending = {}
            last, pages, commit_checksum = index, n_page, state
            transactions += 1
    if not last:
        raise UnsupportedSQLite("WAL sin commit válido; no se publican páginas no confirmadas")
    shm_info = check_shm(shm, wal, page_size, last, pages, commit_checksum)
    old_pages = len(database) // page_size
    if any(p not in committed for p in range(old_pages + 1, pages + 1)):
        raise ValueError("missing growth pages")
    derived = bytearray(database[:pages * page_size])
    derived.extend(b"\0" * (pages * page_size - len(derived)))
    for number, page in committed.items():
        derived[(number - 1) * page_size:number * page_size] = page
    if (derived[:16] != database[:16] or derived[16:18] != database[16:18]
            or derived[18:20] != b"\x02\x02"):
        raise ValueError("derived header mismatch")
    # Explicit derived-image normalization for in-memory SQLite deserialization.
    derived[18:20] = b"\x01\x01"
    derived[28:32] = pages.to_bytes(4, "big")
    derived[92:96] = derived[24:28]
    check_header(derived)
    details = {"components": {role: None if data is None else {"sha256": sha256(data), "size_bytes": len(data)}
                               for role, data in parts.items()},
               "derived_sha256": sha256(derived), "derived_size_bytes": len(derived),
               "last_commit_frame": last, "frames_checked": count, "commits": transactions,
               "page_size": page_size, "database_pages": pages, "shm": shm_info,
               "transformations": ["overlay_committed_pages", "derived_header_18_19_to_1",
                                   "derived_header_28_31_commit_size", "derived_header_92_95_change_counter"]}
    return bytes(derived), details, count - last


class SQLiteSetReader:
    version = "1.0.0"
    dependencies = ()

    def __init__(self, platform, manifest=False):
        self.platform = platform
        self.identifier = "operia." + platform + (".manifest-wal-set" if manifest else ".sqlite-wal-set")
        self.format = "apple-backup-manifest-wal-set" if manifest else "sqlite-wal-catalog-set"
        self.inner = ManifestDatabaseReader() if manifest else SQLiteCatalogReader(platform)

    def read(self, source):
        warnings = ["Conjunto preservado; instantánea derivada del último commit, sin modificar originales ni abrir rutas.",
                    "Checksums y SHM no autentican asociación DB/WAL ni adquisición simultánea; procedencia requiere corroboración.",
                    "SHM: solo cabeceras contrastadas; sin índices hash, locks, marcas de lectores ni reconstrucción del SHM.",
                    "Sin borrados, versiones intermedias, journaling rollback, descifrado ni registros arbitrarios."]
        try:
            derived, details, tail = reconstruct(unpack_set(source.raw))
            result = self.inner.read(Source(source.id, "derived.db", self.platform, self.inner.format, derived))
            result.warnings = warnings + result.warnings[1:]
            if result.status not in ("analizado", "sin_registros"):
                return result
            for item in result.records:
                item["locator"] = "derived/" + item["locator"]
            for item in result.excluded:
                item["locator"] = "derived/" + item["locator"]
            result.records.insert(0, {"locator": "sqlite-set/provenance", "kind": "sqlite_snapshot_provenance",
                                     "original": details, "normalized": dict(details), "time": None})
            result.status = "analizado"
            if tail:
                result.excluded.append({"locator": "wal/frames:" + str(details["last_commit_frame"] + 1) + "-" + str(details["frames_checked"]),
                                        "reason": "Frames válidos posteriores al último commit; no aplicados"})
            return result
        except UnsupportedSQLite as error:
            return ReadResult("no_compatible", warnings=warnings + [str(error)])
        except (ValueError, TypeError, KeyError, OverflowError, MemoryError):
            return ReadResult("corrupto", warnings=warnings + ["Conjunto inválido, inconsistente o fuera de cuotas; no se publica instantánea parcial"])
