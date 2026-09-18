# YouTube Research Assistant — Dockerfile
# Builds a container that runs the FastAPI backend.
# Ollama must be running on the host (or another container) and reachable.

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY youtube-rag/pyproject.toml youtube-rag/
RUN pip install --no-cache-dir /app/youtube-rag/

COPY youtube-rag/app/ ./app/
COPY shared/ ./shared/

RUN mkdir -p /app/chroma_db && chmod 777 /app/chroma_db

ENV OLLAMA_BASE_URL=http://host.docker.internal:11434
ENV CHROMA_DB_PATH=/app/chroma_db
ENV CHROMA_COLLECTION=youtube_rag
ENV PORT=8001

EXPOSE 8001

CMD ["python", "-m", "youtube_rag.main"]
