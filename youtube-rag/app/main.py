"""YouTube Research Assistant — FastAPI backend.

Ingests YouTube video transcripts, chunks them, embeds with
sentence-transformers, stores in Chroma, and answers questions with
timestamp citations via Ollama.
"""
import os
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware

from shared.rag_core import chunk_text, build_rag_prompt, format_citations, compute_similarity
from youtube_rag.config import settings
from youtube_rag.ingest import ingest_video, get_vector_store, list_videos
from youtube_rag.retrieve import retrieve_similar, hybrid_search
from youtube_rag.generate import generate_answer

app = FastAPI(
    title="YouTube Research Assistant",
    description="Paste a YouTube URL, ask questions about the transcript.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response models ──

class VideoProcessRequest(BaseModel):
    url: str = Field(..., description="YouTube video URL")


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(3, ge=1, le=10)
    use_hybrid: bool = Field(True, description="Use keyword + semantic search")


class QueryResponse(BaseModel):
    answer: str
    citations: List[dict]
    sources_used: int
    processing_time_ms: int


class VideoListResponse(BaseModel):
    videos: List[dict]


# ── Endpoints ──

@app.get("/health")
async def health():
    return {"status": "ok", "ollama": settings.ollama_available}


@app.post("/process-video", response_model=dict)
async def process_video(req: VideoProcessRequest):
    """Ingest a YouTube video: fetch transcript, chunk, embed, store."""
    try:
        chunks = ingest_video(req.url)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to process video: {str(e)}")

    vs = get_vector_store()
    vs.add_documents(
        documents=[c.text for c in chunks],
        metadatas=[{"source": c.source, "chunk_id": c.id, "video_id": chunks[0].metadata.get("video_id", "")} for c in chunks],
    )

    return {
        "status": "ok",
        "video_id": chunks[0].metadata.get("video_id", ""),
        "chunks": len(chunks),
        "message": f"Processed video — {len(chunks)} chunks indexed",
    }


@app.get("/videos", response_model=VideoListResponse)
async def get_videos():
    """List all ingested videos."""
    videos = list_videos()
    return {"videos": videos}


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    """Ask a question about ingested videos. Returns answer + timestamp citations."""
    import time
    start = time.time()

    vs = get_vector_store()
    if vs is None or vs._collection.count() == 0:
        raise HTTPException(400, "No videos processed. Add a YouTube video first.")

    if req.use_hybrid:
        results = hybrid_search(vs, req.question, top_k=req.top_k)
    else:
        results = retrieve_similar(vs, req.question, top_k=req.top_k)

    if not results:
        raise HTTPException(400, "No relevant transcript content found for your question.")

    chunks = [r["chunk"] for r in results]
    prompt = build_rag_prompt(req.question, chunks)
    answer = generate_answer(prompt)

    elapsed_ms = int((time.time() - start) * 1000)

    return QueryResponse(
        answer=answer,
        citations=format_citations(chunks),
        sources_used=len(chunks),
        processing_time_ms=elapsed_ms,
    )


@app.delete("/clear")
async def clear_all():
    """Clear all ingested video transcripts from the vector store."""
    vs = get_vector_store()
    if vs:
        vs.clear()
    return {"status": "ok", "message": "Vector store cleared."}


# ── Run ──

def run():
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("youtube_rag.main:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    run()
