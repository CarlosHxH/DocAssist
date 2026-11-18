"""Acesso ao banco vetorial: ChromaDB persistente (armazenado em SQLite em CHROMA_PATH).

Os embeddings são gerados por `ollama_client.embed` e passados explicitamente ao Chroma,
que só armazena e busca (espaço de distância cosseno).
"""

from __future__ import annotations

import chromadb
from chromadb.config import Settings

import config


def _client() -> chromadb.ClientAPI:
    return chromadb.PersistentClient(
        path=str(config.CHROMA_PATH), settings=Settings(anonymized_telemetry=False)
    )


def recreate_collection() -> chromadb.Collection:
    """Apaga e recria a coleção (usado pelo ingest.py para reindexar do zero)."""
    client = _client()
    try:
        client.delete_collection(config.CHROMA_COLLECTION)
    except Exception:  # coleção ainda não existe
        pass
    return client.create_collection(
        name=config.CHROMA_COLLECTION,
        embedding_function=None,
        metadata={"hnsw:space": "cosine", "embedding_model": config.EMBEDDING_MODEL},
    )


def get_collection() -> chromadb.Collection:
    """Abre a coleção existente; levanta FileNotFoundError se ainda não foi indexada."""
    client = _client()
    try:
        collection = client.get_collection(config.CHROMA_COLLECTION, embedding_function=None)
    except Exception as exc:
        raise FileNotFoundError(
            f"Coleção '{config.CHROMA_COLLECTION}' não existe em {config.CHROMA_PATH}. "
            "Rode `python ingest.py` primeiro para gerar o índice."
        ) from exc
    if collection.count() == 0:
        raise FileNotFoundError(
            f"Coleção '{config.CHROMA_COLLECTION}' está vazia. Rode `python ingest.py`."
        )
    indexed_model = (collection.metadata or {}).get("embedding_model")
    if indexed_model and indexed_model != config.EMBEDDING_MODEL:
        raise FileNotFoundError(
            f"O índice foi gerado com o modelo de embeddings '{indexed_model}', mas o .env "
            f"configura '{config.EMBEDDING_MODEL}'. Rode `python ingest.py` para reindexar."
        )
    return collection


def list_sources(collection: chromadb.Collection) -> list[str]:
    metadatas = collection.get(include=["metadatas"])["metadatas"] or []
    return sorted({meta["source"] for meta in metadatas})
