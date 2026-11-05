FROM python:3.12-slim

WORKDIR /app

# DocAssist não tem nenhuma dependência Python externa — ver requirements.txt — então não
# há passo de `pip install`. Isso também evita o problema (documentado no README) de
# pacotes com extensão nativa sem wheel pré-compilada para versões recentes do Python.
COPY . .

RUN useradd --create-home --uid 1000 appuser \
    && chmod +x docker-entrypoint.sh \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8765

ENTRYPOINT ["./docker-entrypoint.sh"]
