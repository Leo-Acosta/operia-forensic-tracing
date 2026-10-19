"""Create/verify a SQLite backup or restore to a NEW path. Never overwrites files.

Stop API/workers before backing up the accompanying storage files. This utility
preserves the database, including mobile BLOB originals; it does not copy storage.
"""
import argparse
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path):
    manifest = json.loads(path.with_suffix(path.suffix + ".manifest.json").read_text(encoding="utf-8"))
    if manifest["sha256"] != sha256(path):
        raise ValueError("El hash del respaldo no coincide")
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as database:
        if database.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("SQLite detectó errores de integridad")
    return manifest


def copy_database(source, destination):
    if not source.is_file():
        raise ValueError("No existe la base de origen")
    manifest_path = destination.with_suffix(destination.suffix + ".manifest.json")
    if destination.exists() or manifest_path.exists():
        raise ValueError("El destino debe ser nuevo; no se sobrescriben bases ni manifiestos")
    # Exclusive create prevents accidental replacement between the check and copy.
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb"):
        pass
    with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as src, closing(sqlite3.connect(destination)) as dst:
        src.backup(dst)
    manifest = {"schema": "operia-sqlite-backup/1", "sha256": sha256(destination),
                "size_bytes": destination.stat().st_size,
                "scope": "SQLite completo; no incluye archivos externos de storage"}
    with manifest_path.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)
    verify(destination)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("backup", "verify", "restore"))
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path, nargs="?")
    args = parser.parse_args()
    if args.action == "verify":
        result = verify(args.source)
    else:
        if not args.destination:
            parser.error("Se requiere destino nuevo")
        if args.action == "restore":
            verify(args.source)
        result = copy_database(args.source, args.destination)
    print(json.dumps({"ok": True, **result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
