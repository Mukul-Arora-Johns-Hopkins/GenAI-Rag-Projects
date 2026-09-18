"""LLM generation for YouTube Research Assistant via Ollama."""
import requests
from dataclasses import dataclass

from youtube_rag.config import settings


@dataclass
class GenerationResult:
    answer: str
    raw_response: str
    model: str


def build_prompt(question: str, retrieved_chunks: list) -> str:
    """Build RAG prompt for YouTube transcript questions."""
    context = "\n\n".join(
        f"[Timestamp: {c.source}]\n{c.text}" for c in retrieved_chunks
    )

    prompt = (
        "You are a helpful research assistant. Answer the question using "
        "ONLY the transcript context provided below. If the context does not "
        "contain enough information, say so — do not make up information.\n\n"
        "When you answer, cite your sources by referencing the timestamps "
        "in the [Timestamp: MM:SS] labels. Use citations like "
        "(see 02:14) or (from timestamp 15:28) in your response.\n\n"
        "Context:\n"
        f"{context}\n\n"
        "Question: "
        f"{question}\n\n"
        "Answer with timestamp citations:"
    )
    return prompt


def generate_answer(question: str, retrieved_chunks: list) -> GenerationResult:
    """Call Ollama to generate an answer from the RAG prompt."""
    prompt = build_prompt(question, retrieved_chunks)

    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "top_p": 0.9,
            "num_ctx": 4096,
        },
    }

    try:
        resp = requests.post(
            f"{settings.ollama_base_url}/api/generate",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return GenerationResult(
            answer=data.get("response", "").strip(),
            raw_response=data.get("response", ""),
            model=settings.ollama_model,
        )
    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            f"Cannot connect to Ollama at {settings.ollama_base_url}. "
            "Is Ollama running? Try: ollama serve"
        )
    except requests.exceptions.Timeout:
        raise TimeoutError("Ollama generation timed out. Try a shorter question or a smaller model.")


def format_citations(chunks: list) -> list:
    """Format retrieved chunks as timestamp citations for the frontend."""
    seen_sources = set()
    citations = []

    for chunk in chunks:
        source = chunk.source or "unknown"
        if source in seen_sources:
            continue
        seen_sources.add(source)

        excerpt = chunk.text
        if len(excerpt) > 250:
            excerpt = excerpt[:250].rsplit(" ", 1)[0] + "…"
        citations.append({"source": source, "excerpt": excerpt})

    return citations
