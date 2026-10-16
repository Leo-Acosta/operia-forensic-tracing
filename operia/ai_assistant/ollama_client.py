import json
import http.client
from operia.core.config import settings

class OllamaUnavailable(RuntimeError):
    pass


def generate_with_ollama(prompt: str, model: str = "mistral", base_url: str = "http://127.0.0.1:11434", timeout: int = 12) -> str:
    if not settings.local_ai_enabled or base_url != "http://127.0.0.1:11434":
        raise OllamaUnavailable("Conector IA local deshabilitado o destino no autorizado")
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    if len(payload) > 2 * 1024 * 1024:
        raise OllamaUnavailable("Solicitud IA supera limite")
    connection = http.client.HTTPConnection("127.0.0.1", 11434, timeout=min(max(timeout, 1), 15))
    try:
        connection.request("POST", "/api/generate", body=payload, headers={"Content-Type": "application/json", "Accept-Encoding": "identity"})
        response = connection.getresponse()
        if response.status != 200 or response.getheader("Content-Encoding", "identity") != "identity":
            raise OllamaUnavailable("Respuesta IA rechazada")
        raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise OllamaUnavailable("Respuesta IA supera limite")
        data = json.loads(raw)
        if not isinstance(data, dict) or not isinstance(data.get("response", ""), str):
            raise ValueError()
        return data.get("response", "")
    except (OSError, http.client.HTTPException, ValueError):
        raise OllamaUnavailable("Conector IA local no disponible") from None
    finally:
        connection.close()
