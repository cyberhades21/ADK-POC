# eComBot Capstone — Feature Guide
## Aureum Serpentis Customer Support Agent (Days 1–8)

This document explains every feature implemented, what each file does, and what each key line of code means — so you can answer proctor questions confidently.

---

## Architecture Overview

```
Browser (localhost:3000)
    │
    ▼
ui/server.py  ← FastAPI proxy (handles CORS, serves UI, exposes DB/RAG APIs)
    │
    ├── /apps/* /run*  ──► adk web src (localhost:8000)  ← Google ADK runtime
    │                            │
    │                       src/agent.py  ← root_agent (LlmAgent)
    │                            │
    │                       src/tools/    ← order_tools, product_tools
    │                       src/services/ ← db.py, session_store.py
    │
    ├── /api/db/*    ──► SQLite (ecombot.db)
    └── /api/rag/*   ──► ChromaDB (chroma_db/)
```

---

## Day 1 — First Agent with Google ADK

**File:** `src/agent.py`

```python
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
```
- `LlmAgent` — the core ADK class that wraps an LLM and gives it a name, instruction, and tools.
- `LiteLlm` — ADK's adapter for non-Google models. It lets ADK talk to Ollama, OpenRouter, or any OpenAI-compatible endpoint.

```python
root_agent = LlmAgent(
    name="eComBot_Support",
    model=model,
    instruction=full_instruction,
    description="Aureum Serpentis customer support agent.",
)
```
- ADK discovers the agent by looking for a variable called exactly `root_agent` in `src/agent.py`. The name must match.
- `instruction` is the system prompt — it tells the model who it is and what it can do.
- `description` is used by ADK internally when multiple agents are connected.

**Why `adk web src`?**
ADK looks inside the `src/` folder for a file called `agent.py` and imports `root_agent` from it. The `adk web` command starts a local web server on port 8000 with a chat UI and REST API.

---

## Day 2 — Instruction Variants

**Files:** `src/agents/support_instructions_v1.txt`, `v2.txt`, `v3.txt`

```python
INSTRUCTION_VERSION = os.getenv("INSTRUCTION_VERSION", "v1")
_instruction_file = _dir / "agents" / f"support_instructions_{INSTRUCTION_VERSION}.txt"
instruction = _instruction_file.read_text(encoding="utf-8")
```
- The instruction file is loaded at startup based on the `INSTRUCTION_VERSION` environment variable in `.env`.
- Changing `INSTRUCTION_VERSION=v2` and restarting ADK switches the agent's tone without changing any code.
- v1 = warm concierge, v2 = formal professional, v3 = minimal terse.

**Why environment variables?**
So you can change behaviour without touching code — a standard software engineering practice called configuration management.

---

## Day 3 — Session Memory

**File:** `src/agent.py` — `extract_and_inject_session()` callback

```python
def extract_and_inject_session(callback_context: CallbackContext, llm_request: LlmRequest) -> None:
```
- This is a `before_model_callback` — ADK calls this function before every LLM request.
- It runs between the user sending a message and the model generating a reply.

```python
state = callback_context.state
```
- `state` is ADK's built-in per-session key-value store. It persists across turns in the same conversation.
- This replaces Redis — ADK handles the in-memory session state natively.

