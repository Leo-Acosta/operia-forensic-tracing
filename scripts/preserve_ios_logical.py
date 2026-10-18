"""Package explicitly selected preserved iOS files; never traverse backup paths."""
import argparse
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from operia.forensic_engine.canonical import MAX_SOURCE_BYTES
from operia.forensic_engine.logical_files import MANIFEST_FORMATS, MAX_FILES, MAX_FILE_BYTES, pack_logical


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-format", choices=MANIFEST_FORMATS, default=MANIFEST_FORMATS[0])
    parser.add_argument("--file", action="append", required=True, help="fileID=path; explicit preserved copy")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= len(args.file) <= MAX_FILES:
        parser.error("Seleccionar 1..32 archivos")
    selected, seen = [], set()
    for item in args.file:
        file_id, separator, path = item.partition("=")
        if not separator or not re.fullmatch(r"[0-9a-f]{40}", file_id) or file_id in seen:
            parser.error("fileID inválido o duplicado")
        seen.add(file_id); selected.append((file_id, Path(path)))
    def read(path, limit):
        if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
            parser.error("Fuente debe ser una copia regular sin enlace y dentro de cuota")
        with path.open("rb") as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            parser.error("Fuente supera cuota")
        return raw
    package = pack_logical(read(args.manifest, MAX_SOURCE_BYTES),
                           [(file_id, read(path, MAX_FILE_BYTES)) for file_id, path in selected], args.manifest_format)
    with args.output.open("xb") as stream:
        stream.write(package)


if __name__ == "__main__":
    main()
