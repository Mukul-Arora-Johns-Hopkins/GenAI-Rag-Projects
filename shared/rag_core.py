"""Shared RAG utilities — chunking, retrieval, prompt building.

Used by both pdf-qa and youtube-rag. Keeps both projects DRY without a heavy framework.
"""
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class Chunk:
    """A single text chunk with metadata for retrieval and citation."""
    id: str
    text: str
    source: str          # e.g. "page 3" or "04:12"
    metadata: Dict[str, Any] = None


def chunk_text(
    text: str,
    source_label: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> List[Chunk]:
    """Split text into overlapping chunks for better retrieval granularity.

    Uses simple sentence-aware splitting: break on sentence boundaries
    near the chunk_size target, with overlap to preserve context across
    boundaries.
    """
    import re

    # Split into sentences (handles . ! ? and newlines)
    sentences = re.split(r'(?<=[.!?])\s+|\n\n+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks = []
    current_chunk = []
    current_len = 0
    chunk_id = 0

    for sentence in sentences:
        sentence_len = len(sentence)

        # If a single sentence is longer than chunk_size, split it on words
        if sentence_len > chunk_size and not current_chunk:
            words = sentence.split()
            sub_chunks = []
            sub = []
            sub_len = 0
            for word in words:
                if sub_len + len(word) + 1 > chunk_size and sub:
                    sub_chunks.append(' '.join(sub))
                    sub = []
                    sub_len = 0
                sub.append(word)
                sub_len += len(word) + 1
            if sub:
                sub_chunks.append(' '.join(sub))
            for sc in sub_chunks:
                chunks.append(Chunk(
                    id=f"{source_label}-chunk-{chunk_id}",
                    text=sc,
                    source=source_label,
                ))
                chunk_id += 1
            continue

        # Would adding this sentence exceed chunk_size?
        if current_len + sentence_len + (1 if current_chunk else 0) > chunk_size and current_chunk:
            # Finalize current chunk
            chunk_text = ' '.join(current_chunk)
            chunks.append(Chunk(
                id=f"{source_label}-chunk-{chunk_id}",
                text=chunk_text,
                source=source_label,
            ))
            chunk_id += 1

            # Start new chunk with overlap (last few sentences)
            overlap_size = chunk_overlap
            overlap_sentences = []
            overlap_len = 0
            for s in reversed(current_chunk):
                if overlap_len + len(s) + 1 <= overlap_size:
                    overlap_sentences.insert(0, s)
                    overlap_len += len(s) + 1
                else:
                    break
            current_chunk = overlap_sentences
            current_len = overlap_len

        current_chunk.append(sentence)
        current_len += sentence_len + (1 if len(current_chunk) > 1 else 0)

    # Final chunk
    if current_chunk:
        chunk_text = ' '.join(current_chunk)
        chunks.append(Chunk(
            id=f"{source_label}-chunk-{chunk_id}",
            text=chunk_text,
            source=source_label,
        ))

    return chunks


def build_rag_prompt(
    question: str,
    retrieved_chunks: List[Chunk],
    system_instruction: str = None,
) -> str:
    """Build the prompt sent to the LLM for a RAG query.

    Includes the retrieved context and explicit instructions to cite sources.
    """
    context = "\n\n".join(
        f"[Source: {c.source}]\n{c.text}" for c in retrieved_chunks
    )

    system = system_instruction or (
        "You are a helpful research assistant. Answer the user's question "
        "using ONLY the provided context. If the context does not contain "
        "enough information to answer, say so clearly. Cite your sources "
        "by referring to the [Source: ...] labels in your answer."
    )

    user = (
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        f"Answer with citations to the [Source: ...] labels above."
    )

    return f"{system}\n\n{user}"


def format_citations(retrieved_chunks: List[Chunk]) -> List[Dict[str, str]]:
    """Format retrieved chunks into citation objects for the frontend.

    Returns a list of {source, excerpt} dicts for display alongside the answer.
    """
    seen = set()
    citations = []
    for c in retrieved_chunks:
        key = c.source
        if key in seen:
            continue
        seen.add(key)
        # Truncate long excerpts for display
        excerpt = c.text[:200] + ('...' if len(c.text) > 200 else '')
        citations.append({'source': c.source, 'excerpt': excerpt})
    return citations


def compute_similarity(
    query_embedding: List[float],
    chunk_embeddings: List[List[float]],
) -> List[float]:
    """Cosine similarity between query and each chunk embedding.

    Pure Python implementation — works without numpy for small sets.
    """
    import math

    def dot(a, b):
        return sum(x * y for x, y in zip(a, b))

    def norm(a):
        return math.sqrt(sum(x * x for x in a))

    query_norm = norm(query_embedding)
    if query_norm == 0:
        return [0.0] * len(chunk_embeddings)

    results = []
    for ce in chunk_embeddings:
        ce_norm = norm(ce)
        if ce_norm == 0:
            results.append(0.0)
        else:
            results.append(dot(query_embedding, ce) / (query_norm * ce_norm))
    return results
