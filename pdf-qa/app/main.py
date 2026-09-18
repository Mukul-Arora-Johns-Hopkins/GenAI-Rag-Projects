"""PDF Q&A Assistant — FastAPI backend.

Ingests PDFs, chunks them, embeds with sentence-transformers, stores in
Chroma, and answers questions with citations via Ollama.
"""
import os
import uuid
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware

from shared.rag_core import chunk_text, build_rag_prompt, format_citations, compute_similarity
from pdf_qa.config import settings
from pdf_qa.ingest import ingest_pdf, get_vector_store, list_documents
from pdf_qa.retrieve import retrieve_similar, hybrid_search
from pdf_qa.generate import generate_answer

app = FastAPI(
    title="PDF Q&A Assistant",
    description="Upload a PDF, ask questions, get answers with citations.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response models ──

class PDFLoadRequest(BaseModel):
    file_path: str = Field(..., description="Path to the PDF file on disk")


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(3, ge=1, le=10)
    use_hybrid: bool = Field(True, description="Use keyword + semantic search")


class QueryResponse(BaseModel):
    answer: str
    citations: List[dict]
    sources_used: int
    processing_time_ms: int


class DocumentListResponse(BaseModel):
    documents: List[dict]


# ── Endpoints ──

@app.get("/health")
async def health():
    return {"status": "ok", "ollama": settings.ollama_available}


@app.post("/load-pdf", response_model=dict)
async def load_pdf(req: PDFLoadRequest):
    """Ingest a PDF: extract text, chunk, embed, store in Chroma."""
    path = Path(req.file_path)
    if not path.exists():
        raise HTTPException(400, f"File not found: {req.file_path}")

    try:
        chunks = ingest_pdf(path)
    except Exception as e:
        raise HTTPException(500, f"Failed to ingest PDF: {str(e)}")

    vs = get_vector_store()
    vs.add_documents(
        documents=[c.text for c in chunks],
        metadatas=[{"source": c.source, "chunk_id": c.id} for c in chunks],
    )

    return {
        "status": "ok",
        "document": path.name,
        "chunks": len(chunks),
        "message": f"Loaded {len(chunks)} chunks from {path.name}",
    }


@app.get("/documents", response_model=DocumentListResponse)
async def get_documents():
    """List all ingested documents."""
    docs = list_documents()
    return {"documents": docs}


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    """Ask a question about ingested PDFs. Returns answer + citations."""
    import time
    start = time.time()

    vs = get_vector_store()
    if vs is None or vs._collection.count() == 0:
        raise HTTPException(400, "No documents loaded. Upload a PDF first.")

    # Retrieve relevant chunks
    if req.use_hybrid:
        results = hybrid_search(vs, req.question, top_k=req.top_k)
    else:
        results = retrieve_similar(vs, req.question, top_k=req.top_k)

    if not results:
        raise HTTPException(400, "No relevant content found for your question.")

    # Build prompt and generate
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
    """Clear all ingested documents from the vector store."""
    vs = get_vector_store()
    if vs:
        vs.clear()
    return {"status": "ok", "message": "Vector store cleared."}


# ── Run ──

def run():
    import uvicorn
    uvicorn.run("pdf_qa.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
