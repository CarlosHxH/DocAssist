"""Cliente HTTP minimalista para a API de IA (Ollama nativo ou API compatível com OpenAI).

Usa só urllib da biblioteca padrão. Provedor, URL, chave e modelos vêm de `config.py`
(variáveis de ambiente / `.env`).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import config


class OllamaUnavailableError(RuntimeError):
    """Levantado quando a API de IA não responde (parada, offline, timeout, erro HTTP)."""


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if config.LLM_API_KEY:
        headers["Authorization"] = f"Bearer {config.LLM_API_KEY}"
    return headers


def _post(path: str, payload: dict) -> dict:
    url = f"{config.LLM_API_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=_headers(), method="POST")
    try:
        with urllib.request.urlopen(request, timeout=config.REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise OllamaUnavailableError(
            f"Não foi possível falar com a API de IA em {url}: {exc}"
        ) from exc
    except TimeoutError as exc:
        raise OllamaUnavailableError(f"Timeout ao chamar a API de IA em {url}") from exc


def is_available(timeout_seconds: float = 2.0) -> bool:
    """Checagem rápida (não usada para embed/generate) para o painel de status da UI."""
    path = "/api/tags" if config.LLM_PROVIDER == "ollama" else "/v1/models"
    request = urllib.request.Request(f"{config.LLM_API_URL}{path}", headers=_headers(), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def embed(text: str, model: str | None = None) -> list[float]:
    model = model or config.EMBEDDING_MODEL
    if config.LLM_PROVIDER == "ollama":
        result = _post("/api/embeddings", {"model": model, "prompt": text})
        embedding = result.get("embedding")
    else:
        result = _post("/v1/embeddings", {"model": model, "input": text})
        embedding = (result.get("data") or [{}])[0].get("embedding")
    if not embedding:
        raise OllamaUnavailableError(f"Resposta de embedding vazia/inesperada: {result}")
    return embedding


def generate(prompt: str, model: str | None = None) -> str:
    model = model or config.GENERATION_MODEL
    if config.LLM_PROVIDER == "ollama":
        result = _post(
            "/api/generate",
            {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": config.GENERATION_TEMPERATURE},
            },
        )
        response = result.get("response")
    else:
        result = _post(
            "/v1/chat/completions",
            {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": config.GENERATION_TEMPERATURE,
            },
        )
        response = ((result.get("choices") or [{}])[0].get("message") or {}).get("content")
    if response is None:
        raise OllamaUnavailableError(f"Resposta de geração vazia/inesperada: {result}")
    return response.strip()
