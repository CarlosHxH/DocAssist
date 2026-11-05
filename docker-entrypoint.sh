#!/bin/sh
# Ponto de entrada do container do DocAssist: espera o Ollama responder, gera o índice
# vetorial na primeira execução (se ainda não existir) e só então sobe o servidor web.
set -e

OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"

echo "Aguardando o Ollama ficar disponível em ${OLLAMA_HOST}..."
until python -c "import sys; import ollama_client; sys.exit(0 if ollama_client.is_available() else 1)"; do
  sleep 2
done
echo "Ollama disponível."

if [ ! -f index.json ]; then
  echo "index.json não encontrado — rodando ingest.py (primeira execução)..."
  python ingest.py
else
  echo "index.json já existe — pulando ingestão (apague o arquivo para reindexar)."
fi

exec python web_server.py --host 0.0.0.0 --port "${PORT:-8765}"
