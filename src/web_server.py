"""Servidor web local do DocAssist — expõe uma interface de chat em HTML/JS (static/) e
uma API JSON simples, reaproveitando o mesmo pipeline RAG de app.py/rag.py.

Usa o http.server da biblioteca padrão do Python (sem Flask/FastAPI).

Uso:
    python src/web_server.py [--host 127.0.0.1] [--port 8765]
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import chromadb

import config
import ollama_client
import rag
import vector_store

STATIC_DIR = Path(__file__).parent / "static"
RAG_DIR = config.RAG_DIR

# Arquivos estáticos servidos tal como estão (sem build step), como em mini-chat-rag/static.
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
}


def _load_doc_titles() -> dict[str, str]:
    """Mapeia cada arquivo do rag ao seu título (linha `# ...`), para a UI mostrar um
    nome legível em vez do nome de arquivo cru."""
    titles: dict[str, str] = {}
    for path in sorted(RAG_DIR.rglob("*.md")):
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
    collection: chromadb.Collection | None = None
    doc_names: list[str] = []
    doc_titles: dict[str, str] = {}

    def log_message(self, format: str, *args) -> None:  # noqa: A002 (nome da API padrão)
        # Log de acesso HTTP simples no console, em vez do formato padrão do http.server.
        print(f"[web] {self.address_string()} - {format % args}")

    def _write_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (nome exigido pela API do http.server)
        if self.path in STATIC_FILES:
            filename, content_type = STATIC_FILES[self.path]
            body = (STATIC_DIR / filename).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/api/health":
            doc_titles = [self.doc_titles.get(name, name) for name in self.doc_names]
            self._write_json(
                {
                    "ready": ollama_client.is_available(),
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
        if self.path != "/api/ask":
            self.send_error(404, "Não encontrado")
            return

        length = int(self.headers.get("Content-Length", 0) or 0)
        raw_body = self.rfile.read(length) if length else b""

        try:
            data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._write_json({"error": "Corpo da requisição não é um JSON válido."}, status=400)
            return

        question = str(data.get("question", ""))

        try:
            result = rag.answer(question, collection=self.collection)
        except Exception as exc:  # falha inesperada não deve derrubar o servidor
            print(f"[web] erro inesperado ao responder pergunta: {exc!r}")
            self._write_json(
                {
                    "answer": "Ocorreu um erro inesperado ao processar sua pergunta. Tente novamente.",
                    "status": "erro",
                    "sources": [],
                    "latency_seconds": 0,
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
            }
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor web do DocAssist")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    try:
        DocAssistHandler.collection = rag.load_index()
    except FileNotFoundError as exc:
        print(f"Erro: {exc}")
        raise SystemExit(1) from exc
    DocAssistHandler.doc_names = vector_store.list_sources(DocAssistHandler.collection)
    DocAssistHandler.doc_titles = _load_doc_titles()

    server = ThreadingHTTPServer((args.host, args.port), DocAssistHandler)
    url = f"http://{args.host}:{args.port}"
    print(f"DocAssist rodando em {url}  ({DocAssistHandler.collection.count()} trechos indexados)")
    print("Pressione Ctrl+C para encerrar.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando servidor...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
