# Day 05 Lab Guide
## eComBot v3 — RAG Knowledge Base with ChromaDB

---

### Module alignment
This session adds the grounding layer. eComBot v3 answers product and FAQ questions from a vector knowledge base instead of inventing details. This RAG layer is used by all agents in the final system.

---

### Starting state
- eComBot v2 from Day 04 is working with SQLite-backed tools and session state.
- No RAG layer exists yet.

### Target state
- Product catalog and FAQ indexed into ChromaDB using sentence-transformers.
- `retrieve(query)` returns relevant chunks.
- Agent injects retrieved context before answering knowledge questions.
- Hallucination guard: unanswerable queries return a graceful fallback.

### Repository additions

```text
ecombot/
├── src/
│   └── rag/
│       ├── __init__.py
│       ├── embed_catalog.py
│       └── retriever.py
├── data/
│   ├── products.json
│   └── faq.json
└── chroma_db/          ← created by embed_catalog.py
```

Add to `requirements.txt`:
```
chromadb
sentence-transformers
```

---

## Task 1 — Create the knowledge base files

**`data/products.json`** — one entry per product, covering specs, price, and warranty:

```json
[
  {
    "id": "PRD-001",
    "name": "Samsung Galaxy A55",
    "category": "phone",
    "price": 32999,
    "description": "6.6-inch AMOLED, 50MP camera, 5000mAh battery.",
    "warranty": "1 year manufacturer warranty.",
    "stock": 15
  },
  {
    "id": "PRD-002",
    "name": "Redmi Note 13",
    "category": "phone",
    "price": 17999,
    "description": "6.67-inch AMOLED, 108MP camera, 5000mAh battery.",
    "warranty": "1 year manufacturer warranty.",
    "stock": 28
  },
  {
    "id": "PRD-003",
    "name": "Samsung 43-inch 4K Smart TV",
    "category": "tv",
    "price": 42999,
    "description": "4K UHD, Smart TV with built-in streaming apps.",
    "warranty": "2 year manufacturer warranty.",
    "stock": 7
  },
  {
    "id": "PRD-004",
    "name": "DStv HD Decoder",
    "category": "decoder",
    "price": 3499,
    "description": "Full HD satellite decoder, compatible with all DStv packages.",
    "warranty": "1 year manufacturer warranty.",
    "stock": 40
  }
]
```

**`data/faq.json`** — support questions and answers:

```json
[
  {"q": "What is your return policy?", "a": "You may return items within 7 days of delivery if unused and in original packaging."},
  {"q": "How long does shipping take?", "a": "Standard delivery takes 3–5 business days. Express delivery takes 1–2 business days."},
  {"q": "Do you offer EMI?", "a": "Yes, zero-cost EMI is available on orders above ₹10,000 with select bank cards."},
  {"q": "What is the warranty on Samsung TVs?", "a": "Samsung TVs carry a 2-year manufacturer warranty covering manufacturing defects."},
  {"q": "Can I cancel my order after it has shipped?", "a": "No. Orders that have shipped cannot be cancelled. You may initiate a return after delivery."},
  {"q": "How do I track my order?", "a": "Ask the agent for your order status using your order ID (format: ORD-XXX)."}
]
```

---

## Task 2 — Build the embedding script

Create `src/rag/embed_catalog.py`. This script runs once to index all knowledge into ChromaDB.

