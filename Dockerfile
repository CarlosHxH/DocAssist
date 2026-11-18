FROM python:3.12-slim

WORKDIR /app

# Dependências Python (chromadb, python-dotenv) instaladas antes de copiar o código para
# aproveitar o cache de camadas do Docker.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# chroma_db/ é criada aqui para que o volume nomeado herde o dono appuser.
RUN useradd --create-home --uid 1000 appuser \
    && chmod +x docker-entrypoint.sh \
    && mkdir -p chroma_db logs \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8765

ENTRYPOINT ["./docker-entrypoint.sh"]
