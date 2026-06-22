"""Print all chunks in the ChromaDB knowledge base: python -m scripts.inspect_kb"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
import chromadb

CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"
COLLECTION = "ecombot_kb"

client     = chromadb.PersistentClient(path=str(CHROMA_DIR))
collection = client.get_collection(COLLECTION)
results    = collection.get(include=["documents", "metadatas"])

for doc, meta in zip(results["documents"], results["metadatas"]):
    print(f"[{meta.get('type','?')} | {meta.get('source','?')}]")
    print(f"  {doc[:120]}...")
    print()
