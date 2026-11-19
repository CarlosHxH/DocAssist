"""Servidor web local do DocAssist — expõe uma interface de chat em HTML/JS (static/) e
uma API JSON simples, reaproveitando o mesmo pipeline RAG de app.py/rag.py.

Usa o http.server da biblioteca padrão do Python (sem Flask/FastAPI).

Uso:
    python src/web_server.py [--host 127.0.0.1] [--port 8765]
"""

from __future__ import annotations

import argparse
import json
import logging
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import config
import log_setup
import ollama_client
import rag
import vector_store

logger = logging.getLogger("docassist.web")
access_logger = logging.getLogger("docassist.access")
client_logger = logging.getLogger("docassist.client")

STATIC_DIR = Path(__file__).parent / "static"
RAG_DIR = config.RAG_DIR

# Arquivos estáticos servidos tal como estão (sem build step), como em mini-chat-rag/static.
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
}


# Rotas consultadas o tempo todo (polling da UI, arquivos estáticos): só aparecem em DEBUG.
QUIET_PATHS = {"/api/health", "/api/live", "/favicon.ico", *STATIC_FILES}

# Limites do endpoint de erros do navegador, para não virar um vetor de spam no log.
CLIENT_LOG_MAX_BYTES = 8 * 1024
CLIENT_LOG_MAX_FIELD = 2000
CLIENT_LOG_LEVELS = {"error": logging.ERROR, "warning": logging.WARNING, "info": logging.INFO}

_ai_state_lock = threading.Lock()
_ai_available: bool | None = None


def _check_ai_available() -> bool:
    """Consulta a API de IA e loga só quando a disponibilidade muda (não a cada polling)."""
    global _ai_available
    available = ollama_client.is_available()
    with _ai_state_lock:
        if available != _ai_available:
            if available:
                logger.info("API de IA disponível em %s", config.LLM_API_URL)
            else:
                logger.warning("API de IA indisponível em %s", config.LLM_API_URL)
            _ai_available = available
    return available


def _load_doc_titles() -> dict[str, str]:
    """Mapeia cada arquivo do rag ao seu título (linha `# ...`), para a UI mostrar um
    nome legível em vez do nome de arquivo cru."""
    titles: dict[str, str] = {}
    for path in sorted(RAG_DIR.rglob("*.md")):
        # Mesmo filtro do ingest.py: pastas ocultas (ex.: .git, wikis clonadas) ficam de fora.
        if any(part.startswith(".") for part in path.relative_to(RAG_DIR).parts):
            continue
        name = path.relative_to(RAG_DIR).as_posix()
        try:
            first_line = path.read_text(encoding="utf-8").splitlines()[0]
        except (OSError, IndexError):
            first_line = ""
        titles[name] = first_line.lstrip("#").strip() if first_line.startswith("#") else path.stem
    return titles


def _sources_detail(result: rag.AnswerResult, doc_titles: dict[str, str]) -> list[dict]:
    """Resume, por documento-fonte, o trecho de maior similaridade usado na resposta.

    Inclui o texto completo do trecho para a interface mostrar a fonte recuperada por
    inteiro (em um `<details>`), não só o nome do arquivo.
    """
    best_by_source: dict[str, dict] = {}
    for chunk in result.retrieved:
        if chunk.score < rag.SIMILARITY_THRESHOLD:
            continue
        current = best_by_source.get(chunk.source)
        if current is None or chunk.score > current["score"]:
            best_by_source[chunk.source] = {
                "source": chunk.source,
                "title": doc_titles.get(chunk.source, chunk.source),
                "heading": chunk.heading,
                "text": chunk.text,
                "score": round(chunk.score, 3),
            }
    return sorted(best_by_source.values(), key=lambda item: item["score"], reverse=True)


