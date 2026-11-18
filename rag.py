"""Núcleo do pipeline RAG: recuperação (busca vetorial no ChromaDB) + geração grounded.

Mantido separado da interface (CLI/Streamlit) para que app.py e eval.py reusem a mesma
lógica, e para que os testes de cenário (ver tests/) possam chamar `answer()` diretamente.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import chromadb

import config
import vector_store
from ollama_client import OllamaUnavailableError, embed, generate

LOG_PATH = Path(__file__).parent / "logs" / "interactions.jsonl"

TOP_K = config.TOP_K
# Abaixo deste score de similaridade de cosseno, consideramos que não há contexto
# relevante o suficiente na base e o sistema deve recusar responder em vez de alucinar.
SIMILARITY_THRESHOLD = config.SIMILARITY_THRESHOLD

NO_CONTEXT_MESSAGE = (
    "Não encontrei essa informação na base de documentação disponível. "
    "Reformule a pergunta ou consulte a documentação completa do sistema."
)

SYSTEM_INSTRUCTIONS = """Você é um assistente que responde perguntas de desenvolvedores \
sobre padrões internos de TI, usando APENAS as informações fornecidas no CONTEXTO abaixo.

Regras obrigatórias:
- Responda em português, de forma direta e objetiva.
- Use somente o que está no CONTEXTO. Nunca invente informação que não esteja lá.
- Se o CONTEXTO não tiver informação suficiente para responder, responda exatamente:
  "{no_context}"
- Ao final da resposta, cite entre colchetes o(s) documento(s) de origem usados, no \
formato [fonte: nome-do-documento.md].
""".format(no_context=NO_CONTEXT_MESSAGE)


@dataclass
class RetrievedChunk:
    score: float
    source: str
    heading: str
    text: str


@dataclass
class AnswerResult:
    question: str
    answer: str
    status: str  # "ok" | "sem_contexto" | "erro"
    sources: list[str] = field(default_factory=list)
    retrieved: list[RetrievedChunk] = field(default_factory=list)
    latency_seconds: float = 0.0
    error: str | None = None


def load_index() -> chromadb.Collection:
    return vector_store.get_collection()


def retrieve(
    question_embedding: list[float], collection: chromadb.Collection, top_k: int = TOP_K
) -> list[RetrievedChunk]:
    result = collection.query(
        query_embeddings=[question_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    # Coleção criada com espaço "cosine": distância = 1 - similaridade de cosseno.
    return [
        RetrievedChunk(
            score=1.0 - distance,
            source=metadata["source"],
            heading=metadata["heading"],
            text=document,
        )
        for document, metadata, distance in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0]
        )
    ]


def _build_prompt(question: str, retrieved: list[RetrievedChunk]) -> str:
    context = "\n\n".join(
        f"[Documento: {chunk.source} | Seção: {chunk.heading}]\n{chunk.text}" for chunk in retrieved
    )
    return f"{SYSTEM_INSTRUCTIONS}\n\nCONTEXTO:\n{context}\n\nPERGUNTA: {question}\n\nRESPOSTA:"


def _log_interaction(result: AnswerResult) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "question": result.question,
        "status": result.status,
        "answer": result.answer,
        "sources": result.sources,
        "retrieved_scores": [round(c.score, 4) for c in result.retrieved],
        "latency_seconds": round(result.latency_seconds, 3),
        "error": result.error,
    }
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def answer(question: str, collection: chromadb.Collection | None = None) -> AnswerResult:
    start = time.monotonic()
    question = (question or "").strip()

    if not question:
        result = AnswerResult(
            question=question,
            answer="Pergunta vazia. Digite uma pergunta sobre os padrões internos de TI.",
            status="sem_contexto",
            latency_seconds=time.monotonic() - start,
        )
        _log_interaction(result)
        return result

    if collection is None:
        collection = load_index()

    try:
        question_embedding = embed(question)
        retrieved = retrieve(question_embedding, collection)
        best_score = retrieved[0].score if retrieved else 0.0

        if not retrieved or best_score < SIMILARITY_THRESHOLD:
            result = AnswerResult(
                question=question,
                answer=NO_CONTEXT_MESSAGE,
                status="sem_contexto",
                retrieved=retrieved,
                latency_seconds=time.monotonic() - start,
            )
            _log_interaction(result)
            return result

        prompt = _build_prompt(question, retrieved)
        raw_answer = generate(prompt)
        sources = sorted({chunk.source for chunk in retrieved if chunk.score >= SIMILARITY_THRESHOLD})

        result = AnswerResult(
            question=question,
            answer=raw_answer,
            status="ok",
            sources=sources,
            retrieved=retrieved,
            latency_seconds=time.monotonic() - start,
        )
        _log_interaction(result)
        return result

    except OllamaUnavailableError as exc:
        result = AnswerResult(
            question=question,
            answer=(
                "O serviço de IA não está disponível no momento. "
                "Verifique se a API configurada no .env está acessível e tente novamente."
            ),
            status="erro",
            latency_seconds=time.monotonic() - start,
            error=str(exc),
        )
        _log_interaction(result)
        return result
