"""Configuração de logs do DocAssist (biblioteca padrão `logging`, sem dependências).

Dois destinos, ambos em `LOG_DIR` (padrão `logs/`) e com rotação por tamanho:

- `docassist.log`      — log operacional (servidor, cliente de IA, erros), uma linha JSON
                         por evento, com nível, módulo, request_id e traceback quando houver.
- `interactions.jsonl` — uma linha JSON por pergunta respondida (ver rag._log_interaction).

O console recebe o mesmo log operacional em texto legível (ou JSON com LOG_FORMAT=json,
útil para coletores de log de container).

O `request_id` de cada requisição HTTP é guardado em um ContextVar e entra
automaticamente em toda linha de log emitida durante aquela requisição.
"""

from __future__ import annotations

import contextvars
import json
import logging
import logging.handlers
import sys
import threading
from datetime import datetime

import config

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

# Atributos padrão de LogRecord; o que não estiver aqui veio de `extra=` e vai para o JSON.
_STANDARD_ATTRS = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "request_id"}

_setup_lock = threading.Lock()
_configured = False
_interaction_logger: logging.Logger | None = None


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.fromtimestamp(record.created).astimezone().isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        entry.update({k: v for k, v in vars(record).items() if k not in _STANDARD_ATTRS})
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def _rotating_handler(filename: str) -> logging.Handler:
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    return logging.handlers.RotatingFileHandler(
        config.LOG_DIR / filename,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )


def setup_logging(console: bool = True) -> None:
    """Configura o logger `docassist` (idempotente). `console=False` mantém só o arquivo,
    para não misturar log com a saída da CLI."""
    global _configured
    with _setup_lock:
        if _configured:
            return
        logger = logging.getLogger("docassist")
        logger.setLevel(config.LOG_LEVEL)
        logger.propagate = False

        file_handler = _rotating_handler("docassist.log")
        file_handler.setFormatter(JsonFormatter())
        file_handler.addFilter(_RequestIdFilter())
        logger.addHandler(file_handler)

        if console:
            console_handler = logging.StreamHandler(sys.stderr)
            if config.LOG_FORMAT == "json":
                console_handler.setFormatter(JsonFormatter())
            else:
                console_handler.setFormatter(
                    logging.Formatter(
                        "%(asctime)s %(levelname)-7s [%(name)s] [%(request_id)s] %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S",
                    )
                )
            console_handler.addFilter(_RequestIdFilter())
            logger.addHandler(console_handler)

        _configured = True


def interaction_logger() -> logging.Logger:
    """Logger dedicado ao `interactions.jsonl`: grava a mensagem crua (já em JSON), com a
    trava do handler garantindo linhas inteiras mesmo com o servidor multi-thread."""
    global _interaction_logger
    with _setup_lock:
        if _interaction_logger is None:
            logger = logging.getLogger("docassist_interactions")
            logger.setLevel(logging.INFO)
            logger.propagate = False
            handler = _rotating_handler("interactions.jsonl")
            handler.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(handler)
            _interaction_logger = logger
        return _interaction_logger
