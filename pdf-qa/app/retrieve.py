"""Vector search (semantic) and hybrid search for PDF Q&A."""
from typing import List, Dict
import chromadb
from sentence_transformers import SentenceTransformer

from pdf_qa.config import settings
from shared.rag_core import Chunk


class VectorStore:
    """Thin wrapper around Chromadb for document storage and similarity search."""

    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.chroma_db_path)
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._embedder = None

    @property
    def embedder(self) -> SentenceTransformer:
        if self._embedder is None:
            self._embedder = SentenceTransformer(settings.embedding_model_name)
        return self._embedder

    def add_documents(self, documents: list, metadatas: list = None):
        embeddings = self.embedder.encode(documents, convert_to_numpy=True).tolist()
        ids = [f"doc_{i}" for i in range(len(documents))]
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas or [{}] * len(documents),
            ids=ids,
        )

    def query(self, query_embeddings: list, n_results: int = 3, include: list = None):
        include = include or ["documents", "metadatas", "distances"]
        return self.collection.query(
            query_embeddings=query_embeddings,
            n_results=n_results,
            include=include,
        )

    def clear(self):
        self.client.delete_collection(settings.chroma_collection_name)
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        return self.collection.count()


def get_vector_store() -> VectorStore:
    """Singleton-like access to the vector store."""
    if not hasattr(get_vector_store, "_instance"):
        get_vector_store._instance = VectorStore()
    return get_vector_store._instance


def retrieve_similar(vector_store: VectorStore, query: str, top_k: int = 3) -> List[Dict]:
    """Semantic retrieval: embed query, search Chroma, return chunks sorted by similarity."""
    query_embedding = vector_store.embedder.encode([query], convert_to_numpy=True).tolist()[0]

    results = vector_store.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    ranked = []
    for i, doc in enumerate(results["documents"][0]):
        meta = results["metadatas"][0][i]
        dist = results["distances"][0][i]
        similarity = 1 - dist  # Chroma cosine distance → similarity
        ranked.append({
            "chunk": Chunk(
                id=meta.get("chunk_id", f"i{i}"),
                text=doc,
                source=meta.get("source", "unknown"),
                metadata=meta,
            ),
            "similarity": round(similarity, 3),
        })

    ranked.sort(key=lambda x: x["similarity"], reverse=True)
    return ranked


def hybrid_search(vector_store: VectorStore, query: str, top_k: int = 3) -> List[Dict]:
    """Combine semantic similarity with keyword overlap scoring."""
    # 1. Semantic retrieval
    semantic_results = retrieve_similar(vector_store, query, top_k * 3)

    # 2. Keyword scoring via BM25-light approach
    query_terms = set(query.lower().split())
    if len(query_terms) <= 1:
        return semantic_results[:top_k]

    # Collect all documents for keyword scoring
    all_docs = vector_store.collection.get(include=["documents", "metadatas"])
    doc_texts = all_docs["documents"]
    doc_metas = all_docs["metadatas"]

    keyword_scores = {}
    for doc, meta in zip(doc_texts, doc_metas):
        text_lower = doc.lower()
        overlap = sum(1 for term in query_terms if term in text_lower)
        if overlap > 0:
            id_ = meta.get("chunk_id", f"doc_{doc}")
            keyword_scores[id_] = overlap / len(query_terms)

    # 3. Combine scores: alpha * semantic + (1 - alpha) * keyword
    alpha = 0.6
    combined = {}
    for r in semantic_results:
        cid = r["chunk"].id
        combined[cid] = {
            "chunk": r["chunk"],
            "semantic": r["similarity"],
            "keyword": keyword_scores.get(cid, 0),
        }

    ranked = []
    for cid, data in combined.items():
        final_score = alpha * data["semantic"] + (1 - alpha) * data["keyword"]
        ranked.append({"chunk": data["chunk"], "similarity": round(final_score, 3)})

    ranked.sort(key=lambda x: x["similarity"], reverse=True)
    return ranked[:top_k]
