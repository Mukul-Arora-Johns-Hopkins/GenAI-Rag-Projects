"""PDF ingestion — extract text from PDF and chunk it."""
import pdfplumber
from pathlib import Path
from typing import List

from pdf_qa.config import settings
from shared.rag_core import chunk_text, Chunk


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from each page of a PDF using pdfplumber."""
    full_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if text:
                full_text.append(f"PAGE {page_num}\n{text}")

    return "\n\n".join(full_text)


def ingest_pdf(pdf_path: Path) -> List[Chunk]:
    """Extract text from PDF, split by page, chunk each page."""
    raw_text = extract_text_from_pdf(pdf_path)

    pages = raw_text.split("\n\nPAGE ")
    chunks = []

    for block in pages:
        if not block.strip():
            continue
        if not block.startswith("PAGE"):
            block = "PAGE " + block

        page_num = block.split("\n")[0].replace("PAGE ", "")
        clean_text = block.replace(f"PAGE {page_num}\n", "", 1)

        page_chunks = chunk_text(
            clean_text,
            source_label=f"page {page_num}",
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        chunks.extend(page_chunks)

    return chunks
