# syntax=docker/dockerfile:1.7

FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "uv>=0.8.17,<0.9"

COPY README.md pyproject.toml uv.lock alembic.ini version.txt ./
COPY migrations ./migrations
COPY src ./src
COPY scripts ./scripts
COPY data/parquet ./data/parquet

RUN uv sync --frozen --no-dev

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app/src \
    HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/alembic.ini ./alembic.ini
COPY --from=builder /app/version.txt ./version.txt
COPY --from=builder /app/migrations ./migrations
COPY --from=builder /app/src ./src
COPY --from=builder /app/scripts ./scripts
COPY --from=builder /app/data/parquet ./data/parquet

EXPOSE 8000

CMD ["uvicorn", "ikea_agent.chat_app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
