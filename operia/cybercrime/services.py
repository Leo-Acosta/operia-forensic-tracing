import shutil
import subprocess
from pathlib import Path
from typing import Any


def verify_tool(executable_path: str | None, fallback_name: str) -> tuple[str, str | None]:
    if executable_path and Path(executable_path).exists():
        return "encontrada", executable_path
    discovered = shutil.which(fallback_name)
    if discovered:
        return "encontrada", discovered
    return "no encontrada", executable_path


def run_lab_command(command: str, capture_output: bool = True, timeout_seconds: int = 60) -> dict[str, Any]:
    if capture_output:
        completed = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        output = "\n".join(part for part in [completed.stdout, completed.stderr] if part).strip()
        return {
            "status": "completado" if completed.returncode == 0 else "completado con advertencias",
            "return_code": completed.returncode,
            "output": output[-12000:],
        }
    subprocess.Popen(command, shell=True)
    return {
        "status": "lanzamiento solicitado",
        "return_code": None,
        "output": "Herramienta abierta como proceso externo. Importar resultados manualmente al finalizar.",
    }

