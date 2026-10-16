"""Fresh export destinations: user filenames cannot select an existing file."""
from pathlib import Path
import re
from uuid import uuid4
from fastapi import HTTPException
from operia.core.config import settings


def new_export_path(filename: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._ -]{0,119}", filename) or filename.endswith((".", " ")):
        raise HTTPException(422, "Nombre de exportacion invalido; no se admiten rutas")
    root = settings.exports_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / (uuid4().hex + "-" + filename)
    with path.open("xb"):
        pass
    return path
