"""
Embeds products.json and faq.json into ChromaDB.
Run once: python -m src.rag.embed_catalog
Add --rebuild flag to wipe and recreate the collection.
"""
import sys
import json
import argparse
from pathlib import Path

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Run: pip install chromadb sentence-transformers")
    sys.exit(1)

DATA_DIR   = Path(__file__).parent.parent.parent / "data"
CHROMA_DIR = Path(__file__).parent.parent.parent / "chroma_db"
COLLECTION = "ecombot_kb"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def load_documents():
    docs = []
    products = json.loads((DATA_DIR / "products.json").read_text())
    for p in products:
        text = f"{p['name']} — ₹{p['price']}. {p['description']} Warranty: {p.get('warranty','')} Shipping: {p.get('shipping','')}"
        docs.append({"id": p["id"], "text": text, "type": "product", "source": "products.json"})

    faqs = json.loads((DATA_DIR / "faq.json").read_text())
    for f in faqs:
        text = f"Q: {f['question']} A: {f['answer']}"
        docs.append({"id": f["id"], "text": text, "type": "faq", "source": "faq.json"})
    return docs


def embed(rebuild=False):
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    if rebuild:
        try:
            client.delete_collection(COLLECTION)
            print("Existing collection deleted.")
        except Exception:
            pass

    collection = client.get_or_create_collection(COLLECTION)
    model = SentenceTransformer(MODEL_NAME)
    docs  = load_documents()

    texts     = [d["text"] for d in docs]
    ids       = [d["id"]   for d in docs]
    metadatas = [{"type": d["type"], "source": d["source"]} for d in docs]
    embeddings = model.encode(texts).tolist()

    collection.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
    print(f"Embedded {len(docs)} documents into '{COLLECTION}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    embed(rebuild=args.rebuild)
