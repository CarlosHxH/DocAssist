"""Núcleo do pipeline RAG: recuperação (busca vetorial no ChromaDB ou Qdrant) + geração grounded.

Mantido separado da interface (CLI/Streamlit) para que app.py e eval.py reusem a mesma
lógica, e para que os testes de cenário (ver tests/) possam chamar `answer()` diretamente.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime

import config
import log_setup
import vector_store
from ollama_client import OllamaUnavailableError, embed, generate

logger = logging.getLogger("docassist.rag")

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
- Formate a resposta em Markdown: listas para passos e itens, **negrito** para termos \
importantes e `crase` para nomes de branch, arquivos, comandos e variáveis.
- Quando o CONTEXTO trouxer exemplos (comandos, nomes, trechos de código ou de \
configuração), inclua-os na resposta exatamente como aparecem no CONTEXTO; exemplos com \
mais de uma linha vão em bloco de código (```linguagem).
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
    # Tempo (s) de cada etapa executada: "embedding", "retrieval", "generation".
    timings: dict[str, float] = field(default_factory=dict)
    error: str | None = None


def load_index() -> vector_store.VectorIndex:
    return vector_store.get_collection()


def retrieve(
    question_embedding: list[float], collection: vector_store.VectorIndex, top_k: int = TOP_K
) -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            score=match.score,
            source=match.metadata["source"],
            heading=match.metadata["heading"],
            text=match.text,
        )
        for match in collection.query(question_embedding, top_k)
    ]


def _build_prompt(question: str, retrieved: list[RetrievedChunk]) -> str:
    context = "\n\n".join(
        f"[Documento: {chunk.source} | Seção: {chunk.heading}]\n{chunk.text}" for chunk in retrieved
    )
    return f"{SYSTEM_INSTRUCTIONS}\n\nCONTEXTO:\n{context}\n\nPERGUNTA: {question}\n\nRESPOSTA:"


def _log_interaction(result: AnswerResult, channel: str | None) -> None:
    best_score = result.retrieved[0].score if result.retrieved else None
    entry = {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "request_id": log_setup.request_id_var.get(),
        "channel": channel,
        "question": result.question,
        "status": result.status,
        "answer": result.answer,
        "sources": result.sources,
        "retrieved": [{"source": c.source, "heading": c.heading, "score": round(c.score, 4)} for c in result.retrieved],
        "retrieved_scores": [round(c.score, 4) for c in result.retrieved],
        "best_score": round(best_score, 4) if best_score is not None else None,
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "provider": config.LLM_PROVIDER,
        "embedding_model": config.EMBEDDING_MODEL,
        "generation_model": config.GENERATION_MODEL,
        "timings": {name: round(seconds, 3) for name, seconds in result.timings.items()},
        "latency_seconds": round(result.latency_seconds, 3),
        "error": result.error,
    }
    try:
        log_setup.interaction_logger().info(json.dumps(entry, ensure_ascii=False))
    except OSError:
        # Falha ao gravar o log (disco cheio, permissão) não pode impedir a resposta.
        logger.exception("Não foi possível gravar a interação em interactions.jsonl")

    log = logger.warning if result.status == "erro" else logger.info
    log(
        "Pergunta respondida: status=%s latência=%.2fs melhor_score=%s",
        result.status, result.latency_seconds, entry["best_score"],
        extra={"channel": channel, "status": result.status, "error": result.error},
    )


def answer(
    question: str, collection: vector_store.VectorIndex | None = None, channel: str | None = None
) -> AnswerResult:
    """Responde `question`. `channel` ("cli", "web", "eval") só identifica a origem no log."""
    start = time.monotonic()
    timings: dict[str, float] = {}
    question = (question or "").strip()

    def finish(result: AnswerResult) -> AnswerResult:
        result.latency_seconds = time.monotonic() - start
        result.timings = timings
        _log_interaction(result, channel)
        return result

    if not question:
        return finish(
            AnswerResult(
                question=question,
                answer="Pergunta vazia. Digite uma pergunta sobre os padrões internos de TI.",
                status="sem_contexto",
            )
        )

    if collection is None:
        collection = load_index()

    try:
        step = time.monotonic()
        question_embedding = embed(question)
        timings["embedding"] = time.monotonic() - step

        step = time.monotonic()
        retrieved = retrieve(question_embedding, collection)
        timings["retrieval"] = time.monotonic() - step
        best_score = retrieved[0].score if retrieved else 0.0

        if not retrieved or best_score < SIMILARITY_THRESHOLD:
            return finish(
                AnswerResult(
                    question=question,
                    answer=NO_CONTEXT_MESSAGE,
                    status="sem_contexto",
                    retrieved=retrieved,
                )
            )

        prompt = _build_prompt(question, retrieved)
        step = time.monotonic()
        raw_answer = generate(prompt)
        timings["generation"] = time.monotonic() - step
        sources = sorted({chunk.source for chunk in retrieved if chunk.score >= SIMILARITY_THRESHOLD})

        return finish(
            AnswerResult(
                question=question,
                answer=raw_answer,
                status="ok",
                sources=sources,
                retrieved=retrieved,
            )
        )

    except OllamaUnavailableError as exc:
        return finish(
            AnswerResult(
                question=question,
                answer=(
                    "O serviço de IA não está disponível no momento. "
                    "Verifique se a API configurada no .env está acessível e tente novamente."
                ),
                status="erro",
                error=str(exc),
            )
        )

    except vector_store.VectorStoreUnavailableError as exc:
        return finish(
            AnswerResult(
                question=question,
                answer=(
                    "O banco vetorial não está disponível no momento. "
                    "Verifique se o banco configurado no .env está acessível e tente novamente."
                ),
                status="erro",
                error=str(exc),
            )
        )

    except Exception as exc:
        # Falha inesperada (ex.: ChromaDB): registra a interação e o traceback, e deixa a
        # exceção subir para a interface decidir como responder.
        logger.exception("Erro inesperado no pipeline RAG")
        finish(
            AnswerResult(
                question=question,
                answer="",
                status="erro",
                error=f"{type(exc).__name__}: {exc}",
            )
        )
        raise
