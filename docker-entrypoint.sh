#!/bin/sh
# Ponto de entrada do container do DocAssist: espera o Ollama responder, gera o índice
# vetorial (ChromaDB) na primeira execução (se ainda não existir) e só então sobe o servidor web.
set -e

echo "Aguardando a API de IA ficar disponível..."
until python -c "import sys; import ollama_client; sys.exit(0 if ollama_client.is_available() else 1)"; do
  sleep 2
done
echo "API de IA disponível."

CHROMA_PATH="${CHROMA_PATH:-chroma_db}"
if [ ! -f "${CHROMA_PATH}/chroma.sqlite3" ]; then
  echo "Banco vetorial não encontrado em ${CHROMA_PATH} — rodando ingest.py (primeira execução)..."
  python ingest.py
else
  echo "Banco vetorial já existe em ${CHROMA_PATH} — pulando ingestão (apague a pasta para reindexar)."
fi

exec python web_server.py --host 0.0.0.0 --port "${PORT:-8765}"