```python
import json
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer

DATA_DIR   = Path(__file__).parent.parent.parent / "data"
CHROMA_DIR = Path(__file__).parent.parent.parent / "chroma_db"
COLLECTION = "ecombot_kb"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

def embed():
    client     = chromadb.PersistentClient(path=str(CHROMA_DIR))
    model      = SentenceTransformer(MODEL_NAME)

    # Delete and recreate for a clean rebuild
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION)

    docs, metas, ids = [], [], []

    # Products
    products = json.loads((DATA_DIR / "products.json").read_text())
    for p in products:
        text = (
            f"Product: {p['name']}. Category: {p['category']}. "
            f"Price: ₹{p['price']}. {p['description']} {p['warranty']}"
        )
        docs.append(text)
        metas.append({"source": "products", "id": p["id"], "name": p["name"]})
        ids.append(f"prod-{p['id']}")

    # FAQ
    faqs = json.loads((DATA_DIR / "faq.json").read_text())
    for i, f in enumerate(faqs):
        text = f"Q: {f['q']} A: {f['a']}"
        docs.append(text)
        metas.append({"source": "faq", "question": f["q"]})
        ids.append(f"faq-{i}")

    embeddings = model.encode(docs).tolist()
    collection.add(documents=docs, embeddings=embeddings, metadatas=metas, ids=ids)
    print(f"Indexed {len(docs)} chunks into '{COLLECTION}'.")

if __name__ == "__main__":
    embed()
```

Run: `python -m src.rag.embed_catalog`

**Checkpoint:** Script completes without errors. `chroma_db/` directory appears.

---

## Task 3 — Build the retriever

Create `src/rag/retriever.py`:

```python
from pathlib import Path

CHROMA_DIR         = Path(__file__).parent.parent.parent / "chroma_db"
COLLECTION         = "ecombot_kb"
MODEL_NAME         = "sentence-transformers/all-MiniLM-L6-v2"
DISTANCE_THRESHOLD = 1.5

_client = _collection = _model = None

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
    """Return top relevant chunks. Empty list if collection unavailable."""
    _init()
    if _collection is None:
        return []
    try:
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
```

**Checkpoint:** `retrieve("Samsung TV warranty")` returns at least one relevant chunk.

---

## Task 4 — Ground the agent

Update `support_agent.py` to retrieve context and inject it before answering product/FAQ questions.

Add a helper that wraps the agent's instruction with retrieved chunks:

```python
from src.rag.retriever import retrieve

def build_grounded_instruction(base_instruction: str, user_query: str) -> str:
    chunks = retrieve(user_query)
    if not chunks:
        return base_instruction
    context_lines = [c["text"] for c in chunks]
    context_block = "\n\n## Retrieved Knowledge\n" + "\n---\n".join(context_lines)
    return base_instruction + context_block + "\n\nAnswer only from the retrieved knowledge above. If the answer is not there, say you could not find that information."
```

Call this in your `before_model_callback` to enrich the system prompt for product/FAQ queries.

**Checkpoint:** Agent answers "What is the return policy?" using FAQ text, not a fabricated answer.

---

## Task 5 — Add the hallucination guard

Add to the instruction (and reinforce in the callback):

```text
If you cannot find the answer in the retrieved knowledge, respond with:
"I couldn't find that information in our knowledge base. Please contact support for details."
Do not invent product specs, prices, warranties, or policies.
```

**Checkpoint:** Asking "What is the warranty on the Flying Car X?" triggers the fallback message.

---

## Task 6 — Validate retrieval quality

Test these queries directly via `retrieve()` in a Python shell or small script:

| Query | Expected source | Expected behavior |
|-------|----------------|-------------------|
| `What is the return policy?` | faq | Returns return policy chunk |
| `Samsung TV warranty` | products + faq | Returns Samsung TV warranty text |
| `How long does shipping take?` | faq | Returns shipping FAQ |
| `What is the price of Redmi Note 13?` | products | Returns Redmi pricing chunk |
| `Tell me about a product that does not exist` | — | Returns empty list → fallback fires |
| `What is the weather tomorrow?` | — | Returns empty list → fallback fires |

**Checkpoint:** At least 4 of 6 queries return the correct source. Both fallback cases trigger correctly.

---

## Verification checklist
- [ ] `data/products.json` and `data/faq.json` exist with realistic content.
- [ ] `src/rag/embed_catalog.py` indexes both files into ChromaDB.
- [ ] `src/rag/retriever.py` returns relevant chunks within the distance threshold.
- [ ] Agent injects retrieved context into the system prompt.
- [ ] Agent answers only from grounded context.
- [ ] Unanswerable queries return the fallback message.
- [ ] Existing tools (`get_order_status`, `cancel_order`, `lookup_product`) still work.
