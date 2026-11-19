"""Acesso ao banco vetorial, escolhido por VECTOR_STORE no .env:

- "chroma": ChromaDB persistente (armazenado em SQLite em CHROMA_PATH);
- "qdrant": servidor Qdrant em QDRANT_URL, via API REST (só urllib da biblioteca padrão).

Os embeddings são gerados por `ollama_client.embed` e passados explicitamente ao banco,
que só armazena e busca (distância cosseno). Os dois backends expõem a mesma interface
(`add`, `query`, `count`, `list_sources`), para que ingest.py, rag.py e web_server.py não
dependam de qual banco está em uso.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

import config

logger = logging.getLogger("docassist.vector_store")


class VectorStoreUnavailableError(RuntimeError):
    """Levantado quando o banco vetorial não responde (offline, timeout, erro HTTP)."""


@dataclass
class Match:
    score: float  # similaridade de cosseno (1 = idêntico)
    text: str
    metadata: dict


def describe() -> str:
    """Descrição curta do banco em uso, para logs e mensagens (sem a chave de API)."""
    if config.VECTOR_STORE == "qdrant":
        return f"Qdrant ({config.QDRANT_URL}, coleção '{config.VECTOR_COLLECTION}')"
    return f"ChromaDB ({config.CHROMA_PATH}, coleção '{config.VECTOR_COLLECTION}')"


# --- ChromaDB ---------------------------------------------------------------------------


class ChromaIndex:
    def __init__(self, collection) -> None:
        self._collection = collection

    def add(self, ids: list[str], texts: list[str], embeddings: list[list[float]], metadatas: list[dict]) -> None:
        self._collection.add(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)

    def query(self, embedding: list[float], top_k: int) -> list[Match]:
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        # Coleção criada com espaço "cosine": distância = 1 - similaridade de cosseno.
        return [
            Match(score=1.0 - distance, text=document, metadata=metadata)
            for document, metadata, distance in zip(
                result["documents"][0], result["metadatas"][0], result["distances"][0]
            )
        ]

    def count(self) -> int:
        return self._collection.count()

    def list_sources(self) -> list[str]:
        metadatas = self._collection.get(include=["metadatas"])["metadatas"] or []
        return sorted({meta["source"] for meta in metadatas})

    def embedding_model(self) -> str | None:
        return (self._collection.metadata or {}).get("embedding_model")


def _chroma_client():
    # Import tardio: quem usa só o Qdrant não paga o custo de carregar o chromadb.
    import chromadb
    from chromadb.config import Settings

    return chromadb.PersistentClient(
        path=str(config.CHROMA_PATH), settings=Settings(anonymized_telemetry=False)
    )


def _chroma_recreate() -> ChromaIndex:
    client = _chroma_client()
    try:
        client.delete_collection(config.VECTOR_COLLECTION)
    except Exception:  # coleção ainda não existe
        pass
    return ChromaIndex(
        client.create_collection(
            name=config.VECTOR_COLLECTION,
            embedding_function=None,
            metadata={"hnsw:space": "cosine", "embedding_model": config.EMBEDDING_MODEL},
        )
    )


def _chroma_open() -> ChromaIndex:
    try:
        collection = _chroma_client().get_collection(config.VECTOR_COLLECTION, embedding_function=None)
    except Exception as exc:
        raise FileNotFoundError(
            f"Coleção '{config.VECTOR_COLLECTION}' não existe em {config.CHROMA_PATH}. "
            "Rode `python src/ingest.py` primeiro para gerar o índice."
        ) from exc
    return ChromaIndex(collection)


# --- Qdrant -----------------------------------------------------------------------------


def _qdrant_request(method: str, path: str, payload: dict | None = None) -> dict:
    """Chama a API REST do Qdrant; devolve o JSON. HTTP 404 vira FileNotFoundError."""
    url = f"{config.QDRANT_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if config.QDRANT_API_KEY:
        headers["api-key"] = config.QDRANT_API_KEY
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=config.REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        if exc.code == 404:
            raise FileNotFoundError(detail) from exc
        logger.warning("Qdrant respondeu HTTP %s em %s %s: %s", exc.code, method, path, detail)
        raise VectorStoreUnavailableError(f"Qdrant em {url} respondeu HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        logger.warning("Falha ao conectar ao Qdrant em %s: %s", url, exc)
        raise VectorStoreUnavailableError(f"Não foi possível falar com o Qdrant em {url}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise VectorStoreUnavailableError(f"Resposta inválida (não-JSON) do Qdrant em {url}") from exc


class QdrantIndex:
    def __init__(self, name: str) -> None:
        self._base = f"/collections/{urllib.parse.quote(name, safe='')}"

    def add(self, ids: list[str], texts: list[str], embeddings: list[list[float]], metadatas: list[dict]) -> None:
        # O Qdrant só aceita ids inteiros ou UUID; o texto do trecho vai no payload, junto
        # com o modelo de embeddings (usado para detectar índice desatualizado).
        points = [
            {
                "id": int(point_id),
                "vector": vector,
                "payload": {**metadata, "text": text, "embedding_model": config.EMBEDDING_MODEL},
            }
            for point_id, text, vector, metadata in zip(ids, texts, embeddings, metadatas)
        ]
        _qdrant_request("PUT", f"{self._base}/points?wait=true", {"points": points})

    def query(self, embedding: list[float], top_k: int) -> list[Match]:
        result = _qdrant_request(
            "POST", f"{self._base}/points/search",
            {"vector": embedding, "limit": top_k, "with_payload": True},
        )["result"]
        # Coleção criada com distância "Cosine": o score já é a similaridade de cosseno.
        return [
            Match(
                score=point["score"],
                text=point["payload"].get("text", ""),
                metadata={k: v for k, v in point["payload"].items() if k not in ("text", "embedding_model")},
            )
            for point in result
        ]

    def count(self) -> int:
        return _qdrant_request("POST", f"{self._base}/points/count", {"exact": True})["result"]["count"]

    def _scroll(self, fields: list[str], limit: int | None = None):
        offset = None
        while True:
            payload = {"limit": min(limit or 256, 256), "with_payload": fields, "with_vector": False}
            if offset is not None:
                payload["offset"] = offset
            result = _qdrant_request("POST", f"{self._base}/points/scroll", payload)["result"]
            yield from result["points"]
            offset = result.get("next_page_offset")
            if offset is None or limit is not None:
                return

    def list_sources(self) -> list[str]:
        return sorted({point["payload"]["source"] for point in self._scroll(["source"])})

    def embedding_model(self) -> str | None:
        for point in self._scroll(["embedding_model"], limit=1):
            return point["payload"].get("embedding_model")
        return None


def _qdrant_recreate(dimension: int) -> QdrantIndex:
    index = QdrantIndex(config.VECTOR_COLLECTION)
    try:
        _qdrant_request("DELETE", index._base)
    except FileNotFoundError:  # coleção ainda não existe
        pass
    _qdrant_request("PUT", index._base, {"vectors": {"size": dimension, "distance": "Cosine"}})
    return index


def _qdrant_open() -> QdrantIndex:
    index = QdrantIndex(config.VECTOR_COLLECTION)
    try:
        _qdrant_request("GET", index._base)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Coleção '{config.VECTOR_COLLECTION}' não existe no Qdrant em {config.QDRANT_URL}. "
            "Rode `python src/ingest.py` primeiro para gerar o índice."
        ) from exc
    return index


# --- Interface comum --------------------------------------------------------------------

VectorIndex = ChromaIndex | QdrantIndex


def recreate_collection(dimension: int) -> VectorIndex:
    """Apaga e recria a coleção (usado pelo ingest.py para reindexar do zero).

    `dimension` é o tamanho dos vetores de embedding; o Qdrant exige saber na criação.
    """
    if config.VECTOR_STORE == "qdrant":
        return _qdrant_recreate(dimension)
    return _chroma_recreate()


def get_collection() -> VectorIndex:
    """Abre a coleção existente; levanta FileNotFoundError se ainda não foi indexada (ou
    se foi indexada com outro modelo de embeddings) e VectorStoreUnavailableError se o
    banco não responder."""
    index = _qdrant_open() if config.VECTOR_STORE == "qdrant" else _chroma_open()
    if index.count() == 0:
        raise FileNotFoundError(f"A coleção em {describe()} está vazia. Rode `python src/ingest.py`.")
    indexed_model = index.embedding_model()
    if indexed_model and indexed_model != config.EMBEDDING_MODEL:
        raise FileNotFoundError(
            f"O índice foi gerado com o modelo de embeddings '{indexed_model}', mas o .env "
            f"configura '{config.EMBEDDING_MODEL}'. Rode `python src/ingest.py` para reindexar."
        )
    return index


def list_sources(index: VectorIndex) -> list[str]:
    return index.list_sources()
