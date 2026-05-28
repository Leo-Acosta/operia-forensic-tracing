import json
from urllib.error import URLError
from urllib.request import Request, urlopen


class OllamaUnavailable(RuntimeError):
    pass


def generate_with_ollama(prompt: str, model: str = "mistral", base_url: str = "http://127.0.0.1:11434", timeout: int = 12) -> str:
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    request = Request(f"{base_url}/api/generate", data=payload, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (TimeoutError, URLError) as exc:
        raise OllamaUnavailable("Ollama no esta disponible en el entorno local.") from exc
    return str(data.get("response") or "")
