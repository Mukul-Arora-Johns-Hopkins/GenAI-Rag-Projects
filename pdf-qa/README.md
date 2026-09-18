# PDF Q&A Assistant

A local-first Retrieval-Augmented Generation tool that lets you upload a PDF and ask questions about its contents. Answers come with page-level citations pointing back to the source document.

Built with **Ollama** (local LLM), **sentence-transformers** (local embeddings), and **Chroma** (local vector store). No API keys, no paid endpoints, no data leaves your machine.

## What it does

1. **Upload a PDF** — extracts text page-by-page using `pdfplumber`
2. **Chunk it** — splits into overlapping 500-token segments with page labels
3. **Embed it** — converts chunks to vectors using `all-MiniLM-L6-v2`
4. **Store it** — saves vectors in a local Chroma collection
5. **Ask questions** — retrieves the most relevant chunks (semantic + keyword hybrid search), builds a RAG prompt, and generates an answer via Ollama
6. **Get citations** — every answer includes source excerpts labeled by page number

## Quick start

```bash
# 1. Ensure Ollama is running with a model pulled
brew install ollama
ollama pull llama3.2

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -e .

# 4. Copy the example env and adjust if needed
cp .env.example .env

# 5. Run the backend
python -m pdf_qa.main
```

The API starts at `http://localhost:8000`. Open `frontend/index.html` in a browser to use the UI, or call the API directly.

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check — reports Ollama connectivity |
| `/load-pdf` | POST | Upload a PDF file path → extract, chunk, embed, store |
| `/documents` | GET | List ingested documents |
| `/query` | POST | Ask a question → get answer + citations |
| `/clear` | DELETE | Clear all indexed documents |

### Example

```bash
# Load a PDF (must be a path on the machine running the backend)
curl -X POST http://localhost:8000/load-pdf \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/Users/me/research-paper.pdf"}'

# Ask a question
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the main findings of this paper?"}'
```

## Architecture

```
User ──▶ FastAPI (localhost:8000)
            ├── Ingest: pdfplumber → chunks (page-labeled)
            ├── Embed: sentence-transformers → vectors
            ├── Store: Chroma (local, cosine similarity)
            └── Generate: Ollama (llama3.2) → answer + citations
```

## Frontend

Open `frontend/index.html` in a browser to use the interactive UI.

**Two modes** are built into the frontend, controlled by the `API_BASE` variable in `app.js`:

| Mode | What you see | When to use |
|------|-------------|-------------|
| **Demo mode** (`API_BASE = ''`) | Simulated answers with realistic page-level citations. The UI is fully interactive — upload, ask, see citations. | Recruiters viewing on GitHub Pages, or when the backend isn't running. This is the **default**. |
| **Live mode** (`API_BASE = 'http://localhost:8000'`) | Real answers from Ollama via the FastAPI backend. | When running the backend locally or after deploying it. |

To switch modes, edit the `API_BASE` variable at the top of `pdf-qa/frontend/app.js`.

## Configuration

All tunables are in `.env` (copy from `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.2` | Model used for generation |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model for embeddings |
| `CHROMA_DB_PATH` | `./chroma_db` | Where Chroma stores its data |
| `CHROMA_COLLECTION` | `pdf_qa` | Chroma collection name |
| `CHUNK_SIZE` | `500` | Characters per chunk |
| `CHUNK_OVERLAP` | `50` | Overlap between chunks |
| `TOP_K` | `3` | Number of chunks retrieved per query |

## Docker

```bash
# Build
docker build -t pdf-qa -f Dockerfile .

# Run (requires Ollama reachable — see networking notes below)
docker run -p 8000:8000 \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  pdf-qa
```

**Docker networking:** If Ollama runs on your host machine, use `host.docker.internal` on macOS/Windows, or the host's IP on Linux. If Ollama runs in another container, point `OLLAMA_BASE_URL` at that container's service name.

## Frontend modes

Each tool's frontend supports two modes — controlled by the `API_BASE` variable in `app.js`:

| Mode | `API_BASE` value | Behavior |
|------|-----------------|----------|
| **Demo mode** | `''` (empty string) | Shows simulated answers with realistic citation formatting. Use this when the backend isn't running, or for presenting on GitHub Pages. |
| **Live mode** | `'http://localhost:8000'` (or your deployed URL) | Connects to a running FastAPI backend and gets real answers from Ollama. |

The frontends ship in **demo mode by default** so recruiters viewing on GitHub Pages see a working interface without needing the backend running. To switch to live mode, edit `API_BASE` at the top of the respective `app.js`.

## Running both backends

The PDF Q&A backend uses port 8000 by default. The YouTube Research Assistant uses port 8001. If you run both on the same machine:

```bash
python -m pdf_qa.main &     # → :8000
python -m youtube_rag.main  # → :8001
```

## License

MIT
