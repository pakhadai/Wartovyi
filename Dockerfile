# WartovyiBot: Telegram-бот + FastAPI (Web App) в одному процесі
FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BOT_DB_PATH=/data/bot_database_v6.db

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ bot/
COPY webapp/ webapp/

RUN mkdir -p /data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=50s --retries=3 \
    CMD curl -sf http://127.0.0.1:8000/openapi.json >/dev/null || exit 1

CMD ["python", "-m", "bot.main"]
