"""Configuration for PDF Q&A Assistant."""
import os
from dataclasses import dataclass


@dataclass
class Settings:
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    embedding_model_name: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    chroma_db_path: str = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    chroma_collection_name: str = os.getenv("CHROMA_COLLECTION", "pdf_qa")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    top_k: int = int(os.getenv("TOP_K", "3"))


settings = Settings()
