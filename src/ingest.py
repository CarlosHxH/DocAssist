"""Lê os documentos .md em corpus/ (recursivamente), divide em trechos (chunks) por seção,
gera embeddings via API de IA e grava tudo no ChromaDB persistente (SQLite).

Uso:
    python src/ingest.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import config
import vector_store
from ollama_client import OllamaUnavailableError, embed

CORPUS_DIR = config.CORPUS_DIR

HEADING_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)

# O modelo de embeddings local (all-minilm) tem uma janela de contexto pequena; chunks
# maiores que isso causam erro "input length exceeds the context length" na API do Ollama.
# Mantemos uma margem de segurança bem abaixo do limite real do modelo (ver MAX_CHUNK_CHARS
# no .env).
MAX_CHUNK_CHARS = config.MAX_CHUNK_CHARS


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

    # Busca recursiva (ex.: wikis clonadas em subpastas), ignorando pastas ocultas como .git.
    doc_paths = sorted(
        path
        for path in CORPUS_DIR.rglob("*.md")
        if not any(part.startswith(".") for part in path.relative_to(CORPUS_DIR).parts)
    )
    if not doc_paths:
        print(f"Nenhum documento .md encontrado em {CORPUS_DIR}", file=sys.stderr)
        sys.exit(1)

    ids: list[str] = []
    documents: list[str] = []
    embeddings: list[list[float]] = []
    metadatas: list[dict] = []
    for doc_path in doc_paths:
        source = doc_path.relative_to(CORPUS_DIR).as_posix()
        text = doc_path.read_text(encoding="utf-8")
        for heading, body in chunk_markdown(text):
            if not body:
                continue
            full_text = f"# {doc_path.stem}\n## {heading}\n{body}"
            try:
                vector = embed(full_text)
            except OllamaUnavailableError as exc:
                print(f"ERRO: {exc}", file=sys.stderr)
                print(
                    f"A API de IA precisa estar acessível em {config.LLM_API_URL} e o modelo "
                    f"de embeddings '{config.EMBEDDING_MODEL}' disponível "
                    f"(no Ollama: `ollama pull {config.EMBEDDING_MODEL}`).",
                    file=sys.stderr,
                )
                sys.exit(1)
            ids.append(str(len(ids)))
            documents.append(body)
            embeddings.append(vector)
            metadatas.append({"source": source, "heading": heading})
        print(f"Processado: {source} (total de chunks acumulados: {len(ids)})")

    collection = vector_store.recreate_collection()
    # Inserção em lotes para respeitar o limite de batch do Chroma em corpora grandes.
    batch_size = 1000
    for start in range(0, len(ids), batch_size):
        end = start + batch_size
        collection.add(
            ids=ids[start:end],
            documents=documents[start:end],
            embeddings=embeddings[start:end],
            metadatas=metadatas[start:end],
        )
    print(
        f"\nÍndice salvo no ChromaDB ({config.CHROMA_PATH}, coleção "
        f"'{config.CHROMA_COLLECTION}') com {len(ids)} chunks de {len(doc_paths)} documentos."
    )


if __name__ == "__main__":
    main()
