# YouTube Research Assistant

A local-first Retrieval-Augmented Generation tool that lets you paste a YouTube URL and ask questions about the video's transcript. Answers come with timestamp citations pointing back to specific moments in the video.

Built with **Ollama** (local LLM), **sentence-transformers** (local embeddings), **Chroma** (local vector store), and **youtube-transcript-api** (free transcript fetching). No API keys, no paid endpoints, no data leaves your machine.

## What it does

1. **Paste a YouTube URL** — extracts the video ID and fetches the transcript using `youtube-transcript-api`
2. **Chunk it** — splits the transcript into overlapping 500-token segments with timestamp labels
3. **Embed it** — converts chunks to vectors using `all-MiniLM-L6-v2`
4. **Store it** — saves vectors in a local Chroma collection
5. **Ask questions** — retrieves the most relevant transcript chunks (semantic + keyword hybrid search), builds a RAG prompt, and generates an answer via Ollama
6. **Get citations** — every answer includes source excerpts labeled with timestamps (MM:SS)

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
python -m youtube_rag.main
```

The API starts at `http://localhost:8001`. Open `frontend/index.html` in a browser to use the UI, or call the API directly.

Demo mode shows a simulated transcript and answers — click "Try the UI · demo mode" on the portfolio page to see it without running the backend. Live mode connects to a running FastAPI backend (default: `localhost:8001`).

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check — reports Ollama connectivity |
| `/process-video` | POST | Process a YouTube URL → fetch transcript, chunk, embed, store |
| `/videos` | GET | List processed videos |
| `/query` | POST | Ask a question → get answer + timestamp citations |
| `/clear` | DELETE | Clear all indexed transcripts |

### Example

```bash
# Process a YouTube video
curl -X POST http://localhost:8001/process-video \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'

# Ask a question
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What does the speaker say about climate change?"}'
```

## Architecture

```
User ──▶ FastAPI (localhost:8001)
            ├── Fetch: youtube-transcript-api → transcript text
            ├── Chunk: overlapping segments (timestamp-labeled)
            ├── Embed: sentence-transformers → vectors
            ├── Store: Chroma (local, cosine similarity)
            └── Generate: Ollama (llama3.2) → answer + citations
```

## Frontend

Open `frontend/index.html` in a browser. It connects to the backend at `localhost:8001` by default. There is also a **demo mode** that simulates transcripts and answers for presentation purposes — set `API_BASE = ''` in `app.js` to enable it.

The demo mode includes a **timeline visualization** showing transcript markers across the video duration, which you can click to jump to different points.

To connect a live backend, set `API_BASE = 'http://localhost:8001'` (or your deployed backend URL) in `app.js`.

## Configuration

All tunables are in `.env` (copy from `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.2` | Model used for generation |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model for embeddings |
| `CHROMA_DB_PATH` | `./chroma_db` | Where Chroma stores its data |
| `CHROMA_COLLECTION` | `youtube_rag` | Chroma collection name |
| `CHUNK_SIZE` | `500` | Characters per chunk |
| `CHUNK_OVERLAP` | `50` | Overlap between chunks |
| `TOP_K` | `3` | Number of chunks retrieved per query |
| `MAX_TRANSCRIPT_LENGTH` | `50000` | Max transcript length to process |

## YouTube transcript limitations

The `youtube-transcript-api` library works with most videos that have captions available (auto-generated or manual). Some videos — especially short clips, region-restricted content, or videos without any captions — will not have accessible transcripts. The backend returns a clear error in those cases.

## Docker

```bash
# Build
docker build -t youtube-rag -f Dockerfile .

# Run (requires Ollama reachable)
docker run -p 8001:8001 \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  youtube-rag
```

**Docker networking:** If Ollama runs on your host machine, use `host.docker.internal` on macOS/Windows, or the host's IP on Linux. If Ollama runs in another container, point `OLLAMA_BASE_URL` at that container's service name.

## Frontend modes

Each tool's frontend supports two modes — controlled by the `API_BASE` variable in `app.js`:

| Mode | `API_BASE` value | Behavior |
|------|-----------------|----------|
| **Demo mode** | `''` (empty string) | Shows simulated answers with realistic timestamp citation formatting. Use this when the backend isn't running, or for presenting on GitHub Pages. |
| **Live mode** | `'http://localhost:8001'` (or your deployed URL) | Connects to a running FastAPI backend and gets real answers from Ollama. |

The frontends ship in **demo mode by default** so recruiters viewing on GitHub Pages see a working interface without needing the backend running. To switch to live mode, edit `API_BASE` at the top of the respective `app.js`.

## Running both backends

The PDF Q&A backend uses port 8000 by default. The YouTube Research Assistant uses port 8001. If you run both on the same machine:

```bash
python -m pdf_qa.main &     # → :8000
python -m youtube_rag.main  # → :8001
```

## License

MIT
