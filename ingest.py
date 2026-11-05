"""Lê os documentos fictícios em corpus/, divide em trechos (chunks) por seção e gera
embeddings locais via Ollama, salvando tudo em index.json.

Uso:
    python ingest.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from ollama_client import OllamaUnavailableError, embed

CORPUS_DIR = Path(__file__).parent / "corpus"
INDEX_PATH = Path(__file__).parent / "index.json"
EMBEDDING_MODEL = "all-minilm"

HEADING_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)

# O modelo de embeddings local (all-minilm) tem uma janela de contexto pequena; chunks
# maiores que isso causam erro "input length exceeds the context length" na API do Ollama.
# Mantemos uma margem de segurança bem abaixo do limite real do modelo.
MAX_CHUNK_CHARS = 500


def _split_long_text(text: str, max_chars: int) -> list[str]:
    """Divide um texto longo em pedaços menores, tentando respeitar parágrafos e linhas."""
    if len(text) <= max_chars:
        return [text]

    paragraphs = text.split("\n\n")
    pieces: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) > max_chars and current:
            pieces.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        pieces.append(current)

    # Parágrafos individuais que ainda excedem o limite (ex.: listas longas) são
    # quebrados por linha.
    final_pieces: list[str] = []
    for piece in pieces:
        if len(piece) <= max_chars:
            final_pieces.append(piece)
            continue
        lines = piece.split("\n")
        current_line_group = ""
        for line in lines:
            candidate = f"{current_line_group}\n{line}".strip() if current_line_group else line
            if len(candidate) > max_chars and current_line_group:
                final_pieces.append(current_line_group)
                current_line_group = line
            else:
                current_line_group = candidate
        if current_line_group:
            final_pieces.append(current_line_group)

    return final_pieces


def chunk_markdown(text: str) -> list[tuple[str, str]]:
    """Divide o markdown em (titulo_da_secao, conteudo) usando headings de nível 2 (##).

    O conteúdo antes do primeiro '##' (geralmente só o título H1 e uma introdução curta)
    vira um chunk próprio chamado "Introdução". Seções grandes demais para o modelo de
    embeddings são subdivididas, recebendo um sufixo "(parte N)" no título da seção.
    """
    matches = list(HEADING_RE.finditer(text))
    sections: list[tuple[str, str]] = []

    if not matches:
        sections.append(("Documento completo", text.strip()))
    else:
        intro = text[: matches[0].start()].strip()
        if intro:
            sections.append(("Introdução", intro))

        for i, match in enumerate(matches):
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            heading = match.group(1).strip()
            body = text[start:end].strip()
            sections.append((heading, body))

    chunks: list[tuple[str, str]] = []
    for heading, body in sections:
        pieces = _split_long_text(body, MAX_CHUNK_CHARS)
        if len(pieces) == 1:
            chunks.append((heading, pieces[0]))
        else:
            for i, piece in enumerate(pieces, start=1):
                chunks.append((f"{heading} (parte {i})", piece))

    return chunks


def main() -> None:
    if not CORPUS_DIR.exists():
        print(f"Pasta de corpus não encontrada: {CORPUS_DIR}", file=sys.stderr)
        sys.exit(1)

    doc_paths = sorted(CORPUS_DIR.glob("*.md"))
    if not doc_paths:
        print(f"Nenhum documento .md encontrado em {CORPUS_DIR}", file=sys.stderr)
        sys.exit(1)

    records = []
    for doc_path in doc_paths:
        text = doc_path.read_text(encoding="utf-8")
        for heading, body in chunk_markdown(text):
            if not body:
                continue
            full_text = f"# {doc_path.stem}\n## {heading}\n{body}"
            try:
                vector = embed(full_text, model=EMBEDDING_MODEL)
            except OllamaUnavailableError as exc:
                print(f"ERRO: {exc}", file=sys.stderr)
                print(
                    "O Ollama precisa estar rodando localmente (comando: `ollama serve`) "
                    "e o modelo de embeddings disponível (`ollama pull all-minilm`).",
                    file=sys.stderr,
                )
                sys.exit(1)
            records.append(
                {
                    "id": len(records),
                    "source": doc_path.name,
                    "heading": heading,
                    "text": body,
                    "embedding": vector,
                }
            )
        print(f"Processado: {doc_path.name} (total de chunks acumulados: {len(records)})")

    INDEX_PATH.write_text(
        json.dumps({"embedding_model": EMBEDDING_MODEL, "chunks": records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nÍndice salvo em {INDEX_PATH} com {len(records)} chunks de {len(doc_paths)} documentos.")


if __name__ == "__main__":
    main()
