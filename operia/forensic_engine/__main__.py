"""Standalone deterministic CLI. All paths are local operator-selected inputs."""
import argparse
from pathlib import Path

from operia.forensic_engine.analysis import analyze
from operia.forensic_engine.canonical import MAX_SOURCE_BYTES, canonical_bytes
from operia.forensic_engine.contracts import Source
from operia.forensic_engine.readers import reader_order


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--platform", required=True, choices=("ios", "android"))
    parser.add_argument("--format", required=True, choices=tuple(reader.format for reader in reader_order()))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--indicators", type=Path)
    parser.add_argument("--demo-rules", action="store_true")
    args = parser.parse_args()
    if args.source.is_symlink() or not args.source.is_file() or args.source.stat().st_size > MAX_SOURCE_BYTES:
        parser.error("Fuente debe ser un archivo regular de hasta 5 MiB sin enlace simbólico")
    source = Source("input", args.source.name, args.platform, args.format, args.source.read_bytes())
    indicator_bytes = None
    if args.indicators:
        if args.indicators.is_symlink() or not args.indicators.is_file() or args.indicators.stat().st_size > 256 * 1024:
            parser.error("Indicadores deben ser un archivo regular de hasta 256 KiB")
        indicator_bytes = args.indicators.read_bytes()
    output = canonical_bytes(analyze(source, indicator_bytes, args.demo_rules))
    with args.output.open("xb") as stream:
        stream.write(output)


if __name__ == "__main__":
    main()