```python
order_match = re.search(r'\bORD-\d+\b', last_user_text, re.IGNORECASE)
if order_match:
    state["last_order_id"] = order_match.group(0).upper()
```
- Scans the user's message for a pattern like `ORD-001` using a regular expression.
- `\b` = word boundary (so `WORD-001` wouldn't match), `\d+` = one or more digits.
- Saves it to session state so the agent doesn't ask for the order ID again.

```python
name_match = re.search(
    r"(?:my name is|i am|i'm|this is)\s+([A-Z][a-z]+...)",
    last_user_text, re.IGNORECASE
)
```
- Detects when the customer introduces themselves ("My name is Priya") and saves their name.
- The captured group `([A-Z][a-z]+...)` matches a proper name like "Priya" or "Priya Menon".

---

## Day 4 — SQLite Database + Tools

### Database connection
**File:** `src/services/db.py`

```python
DB_PATH = os.getenv("DB_PATH", "ecombot.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
```
- `sqlite3` is built into Python — no installation needed.
- `conn.row_factory = sqlite3.Row` makes query results behave like dictionaries (`row["order_id"]`) instead of tuples (`row[0]`).
- `DB_PATH` is read from `.env` so the database location is configurable.

**Why SQLite instead of PostgreSQL?**
SQLite is a file-based database — no server to install, no connection strings, no Docker. Perfect for development and capstone projects.

### In-memory session store (replaces Redis)
**File:** `src/services/session_store.py`

```python
_store: dict = {}

def set_val(session_id: str, key: str, value):
    _store.setdefault(session_id, {})[key] = value
```
- `_store` is a plain Python dictionary at module level — it lives in memory for the lifetime of the process.
- `setdefault(session_id, {})` — if this session ID doesn't exist yet, create an empty dict for it.
- **Trade-off vs Redis:** Redis persists across restarts and works across multiple servers. This dict resets when the process stops — acceptable for a capstone.

### Order tools
**File:** `src/tools/order_tools.py`

```python
def get_order_status(order_id: str) -> dict:
    order_id = order_id.strip().upper()
    if not order_id.startswith("ORD-"):
        return {"error": "Invalid format. Use ORD-XXX (e.g. ORD-001)."}
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM orders WHERE order_id = ?", (order_id,)
        ).fetchone()
```
- `.strip().upper()` — normalise input so "ord-001 " and "ORD-001" both work.
- `"SELECT * FROM orders WHERE order_id = ?"` — the `?` is a parameterised query. This prevents SQL injection — user input never gets concatenated into the SQL string directly.
- `fetchone()` — returns one row or `None` if not found.

```python
def cancel_order(order_id: str) -> dict:
    if not row["can_cancel"]:
        return {"error": f"Order {order_id} cannot be cancelled (status: {row['status']})."}
    conn.execute(
        "UPDATE orders SET status = 'Cancelled', can_cancel = 0 WHERE order_id = ?", ...
    )
```
- `can_cancel` is an integer column (1 = yes, 0 = no). Shipped/Delivered orders have `can_cancel=0`.
- After cancelling, `can_cancel` is set to 0 so it can't be cancelled twice.

---

## Day 5 — RAG Knowledge Base

**RAG = Retrieval-Augmented Generation.** Instead of relying purely on the model's training data, we store our own documents and retrieve relevant ones before answering.

### Embedding and indexing
**File:** `src/rag/embed_catalog.py`

```python
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
embeddings = model.encode(texts).tolist()
```
- `SentenceTransformer` converts text into a list of numbers (a vector/embedding) that represents the semantic meaning of the text.
- Similar meanings produce similar vectors — "return policy" and "can I get a refund?" will have close vectors even though the words differ.
- `all-MiniLM-L6-v2` is a small, fast model that runs locally with no API key.

```python
client = chromadb.PersistentClient(path=str(CHROMA_DIR))
collection = client.get_or_create_collection(COLLECTION)
collection.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
```
- `ChromaDB` is a vector database — it stores embeddings and lets you search by similarity.
- `PersistentClient` saves the data to disk (`chroma_db/` folder) so it survives restarts.
- `upsert` = insert or update. If a document with the same `id` already exists, it updates it.

### Retrieval
**File:** `src/rag/retriever.py`

```python
embedding = _model.encode([query]).tolist()
results = _collection.query(query_embeddings=embedding, n_results=n_results)
```
- The user's query is converted to an embedding using the same model used during indexing.
- ChromaDB finds the stored documents whose embeddings are closest to the query embedding.

```python
DISTANCE_THRESHOLD = 1.5
if dist <= DISTANCE_THRESHOLD:
    chunks.append(...)
```
- `distance` measures how different two vectors are. Lower = more similar.
- If distance > 1.5, the match is too weak — we discard it rather than returning irrelevant results.
- This is the "graceful fallback" — instead of hallucinating, the agent says it doesn't have that information.

---

## Day 6 — PDF Ingestion

**File:** `src/rag/pdf_ingestor.py`

```python
from pypdf import PdfReader
reader = PdfReader(str(pdf_path))
for page_num, page in enumerate(reader.pages, start=1):
    text = page.extract_text() or ""
```
- `pypdf` reads the text content from each page of a PDF.
- `or ""` handles pages with no extractable text (e.g. scanned image pages).

```python
CHUNK_SIZE = 400
OVERLAP    = 80

def chunk_text(text: str) -> list[str]:
    chunks, start = [], 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end].strip())
        start += CHUNK_SIZE - OVERLAP
```
- Long documents are split into chunks of ~400 characters.
- `OVERLAP = 80` means consecutive chunks share 80 characters — this prevents a sentence being cut in half and losing context at chunk boundaries.

```python
uid = hashlib.md5(chunk.encode()).hexdigest()
```
- Each chunk gets a unique ID derived from its content using MD5 hashing.
- If the same PDF is ingested twice, the same chunks produce the same IDs, so `upsert` deduplicates them automatically.

---

## Day 7 — LiteLLM Model Router

**File:** `src/services/llm_router.py`

```python
COMPLEX_KEYWORDS = {
    "compare", "recommend", "complaint", "refund",
    "cancel", "broken", "damage", "vs", "better", "worse", "difference"
}

def classify(message: str) -> str:
    words = set(message.lower().split())
    return "deep" if words & COMPLEX_KEYWORDS else "fast"
```
- `set(message.lower().split())` — converts the message to a set of lowercase words.
- `words & COMPLEX_KEYWORDS` — set intersection: returns words that appear in both sets.
- If any complex keyword is found → route to the `DEEP_MODEL`. Otherwise → `FAST_MODEL`.
- This is called **model routing** — sending different queries to different models based on complexity.

```python
logging.basicConfig(filename=str(LOG_FILE), level=logging.INFO, ...)

logging.info(f"complexity={complexity} model={model} query={user_message[:60]}")
```
- Every routing decision is written to `logs/routing.log` with a timestamp.
- This is **observability** — being able to see what decisions the system made after the fact.

```python
try:
    resp = litellm.completion(model=DEEP_MODEL, ...)
except Exception as e:
    resp = litellm.completion(model=FAST_MODEL, ...)
```
- If the deep model fails (not installed, timeout, etc.), it falls back to the fast model.
- This is a **graceful degradation** pattern — the system keeps working even when one component fails.

---

## Day 8 — FastMCP External Tool Servers

**Files:** `src/services/orders_server.py`, `src/services/inventory_server.py`

**MCP = Model Context Protocol** — a standard way to expose tools as separate services that an AI agent can call over a network.

```python
from fastmcp import FastMCP
mcp = FastMCP("eComBot Orders")

@mcp.tool()
def order_status(order_id: str) -> dict:
    """Get the current status of an order by ID (format: ORD-XXX)."""
    return get_order_status(order_id)
```
- `@mcp.tool()` decorator registers a Python function as an MCP tool.
- The docstring becomes the tool description — the AI agent reads it to understand what the tool does.
- `FastMCP` handles all the protocol details — you just write normal Python functions.

**Why MCP instead of calling the function directly?**
MCP tools run as separate processes. This means:
- Tools can be on different machines or containers.
- Tools can be written in different languages.
- The agent doesn't need the tool's code — it only needs to know the tool exists and what it does.

---

## Bonus — UI Proxy Server

**File:** `ui/server.py`

**Why is there a proxy server?**
Browsers enforce CORS (Cross-Origin Resource Sharing) — a security rule that blocks JavaScript from making requests to a different domain/port than the page itself. The UI is on port 3000, ADK is on port 8000 — that's a different port, so the browser blocks it.

```python
async def handle(request: Request) -> Response:
    if request.method == "OPTIONS":
        return Response(status_code=200, headers=CORS_HEADERS)
```
- `OPTIONS` is a CORS preflight — the browser sends this first to ask "are you allowed to accept my request?" 
- We respond with 200 immediately so the browser proceeds with the actual request.

```python
if any(full_path.startswith(p) for p in PROXY_PREFIXES):
    url = f"{ADK}/{path}"
    ...
    r = await client.request(request.method, url, headers=headers, content=body)
```
- If the path starts with `/apps/` or `/run`, forward it to ADK on port 8000.
- The browser thinks it's talking to port 3000 the whole time — no CORS issue.

```python
headers = {k: v for k, v in request.headers.items()
           if k.lower() not in ("host", "content-length", "origin", "referer")}
```
- Strip `origin` and `referer` headers before forwarding — ADK checks these and rejects requests from different origins.
- By removing them, ADK sees the request as coming from itself.

---

## Common Proctor Questions

**Q: Why use Google ADK instead of calling the LLM directly?**
ADK provides session management, tool calling, multi-agent orchestration, streaming, and a ready-made web UI. Without it you'd build all of that manually.

**Q: Why Ollama instead of OpenAI?**
Ollama runs models locally — no API key, no cost, no internet required, no data leaving your machine. For a capstone, this means anyone can run it without signing up for anything.

**Q: What is the difference between a tool and a prompt in ADK?**
A prompt is static text that tells the model how to behave. A tool is a Python function the model can call at runtime to get live data (like checking an actual database). Prompts give the model knowledge; tools give it actions.

**Q: Why SQLite instead of PostgreSQL?**
SQLite is a file — `ecombot.db`. No server, no configuration, no Docker. It uses the exact same SQL syntax as PostgreSQL, so the concepts transfer directly. For production you'd swap `sqlite3.connect()` for a PostgreSQL connection string.

**Q: What is an embedding?**
A list of numbers (vector) that represents the meaning of a piece of text. Two sentences that mean the same thing have similar vectors even if they use different words. This is how semantic search works — we search by meaning, not keyword matching.

**Q: What is the distance threshold in the RAG retriever?**
`DISTANCE_THRESHOLD = 1.5` — if the closest match in the knowledge base has a distance greater than 1.5, it means nothing relevant was found. We return an empty list instead of forcing a bad match, so the agent admits it doesn't know rather than hallucinating.

**Q: What is MCP and why does it matter?**
Model Context Protocol is an open standard (from Anthropic) for connecting AI agents to external tools and data sources. Instead of hardcoding tool logic inside the agent, MCP lets tools live as independent services. This is the same idea as microservices — separation of concerns.

**Q: Why does the session store reset on restart?**
It's a plain Python dictionary (`_store = {}`). When the process stops, the dictionary is gone. Redis would persist this to disk. For a capstone this is acceptable — the trade-off is acknowledged explicitly in the code comment.
