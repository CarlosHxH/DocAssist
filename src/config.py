"""Configuração central do DocAssist, lida de variáveis de ambiente e do arquivo `.env`.

Variáveis já definidas no ambiente (ex.: `environment:` do docker-compose) têm prioridade
sobre o `.env`. Veja `.env.example` para a lista completa e os valores padrão.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Raiz do projeto (um nível acima de src/): .env, rag/ e chroma_db/ ficam lá.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env", override=False)


def _resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else BASE_DIR / path


# --- API de IA --------------------------------------------------------------------------
# "ollama": API nativa do Ollama (/api/embeddings, /api/generate).
# "openai": qualquer API compatível com OpenAI (/v1/embeddings, /v1/chat/completions) —
#           OpenAI, Azure/LiteLLM/vLLM, LM Studio, o próprio Ollama em /v1 etc.
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama").strip().lower()
# URL base da API. Mantém compatibilidade com a variável OLLAMA_HOST usada antes.
LLM_API_URL = os.environ.get("LLM_API_URL") or os.environ.get("OLLAMA_HOST") or "http://localhost:11434"
LLM_API_URL = LLM_API_URL.rstrip("/")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("REQUEST_TIMEOUT_SECONDS", "120"))

# --- Modelos ----------------------------------------------------------------------------
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "all-minilm")
GENERATION_MODEL = os.environ.get("GENERATION_MODEL", "qwen2.5:3b")
GENERATION_TEMPERATURE = float(os.environ.get("GENERATION_TEMPERATURE", "0.1"))

# --- Banco vetorial ---------------------------------------------------------------------
# "chroma": ChromaDB persistente, armazenado em SQLite em CHROMA_PATH.
# "qdrant": servidor Qdrant em QDRANT_URL (API REST).
VECTOR_STORE = os.environ.get("VECTOR_STORE", "chroma").strip().lower()
CHROMA_PATH = _resolve_path(os.environ.get("CHROMA_PATH", "chroma_db"))
VECTOR_COLLECTION = os.environ.get("VECTOR_COLLECTION", "docassist")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333").rstrip("/")
# Enviada no header "api-key". Deixe vazio se o Qdrant não exigir autenticação.
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", "")
VECTOR_COLLECTION = os.environ.get("VECTOR_COLLECTION", "docassist")

# --- Ingestão e recuperação -------------------------------------------------------------
RAG_DIR = _resolve_path(os.environ.get("RAG_DIR", "rag"))
# O modelo de embeddings padrão (all-minilm) tem janela de contexto pequena; ajuste se
# trocar para um modelo com janela maior.
MAX_CHUNK_CHARS = int(os.environ.get("MAX_CHUNK_CHARS", "500"))
TOP_K = int(os.environ.get("TOP_K", "4"))
SIMILARITY_THRESHOLD = float(os.environ.get("SIMILARITY_THRESHOLD", "0.40"))

# --- Logs -------------------------------------------------------------------------------
LOG_DIR = _resolve_path(os.environ.get("LOG_DIR", "logs"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
# Formato do console: "text" (legível) ou "json" (para coletores de log de container).
# O arquivo logs/docassist.log é sempre JSON.
LOG_FORMAT = os.environ.get("LOG_FORMAT", "text").strip().lower()
LOG_MAX_BYTES = int(os.environ.get("LOG_MAX_BYTES", str(5 * 1024 * 1024)))
LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", "5"))
