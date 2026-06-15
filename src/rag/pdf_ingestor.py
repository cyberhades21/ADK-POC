"""
Ingest a PDF into the ChromaDB knowledge base.
Run: python -m src.rag.pdf_ingestor --file data/ecom_handbook.pdf
"""
import sys
import argparse
import hashlib
from pathlib import Path

try:
    from pypdf import PdfReader
    import chromadb
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Run: pip install pypdf chromadb sentence-transformers")
    sys.exit(1)

CHROMA_DIR = Path(__file__).parent.parent.parent / "chroma_db"
COLLECTION = "ecombot_kb"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 400
OVERLAP    = 80


def chunk_text(text: str) -> list[str]:
    chunks, start = [], 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end].strip())
        start += CHUNK_SIZE - OVERLAP
    return [c for c in chunks if len(c) > 40]


def ingest(pdf_path: Path):
    reader     = PdfReader(str(pdf_path))
    client     = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(COLLECTION)
    model      = SentenceTransformer(MODEL_NAME)

    all_ids, all_texts, all_embeddings, all_meta = [], [], [], []

    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for chunk in chunk_text(text):
            uid = hashlib.md5(chunk.encode()).hexdigest()
            all_ids.append(uid)
            all_texts.append(chunk)
            all_meta.append({
                "type": "pdf",
                "source": pdf_path.name,
                "page": str(page_num),
                "section": chunk[:60],
            })

    all_embeddings = model.encode(all_texts).tolist()
    collection.upsert(ids=all_ids, documents=all_texts,
                      embeddings=all_embeddings, metadatas=all_meta)
    print(f"Ingested {len(all_ids)} chunks from {pdf_path.name}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to PDF file")
    args   = parser.parse_args()
    ingest(Path(args.file))
