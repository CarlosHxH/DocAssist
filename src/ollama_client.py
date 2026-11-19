"""Cliente HTTP minimalista para a API de IA (Ollama nativo ou API compatível com OpenAI).

Usa só urllib da biblioteca padrão. Provedor, URL, chave e modelos vêm de `config.py`
(variáveis de ambiente / `.env`).
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request

import config

logger = logging.getLogger("docassist.llm")


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
    log_fields = {"llm_url": url, "llm_model": payload.get("model")}
    start = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=config.REQUEST_TIMEOUT_SECONDS) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # O corpo do erro costuma trazer o motivo real (ex.: "model not found").
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        logger.warning(
            "API de IA respondeu HTTP %s em %s: %s", exc.code, path, detail,
            extra={**log_fields, "http_status": exc.code, "duration_seconds": round(time.monotonic() - start, 3)},
        )
        raise OllamaUnavailableError(f"API de IA em {url} respondeu HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        logger.warning(
            "Falha ao conectar à API de IA em %s: %s", path, exc.reason,
            extra={**log_fields, "duration_seconds": round(time.monotonic() - start, 3)},
        )
        raise OllamaUnavailableError(
            f"Não foi possível falar com a API de IA em {url}: {exc}"
        ) from exc
    except TimeoutError as exc:
        logger.warning(
            "Timeout após %.0fs chamando a API de IA em %s", config.REQUEST_TIMEOUT_SECONDS, path,
            extra={**log_fields, "duration_seconds": round(time.monotonic() - start, 3)},
        )
        raise OllamaUnavailableError(f"Timeout ao chamar a API de IA em {url}") from exc
    except json.JSONDecodeError as exc:
        logger.warning("API de IA devolveu JSON inválido em %s", path, extra=log_fields)
        raise OllamaUnavailableError(f"Resposta inválida (não-JSON) da API de IA em {url}") from exc

    logger.debug(
        "Chamada à API de IA %s concluída em %.2fs", path, time.monotonic() - start,
        extra={**log_fields, "duration_seconds": round(time.monotonic() - start, 3)},
    )
    return result


def is_available(timeout_seconds: float = 2.0) -> bool:
    """Checagem rápida (não usada para embed/generate) para o painel de status da UI."""
    path = "/api/tags" if config.LLM_PROVIDER == "ollama" else "/v1/models"
    request = urllib.request.Request(f"{config.LLM_API_URL}{path}", headers=_headers(), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        # DEBUG: a UI consulta o status a cada 30s; a mudança de estado é logada no servidor.
        logger.debug("Health check da API de IA falhou: %s", exc)
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
