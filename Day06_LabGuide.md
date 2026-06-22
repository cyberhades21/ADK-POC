# Day 06 Lab Guide
## eComBot v3 — RAG Hardening: Chunking, Metadata, and Retrieval Validation

---

### Module alignment
This session hardens the RAG layer built on Day 05. The focus is on retrieval quality: better chunking, metadata for traceability, and a systematic validation pass covering correct, partial, and missing matches. This directly supports the capstone's hallucination-guard requirement.

---

### Starting state
- eComBot v3 RAG layer from Day 05 is working.
- `embed_catalog.py` indexes products and FAQ as flat text.
- `retrieve()` returns chunks but chunking is basic.
- No metadata-based filtering yet.

### Target state
- Each chunk carries structured metadata (`source`, `category`, `doc_type`).
- Retrieval is validated against 15+ queries across three match categories.
- Distance threshold is tuned so weak matches are filtered out.
- A rebuild script re-indexes the knowledge base cleanly.

---

## Task 1 — Improve chunk metadata

Update `embed_catalog.py` to include richer metadata per chunk. Good metadata makes debugging and filtering much easier.

**Products — add `category` and `price_band`:**

```python
price_band = "budget" if p["price"] < 20000 else "mid" if p["price"] < 50000 else "premium"
metas.append({
    "source":     "products",
    "doc_type":   "product_catalog",
    "id":         p["id"],
    "name":       p["name"],
    "category":   p["category"],
    "price_band": price_band,
})
```

**FAQ — add `topic` derived from the question keywords:**

```python
topic = "returns" if "return" in f["q"].lower() else \
        "shipping" if "ship" in f["q"].lower() or "deliver" in f["q"].lower() else \
        "payment" if "emi" in f["q"].lower() or "pay" in f["q"].lower() else \
        "warranty" if "warrant" in f["q"].lower() else "general"
metas.append({
    "source":   "faq",
    "doc_type": "faq",
    "topic":    topic,
    "question": f["q"],
})
```

Re-run: `python -m src.rag.embed_catalog`

**Checkpoint:** `retrieve("Redmi Note 13")` returns a chunk whose metadata includes `category: phone`.

---

## Task 2 — Tune the distance threshold

The current threshold of `1.5` may be too loose or too tight for your embedding model. Run these queries and note the distance scores:

```python
from src.rag.retriever import retrieve

test_queries = [
    "What is the return policy?",          # should match faq clearly
    "Samsung TV warranty",                  # should match faq + products
    "Tell me about a product that does not exist",  # should return empty
    "What is the weather tomorrow?",        # should return empty
]

for q in test_queries:
    results = retrieve(q)
    print(f"\n{q}")
    for r in results:
        print(f"  dist={r['distance']:.3f} | {r['text'][:80]}")
```

Adjust `DISTANCE_THRESHOLD` in `retriever.py` until:
- Clearly relevant chunks are included.
- Clearly unrelated queries return zero chunks.

A typical good range for `all-MiniLM-L6-v2` is `1.0–1.3`.

**Checkpoint:** "What is the weather tomorrow?" returns an empty list.

---

## Task 3 — Retrieval validation suite

Write a script `scripts/inspect_kb.py` (or run interactively) that tests 15 queries and prints pass/fail:

**Correct match (answer exists):**

| Query | Expected chunk source |
|-------|-----------------------|
| `What is the return policy?` | faq — returns |
| `How long does shipping take?` | faq — shipping |
| `Do you offer EMI?` | faq — payment |
| `What is the warranty on Samsung TVs?` | faq — warranty |
| `Can I cancel after shipping?` | faq — general |
| `Samsung Galaxy A55 price` | products — phone |
| `Redmi Note 13 specs` | products — phone |
| `DStv decoder description` | products — decoder |

**Partial match (answer partially covered):**

| Query | Expected behavior |
|-------|-------------------|
| `How much is the phone?` | Returns phone chunks; may not know which one |
| `What can I return?` | Returns return policy chunk |
| `Tell me about your TVs` | Returns Samsung TV product chunk |

**No match (hallucination guard must fire):**

| Query | Expected behavior |
|-------|-------------------|
| `What is the best restaurant near me?` | Empty retrieval → fallback |
| `Can I buy airline tickets?` | Empty retrieval → fallback |
| `Tell me about the iPhone 16` | Empty retrieval → fallback |
| `What is today's weather?` | Empty retrieval → fallback |

**Checkpoint:** At least 14 of 15 queries behave as expected. All 4 no-match queries trigger fallback.

---

## Task 4 — Source tag in agent response

When the agent answers from retrieved knowledge, it should indicate the source. Update the grounded instruction to ask for this:

```text
When you answer from retrieved knowledge, end your response with:
"[Source: product catalog]" or "[Source: FAQ]" depending on the chunk metadata.
```

Update the `build_grounded_instruction` helper to pass the source metadata into the context block:

```python
context_lines = [
    f"{c['text']}\n[source: {c['metadata'].get('source', 'unknown')}]"
    for c in chunks
]
```

**Checkpoint:** An answer about the return policy ends with `[Source: FAQ]`. A product spec answer ends with `[Source: product catalog]`.

---

## Task 5 — Clean rebuild script

Add a `--rebuild` flag to `embed_catalog.py` (or verify it already deletes and recreates the collection). Document how to run a rebuild after adding new products or FAQ entries:

```bash
python -m src.rag.embed_catalog
```

**Checkpoint:** Running the script twice doesn't create duplicate chunks.

---

## Task 6 — Keep tools working alongside RAG

Confirm that order tool calls still work when RAG is active:

| Turn | Input | Expected |
|------|-------|----------|
| 1 | `Where is my order ORD-001?` | Tool called; not RAG |
| 2 | `What is the return policy?` | RAG retrieval; not tool |
| 3 | `Cancel my order ORD-002.` | Tool called; not RAG |
| 4 | `What is the warranty on the Samsung TV?` | RAG retrieval; not tool |

**Checkpoint:** Tool and RAG paths do not interfere with each other.

---

## Verification checklist
- [ ] Metadata includes `source`, `doc_type`, `category` or `topic` on every chunk.
- [ ] Distance threshold tuned — unrelated queries return empty list.
- [ ] 15-query validation suite run and results documented.
- [ ] At least 14/15 queries behave correctly.
- [ ] All 4 out-of-scope queries trigger the fallback message.
- [ ] Source tag visible in agent responses from RAG.
- [ ] Rebuild script recreates collection cleanly without duplicates.
- [ ] Order tools still work alongside RAG without interference.
