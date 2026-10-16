from operia.security.outbound import local_ai
from operia.security.errors import ConnectorRejected

class OllamaUnavailable(RuntimeError):
    pass


def generate_with_ollama(prompt: str, model: str = "mistral", base_url: str = "http://127.0.0.1:11434", timeout: int = 12) -> str:
    if base_url != "http://127.0.0.1:11434":
        raise OllamaUnavailable("Destino IA no autorizado")
    try:
        return local_ai(prompt, model, timeout)
    except ConnectorRejected as error:
        raise OllamaUnavailable(str(error)) from None
