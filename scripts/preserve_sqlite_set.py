"""Package explicitly selected preserved copies, never discover sidecars or open SQLite."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from operia.forensic_engine.canonical import MAX_SOURCE_BYTES
from operia.forensic_engine.wal_readers import pack_set


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--wal", type=Path, required=True)
    parser.add_argument("--shm", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    def read(path):
        if path is None:
            return None
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_SOURCE_BYTES:
            parser.error("Cada fuente debe ser una copia regular sin enlace, de hasta 5 MiB")
        with path.open("rb") as stream:
            raw = stream.read(MAX_SOURCE_BYTES + 1)
        if len(raw) > MAX_SOURCE_BYTES:
            parser.error("Fuente supera cuota")
        return raw
    raw = pack_set(read(args.database), read(args.wal), read(args.shm))
    with args.output.open("xb") as stream:
        stream.write(raw)


if __name__ == "__main__":
    main()
