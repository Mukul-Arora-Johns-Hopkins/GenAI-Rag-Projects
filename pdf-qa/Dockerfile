# PDF Q&A Assistant — Dockerfile
# Builds a container that runs the FastAPI backend.
# Ollama must be running on the host (or another container) and reachable.

FROM python:3.12-slim

WORKDIR /app

# Install system deps for PDF parsing and sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY pdf-qa/pyproject.toml pdf-qa/
RUN pip install --no-cache-dir /app/pdf-qa/

# Copy application code
COPY pdf-qa/app/ ./app/
COPY shared/ ./shared/

# Create chroma db directory
RUN mkdir -p /app/chroma_db && chmod 777 /app/chroma_db

# Default env
ENV OLLAMA_BASE_URL=http://host.docker.internal:11434
ENV CHROMA_DB_PATH=/app/chroma_db
ENV CHROMA_COLLECTION=pdf_qa
ENV PORT=8000

EXPOSE 8000

CMD ["python", "-m", "pdf_qa.main"]
