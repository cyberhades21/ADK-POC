# Day 10 Lab Guide
## eComBot v7 — Generative UI with Chainlit

---

### Module alignment
This session adds a Chainlit chat interface with rich UI components: product cards, order status cards, agent routing trace, RAG source tags, and a model badge. Real-time streaming is enabled. Layers added in Days 11–12 (reasoning panel, admin panel, blocked indicator) build directly on top of what is built here.

---

### Starting state
- eComBot v6 is working with Orchestrator + Support Agent + Sales Agent.
- ADK Web is the current UI — functional but plain.
- No Chainlit UI exists yet.

### Target state
- `src/ui/app.py` is a Chainlit app that connects to the three-agent system.
- Product cards show name, price, and stock badge.
- Order status cards show ID, status, ETA, and a cancel button.
- Agent routing trace shows which agent handled each response.
- RAG source tag visible when the answer comes from the knowledge base.
- Model badge shows which model was used.
- Responses stream in real time.

### New dependency

```
chainlit
```

Add to `requirements.txt` and install.

### Repository addition

```text
ecombot/
└── src/
    └── ui/
        ├── __init__.py
        └── app.py
```

---

## Task 1 — Basic Chainlit app

Create `src/ui/app.py` with the minimal Chainlit structure connected to the Orchestrator:

```python
import chainlit as cl
from src.agents.orchestrator import orchestrator

@cl.on_chat_start
async def on_start():
    cl.user_session.set("session_id", "demo-session")
    await cl.Message(content="Hi! I'm eComBot. How can I help you today?").send()

@cl.on_message
async def on_message(message: cl.Message):
    user_text = message.content
    # Route through the orchestrator
    # (Implementation depends on how you run ADK agents outside ADK Web)
    response = await run_agent(user_text)
    await cl.Message(content=response).send()
```

For running ADK agents in Chainlit, use the ADK runner directly:

```python
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

session_service = InMemorySessionService()
runner = Runner(agent=orchestrator, app_name="eComBot", session_service=session_service)

async def run_agent(user_text: str) -> str:
    session_id = cl.user_session.get("session_id", "demo-session")
    from google.genai.types import Content, Part
    response_text = ""
    async for event in runner.run_async(
        user_id="user",
        session_id=session_id,
        new_message=Content(role="user", parts=[Part(text=user_text)]),
    ):
        if event.is_final_response() and event.content and event.content.parts:
            response_text = event.content.parts[0].text or ""
    return response_text
```

Start with: `chainlit run src/ui/app.py`

**Checkpoint:** Chainlit opens in browser, agent responds to a plain text query.

---

## Task 2 — Streaming responses

Replace the single `Message.send()` with a streaming response so text appears token by token:

```python
@cl.on_message
async def on_message(message: cl.Message):
    user_text = message.content
    session_id = cl.user_session.get("session_id", "demo-session")

    msg = cl.Message(content="")
    await msg.send()

    from google.genai.types import Content, Part
    async for event in runner.run_async(
        user_id="user",
        session_id=session_id,
        new_message=Content(role="user", parts=[Part(text=user_text)]),
    ):
        if event.content and event.content.parts:
            chunk = event.content.parts[0].text or ""
            if chunk:
                await msg.stream_token(chunk)

    await msg.update()
```

**Checkpoint:** Agent response streams token by token instead of appearing all at once.

---

## Task 3 — Agent routing trace

After each response, show which agent handled it using a `cl.Text` element:

```python
# After streaming is complete, check which agent responded
agent_name = cl.user_session.get("last_agent", "Orchestrator")
await cl.Text(
    name="routing_trace",
    content=f"Handled by: **{agent_name}**",
    display="inline",
).send()
```

Store the agent name during the run by inspecting the ADK event's author field:

```python
async for event in runner.run_async(...):
    if hasattr(event, "author") and event.author:
        cl.user_session.set("last_agent", event.author)
    ...
```

**Checkpoint:** Every response shows "Handled by: Support_Agent" or "Handled by: Sales_Agent".

---

## Task 4 — Order status card

When a response contains order data (detected by looking for keys like `status`, `eta`, `carrier`), render a structured card instead of plain text.

Parse the agent's response for order dict output and render:

```python
import json

def try_parse_order(text: str) -> dict | None:
    try:
        data = json.loads(text)
        if "order_id" in data and "status" in data:
            return data
    except Exception:
        pass
    return None

# In on_message, after collecting the full response:
order = try_parse_order(full_response)
if order:
    status_color = {"Shipped": "🟡", "Delivered": "🟢", "Cancelled": "🔴", "Processing": "🔵"}.get(order["status"], "⚪")
    card = f"""**Order {order['order_id']}**
Status: {status_color} {order['status']}
ETA: {order.get('eta', '—')}
Carrier: {order.get('carrier', '—')}"""
    await cl.Message(content=card).send()
else:
    await cl.Message(content=full_response).send()
```

**Checkpoint:** "Where is my order ORD-001?" renders a formatted order card.

---

## Task 5 — Product card

When the response contains product data from `lookup_product`, render a product card:

```python
def try_parse_product_list(text: str) -> list | None:
    try:
        data = json.loads(text)
        if "results" in data:
            return data["results"]
    except Exception:
        pass
    return None

products = try_parse_product_list(full_response)
if products:
    for p in products:
        stock_badge = "✅ In Stock" if p.get("stock", 0) > 0 else "❌ Out of Stock"
        card = f"**{p['name']}** — ₹{p['price']} | {stock_badge}"
        await cl.Message(content=card).send()
```

**Checkpoint:** "Do you have the Redmi Note 13?" renders a product card with stock badge.

---

## Task 6 — RAG source tag

When the answer comes from retrieved knowledge, show the source. Store the RAG source in session state during the before_model_callback and pass it through:

```python
source = cl.user_session.get("rag_source")
if source:
    await cl.Text(
        name="source_tag",
        content=f"[Source: {source}]",
        display="inline",
    ).send()
    cl.user_session.set("rag_source", None)
```

**Checkpoint:** "What is the return policy?" shows `[Source: FAQ]` below the answer.

---

## Task 7 — Model badge

Show which model was used from `last_model_used` in session state:

```python
model_used = cl.user_session.get("last_model_used", "unknown")
short_name = model_used.split("/")[-1]
await cl.Text(
    name="model_badge",
    content=f"Model: `{short_name}`",
    display="inline",
).send()
```

**Checkpoint:** Each response shows the model name badge.

---

## Task 8 — Graceful fallback for unstructured output

If the response is plain text (not a structured card), it must still display cleanly. The card parsing in Tasks 4 and 5 already handles this — plain text falls through to `cl.Message(content=full_response)`. Confirm this works for:
- A greeting response.
- A RAG-grounded FAQ answer.
- A fallback "I couldn't find that information" message.

**Checkpoint:** All three cases display cleanly without card rendering errors.

---

## Verification checklist
- [ ] `chainlit run src/ui/app.py` starts and opens in browser.
- [ ] Agent responses stream in real time.
- [ ] Agent routing trace shows which agent handled each response.
- [ ] Order status queries render an order card (ID, status, ETA, carrier).
- [ ] Product queries render a product card (name, price, stock badge).
- [ ] RAG answers show `[Source: FAQ]` or `[Source: product catalog]`.
- [ ] Model badge shows the model used for each response.
- [ ] Unstructured text responses display cleanly without errors.
