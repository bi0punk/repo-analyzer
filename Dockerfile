# syntax=docker/dockerfile:1
FROM python:3.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY repo_agent ./repo_agent
COPY src ./src

RUN pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin analyzer

USER analyzer

# Monta el repositorio a analizar en /work
WORKDIR /work

ENTRYPOINT ["repo-analyzer"]
CMD ["--help"]
