"""Cliente HTTP minimalista para a API local do Ollama (http://localhost:11434).

Só usa a biblioteca padrão do Python (urllib) para evitar qualquer dependência externa
(ver README: isso é uma decisão de projeto para contornar a falta de wheels pré-compiladas
de pacotes como numpy/chromadb para a versão de Python usada no desenvolvimento, e para
manter a reprodutibilidade simples).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

# Configurável via variável de ambiente para funcionar tanto localmente (localhost) quanto
# em Docker Compose, onde o Ollama roda em outro container (ex.: http://ollama:11434).
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
# Geração em CPU com múltiplas requisições concorrentes pode levar mais de 1 minuto;
# o limite abaixo dá margem confortável sem deixar o usuário esperando indefinidamente.
REQUEST_TIMEOUT_SECONDS = 120


class OllamaUnavailableError(RuntimeError):
    """Levantado quando o serviço Ollama local não responde (parado, offline, timeout)."""


def _post(path: str, payload: dict) -> dict:
    url = f"{OLLAMA_HOST}{path}"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise OllamaUnavailableError(
            f"Não foi possível falar com o Ollama em {url}: {exc}"
        ) from exc
    except TimeoutError as exc:
        raise OllamaUnavailableError(f"Timeout ao chamar o Ollama em {url}") from exc


def is_available(timeout_seconds: float = 2.0) -> bool:
    """Checagem rápida (não usada para embed/generate) para o painel de status da UI."""
    request = urllib.request.Request(f"{OLLAMA_HOST}/api/tags", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def embed(text: str, model: str = "all-minilm") -> list[float]:
    result = _post("/api/embeddings", {"model": model, "prompt": text})
    embedding = result.get("embedding")
    if not embedding:
        raise OllamaUnavailableError(f"Resposta de embedding vazia/inesperada: {result}")
    return embedding


def generate(prompt: str, model: str = "qwen2.5:3b") -> str:
    result = _post(
        "/api/generate",
        {"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.1}},
    )
    response = result.get("response")
    if response is None:
        raise OllamaUnavailableError(f"Resposta de geração vazia/inesperada: {result}")
    return response.strip()
