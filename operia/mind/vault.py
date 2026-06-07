import re
from pathlib import Path

from operia.core.config import settings


VAULT_FOLDERS = [
    "00_Index",
    "01_Casos",
    "02_Documentos",
    "03_Evidencia",
    "04_Notas",
    "05_Hallazgos",
    "06_Hipotesis",
    "07_Matrices",
    "08_Informes",
    "09_Prompts",
    "10_Agentes",
    "11_Auditoria",
    "12_Contexto",
    "13_Grafo",
    "14_Legal",
    "15_Cybercrime",
    "16_Blockchain",
    "17_Deepfake",
    "18_IoT",
    "19_Exportaciones",
]

NOTE_FOLDERS = {
    "caso": "01_Casos",
    "documento": "02_Documentos",
    "evidencia": "03_Evidencia",
    "nota": "04_Notas",
    "hallazgo": "05_Hallazgos",
    "hipotesis": "06_Hipotesis",
    "matriz": "07_Matrices",
    "informe": "08_Informes",
    "auditoria": "11_Auditoria",
    "legal": "14_Legal",
    "cybercrime": "15_Cybercrime",
    "blockchain": "16_Blockchain",
    "deepfake": "17_Deepfake",
    "iot": "18_IoT",
    "exportacion": "19_Exportaciones",
}


def vault_root() -> Path:
    return settings.storage_dir.parent / "memory_vault"


def ensure_vault() -> Path:
    root = vault_root()
    root.mkdir(parents=True, exist_ok=True)
    for folder in VAULT_FOLDERS:
        (root / folder).mkdir(parents=True, exist_ok=True)
    index_path = root / "00_Index" / "OPERIA Mind.md"
    if not index_path.exists():
        index_path.write_text(
            "# OPERIA Mind\n\nMemoria forense persistente compatible con Obsidian.\n",
            encoding="utf-8",
        )
    return root


def slugify(value: str, fallback: str = "nota") -> str:
    normalized = re.sub(r"[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ_-]+", "-", value.strip())
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-_")
    return normalized[:120] or fallback


def note_folder(note_type: str) -> str:
    return NOTE_FOLDERS.get(note_type.lower().strip(), "04_Notas")


def write_note(relative_path: str, markdown: str) -> Path:
    root = ensure_vault()
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path


def write_support_file(relative_path: str, content: str) -> Path:
    return write_note(relative_path, content)