class DocAssistHandler(BaseHTTPRequestHandler):
    # Carregados uma vez por processo (não por requisição), definidos em main().
    collection: vector_store.VectorIndex | None = None
    doc_names: list[str] = []
    doc_titles: dict[str, str] = {}

    def handle_one_request(self) -> None:
        # Cada requisição ganha um request_id, que entra em todas as linhas de log emitidas
        # durante ela, no interactions.jsonl e no header X-Request-ID da resposta.
        self.command = None
        self._status: int | None = None
        self._started = time.monotonic()
        token = log_setup.request_id_var.set(uuid.uuid4().hex[:12])
        try:
            super().handle_one_request()
        finally:
            if self.command:  # None quando a conexão fecha sem uma nova requisição
                self._log_access()
            log_setup.request_id_var.reset(token)

    def _log_access(self) -> None:
        status = self._status or 0
        path = self.path.split("?", 1)[0]
        if status >= 500:
            level = logging.ERROR
        elif status >= 400:
            level = logging.WARNING
        elif path in QUIET_PATHS:
            level = logging.DEBUG
        else:
            level = logging.INFO
        duration_ms = (time.monotonic() - self._started) * 1000
        access_logger.log(
            level,
            "%s %s %s %.0fms",
            self.command, path, status, duration_ms,
            extra={
                "method": self.command,
                "path": path,
                "http_status": status,
                "duration_ms": round(duration_ms, 1),
                "client_ip": self.client_address[0],
                "user_agent": self.headers.get("User-Agent", "") if self.headers else "",
            },
        )

    def send_response(self, code: int, message: str | None = None) -> None:
        self._status = code
        super().send_response(code, message)
        self.send_header("X-Request-ID", log_setup.request_id_var.get())

    def log_request(self, code="-", size="-") -> None:  # noqa: ARG002
        pass  # substituído por _log_access, que inclui duração e request_id

    def log_error(self, format: str, *args) -> None:  # noqa: A002 (nome da API padrão)
        # O status de erro já sai no log de acesso; aqui só o detalhe, em DEBUG.
        logger.debug(format, *args)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        logger.debug(format, *args)

    def _write_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self._send_body(body)

    def _send_body(self, body: bytes) -> None:
        # O navegador pode fechar a conexão antes da resposta (recarregar a página, trocar
        # de aba); não é erro do servidor, então não deixa o traceback poluir o console.
        try:
            self.wfile.write(body)
        except ConnectionError:
            logger.debug("Cliente fechou a conexão antes de receber a resposta")
            self.close_connection = True

    def do_GET(self) -> None:  # noqa: N802 (nome exigido pela API do http.server)
        if self.path in STATIC_FILES:
            filename, content_type = STATIC_FILES[self.path]
            body = (STATIC_DIR / filename).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self._send_body(body)
            return

        if self.path == "/api/live":
            # Liveness para o healthcheck do container/proxy: não consulta a API de IA.
            self._write_json({"status": "ok"})
            return

        if self.path == "/api/health":
            doc_titles = [self.doc_titles.get(name, name) for name in self.doc_names]
            self._write_json(
                {
                    "ready": _check_ai_available(),
                    "generation_model": config.GENERATION_MODEL,
                    "embedding_model": config.EMBEDDING_MODEL,
                    "docs": len(self.doc_names),
                    "doc_names": self.doc_names,
                    "doc_titles": doc_titles,
                    "chunks": self.collection.count() if self.collection else 0,
                }
            )
            return

        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        self.send_error(404, "Não encontrado")

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/client-log":
            self._handle_client_log()
            return
        if self.path != "/api/ask":
            self.send_error(404, "Não encontrado")
            return

        length = int(self.headers.get("Content-Length", 0) or 0)
        raw_body = self.rfile.read(length) if length else b""

        try:
            data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.warning("Corpo inválido em /api/ask (%d bytes)", len(raw_body))
            self._write_json({"error": "Corpo da requisição não é um JSON válido."}, status=400)
            return

        question = str(data.get("question", ""))

        try:
            result = rag.answer(question, collection=self.collection, channel="web")
        except Exception:  # falha inesperada não deve derrubar o servidor
            logger.exception("Erro inesperado ao responder pergunta")
            self._write_json(
                {
                    "answer": "Ocorreu um erro inesperado ao processar sua pergunta. Tente novamente.",
                    "status": "erro",
                    "sources": [],
                    "latency_seconds": 0,
                    "request_id": log_setup.request_id_var.get(),
                },
                status=500,
            )
            return

        self._write_json(
            {
                "answer": result.answer,
                "status": result.status,
                "sources": result.sources,
                "sources_detail": _sources_detail(result, self.doc_titles),
                "latency_seconds": round(result.latency_seconds, 2),
                "request_id": log_setup.request_id_var.get(),
            }
        )

    def _handle_client_log(self) -> None:
        """Recebe erros de JavaScript do navegador (ver reportClientError em app.js)."""
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0 or length > CLIENT_LOG_MAX_BYTES:
            self.send_error(413 if length > 0 else 400, "Relato de erro inválido")
            return
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("esperado um objeto JSON")
        except (UnicodeDecodeError, ValueError):
            self.send_error(400, "Relato de erro inválido")
            return

        fields = {
            f"client_{key}": str(data.get(key, ""))[:CLIENT_LOG_MAX_FIELD]
            for key in ("message", "source", "stack", "url", "user_agent")
        }
        level = CLIENT_LOG_LEVELS.get(str(data.get("level", "error")), logging.ERROR)
        client_logger.log(level, "Erro no navegador: %s", fields["client_message"], extra=fields)
        self.send_response(204)
        self.end_headers()


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor web do DocAssist")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    log_setup.setup_logging()

    try:
        DocAssistHandler.collection = rag.load_index()
    except FileNotFoundError as exc:
        logger.error("Índice vetorial não encontrado: %s", exc)
        raise SystemExit(1) from exc
    except vector_store.VectorStoreUnavailableError as exc:
        logger.error("Banco vetorial indisponível: %s", exc)
        raise SystemExit(1) from exc
    DocAssistHandler.doc_names = vector_store.list_sources(DocAssistHandler.collection)
    DocAssistHandler.doc_titles = _load_doc_titles()

    # Configuração efetiva no início do log (sem a chave de API), para facilitar o suporte.
    logger.info(
        "Configuração: provedor=%s api=%s banco=%s embedding=%s geração=%s top_k=%s limiar=%s logs=%s nível=%s",
        config.LLM_PROVIDER, config.LLM_API_URL, vector_store.describe(), config.EMBEDDING_MODEL, config.GENERATION_MODEL,
        config.TOP_K, config.SIMILARITY_THRESHOLD, config.LOG_DIR, config.LOG_LEVEL,
    )
    _check_ai_available()

    server = ThreadingHTTPServer((args.host, args.port), DocAssistHandler)
    url = f"http://{args.host}:{args.port}"
    logger.info(
        "DocAssist rodando em %s (%d documentos, %d trechos indexados). Ctrl+C para encerrar.",
        url, len(DocAssistHandler.doc_names), DocAssistHandler.collection.count(),
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Encerrando servidor...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
