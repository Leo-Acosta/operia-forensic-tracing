from pathlib import Path

from operia.shared.hashing import file_md5, file_sha256


def sha256_file(path: Path) -> str:
    return file_sha256(path)


def md5_file(path: Path) -> str:
    return file_md5(path)

