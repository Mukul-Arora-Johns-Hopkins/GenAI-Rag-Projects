# GenAI & RAG Tools — Monorepo

A portfolio-ready monorepo of two Retrieval-Augmented Generation systems built with open-source, local-first tools. Both run on Ollama (local LLM) with sentence-transformers (local embeddings) and Chroma (local vector store). No API keys, no third-party data processing, no paid endpoints.

## Projects

| Project | What it does | Source |
|---------|-------------|--------|
| `pdf-qa/` | Upload a PDF → chunk → retrieve relevant passages → answer with citations | Your PDFs |
| `youtube-rag/` | Paste a YouTube URL → extract transcript → embed → answer questions with timestamps | YouTube video transcripts |

## Stack (all free, all local)

- **LLM**: Ollama (llama3.1 or qwen2.5) — runs locally, no data leaves your machine
- **Embeddings**: sentence-transformers (`all-MiniLM-L6-v2` or `nomic-embed-text`) — local, no API
- **Vector DB**: Chroma — local, SQLite-backed, no server
- **PDF parsing**: pdfplumber — BSD-licensed, reliable
- **YouTube transcripts**: youtube-transcript-api — free, no API key
- **Backend**: Python + FastAPI
- **Frontend**: Plain HTML/CSS/JS (zero build step, GitHub Pages compatible)
- **Deployment**: Dockerized backend; frontend on GitHub Pages

## Quick start

```bash
# 1. Install Ollama and pull a model
brew install ollama
ollama pull llama3.1

# 2. Clone and install Python deps
cd genai-rag-tools
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Run both backends (or one at a time)
python -m pdf_qa.main      # → http://localhost:8000
python -m youtube_rag.main  # → http://localhost:8001
```

Then open the frontend in `portfolio/` or the individual tool frontends in `pdf-qa/frontend/` and `youtube-rag/frontend/`.

## Architecture

```
┌──────────┐     ┌─────────────┐     ┌──────────────┐
│  User    │────▶│  FastAPI    │────▶│  Chroma      │
│  (web)   │     │  (backend)  │     │  (vectors)   │
└──────────┘     └──────┬──────┘     └──────────────┘
                        │                       ▲
                        ▼                       │
                   ┌──────────┐                │
                   │  Ollama  │────────────────┘
                   │ (LLM)    │   retrieved chunks
                   └──────────┘
```

See `portfolio/` for the full diagram and project overview.

## Project structure

```
genai-rag-tools/
├── pdf-qa/
│   ├── app/
│   │   ├── main.py
│   │   ├── ingest.py
│   │   ├── retrieve.py
│   │   ├── generate.py
│   │   ├── config.py
│   │   └── models.py
│   ├── frontend/
│   │   ├── index.html
│   │   ├── style.css
│   │   └── app.js
│   ├── tests/
│   ├── Dockerfile
│   └── README.md
├── youtube-rag/
│   ├── app/
│   │   ├── main.py
│   │   ├── ingest.py
│   │   ├── retrieve.py
│   │   ├── generate.py
│   │   ├── config.py
│   │   └── models.py
│   ├── frontend/
│   │   ├── index.html
│   │   ├── style.css
│   │   └── app.js
│   ├── tests/
│   ├── Dockerfile
│   └── README.md
├── portfolio/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── shared/
│   └── rag_core.py          # Shared chunking, retrieval, prompt utilities
├── .gitignore
└── README.md
```

## License

MIT
