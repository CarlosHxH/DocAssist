#!/bin/sh
# Ponto de entrada do container do DocAssist: espera a API de IA responder, gera o índice
# vetorial (ChromaDB ou Qdrant, conforme VECTOR_STORE) se ele ainda não existir e só então
# sobe o servidor web.
set -e

echo "Aguardando a API de IA ficar disponível..."
until python -c "import sys; sys.path.insert(0, 'src'); import ollama_client; sys.exit(0 if ollama_client.is_available() else 1)"; do
  sleep 2
done
echo "API de IA disponível."

# 0 = índice pronto, 1 = falta indexar (coleção inexistente, vazia ou de outro modelo de
# embeddings), 2 = banco vetorial inacessível (o container sai e o restart tenta de novo).
set +e
python - <<'EOF'
import sys
sys.path.insert(0, "src")
import vector_store
try:
    vector_store.get_collection()
except FileNotFoundError as exc:
    print(f"Índice vetorial não encontrado: {exc}")
    sys.exit(1)
except vector_store.VectorStoreUnavailableError as exc:
    print(f"ERRO: {exc}", file=sys.stderr)
    sys.exit(2)
EOF
status=$?
set -e

if [ "$status" -eq 2 ]; then
  exit 1
elif [ "$status" -eq 1 ]; then
  echo "Rodando ingest.py (primeira execução ou reindexação)..."
  python src/ingest.py
else
  echo "Banco vetorial já indexado — pulando ingestão (rode src/ingest.py para reindexar)."
fi

exec python src/web_server.py --host 0.0.0.0 --port "${PORT:-8765}"
