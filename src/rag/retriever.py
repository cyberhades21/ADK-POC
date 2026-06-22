"""RAG retriever — returns relevant chunks from ChromaDB for a query."""
from pathlib import Path

CHROMA_DIR = Path(__file__).parent.parent.parent / "chroma_db"
COLLECTION = "ecombot_kb"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DISTANCE_THRESHOLD = 1.5

_client     = None
_collection = None
_model      = None


def _init():
    global _client, _collection, _model
    if _collection is not None:
        return
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
        _client     = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = _client.get_collection(COLLECTION)
        _model      = SentenceTransformer(MODEL_NAME)
    except Exception:
        _collection = None


def retrieve(query: str, n_results: int = 3) -> list[dict]:
    _init()
    if _collection is None:
        return []
    try:
        from sentence_transformers import SentenceTransformer
        if _model is None:
            return []
        embedding = _model.encode([query]).tolist()
        results   = _collection.query(query_embeddings=embedding, n_results=n_results)
        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            if dist <= DISTANCE_THRESHOLD:
                chunks.append({"text": doc, "metadata": meta, "distance": dist})
        return chunks
    except Exception:
        return []
