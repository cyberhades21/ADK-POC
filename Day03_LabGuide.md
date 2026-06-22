# Day 03 Lab Guide
## eComBot v2 — Tool Calling and In-Memory Session State

---

### Module alignment
This session adds the first production capability to eComBot: callable tools and short-term session memory. The tool layer and session state established here carry forward through the entire capstone.

---

### Starting state
- eComBot v1 from Day 01–02 is working in ADK Web.
- Repository has `src/agents/`, `src/config/`, and `tests/`.
- OpenRouter key is in `.env`.

### Target state
- `get_order_status(order_id)` tool is implemented and registered.
- Agent calls the tool when a customer asks about their order.
- In-memory session state stores customer name and last order ID across turns.

### Repository layout

```text
ecombot/
├── src/
│   ├── agents/
│   │   └── support_agent.py
│   ├── tools/
│   │   └── order_tools.py
│   └── config/
│       └── settings.py
├── tests/
│   └── test_support_agent_manual.md
├── .env
└── requirements.txt
```

---

## Task 1 — Create the tool module

Implement `src/tools/order_tools.py` with a simple mock dictionary for now.

```python
MOCK_ORDERS = {
    "ORD-001": {"order_id": "ORD-001", "status": "Shipped",     "eta": "5 Jun 2026", "carrier": "BlueDart"},
    "ORD-002": {"order_id": "ORD-002", "status": "Processing",  "eta": "7 Jun 2026", "carrier": "DTDC"},
    "ORD-003": {"order_id": "ORD-003", "status": "Delivered",   "eta": "Already delivered", "carrier": "FedEx"},
}

def get_order_status(order_id: str) -> dict:
    """Look up the current status of an order by its ID (format: ORD-XXX)."""
    order_id = order_id.strip().upper()
    if not order_id.startswith("ORD-"):
        return {"error": "Invalid format. Use ORD-XXX (e.g. ORD-001)."}
    order = MOCK_ORDERS.get(order_id)
    if not order:
        return {"error": f"Order {order_id} not found. Please check the ID."}
    return order
```

**Checkpoint:** Call `get_order_status("ORD-001")` directly in Python — confirm it returns a dict.

---

## Task 2 — Register the tool with the agent

1. Import `get_order_status` in `support_agent.py`.
2. Add it to the `tools=[]` list on `LlmAgent`.
3. Update the instruction to tell the agent when to call the tool:

```text
When a customer asks about their order, use the get_order_status tool.
Ask for the order ID if it is missing. Do not guess order details.
```

**Checkpoint:** ADK Web shows the tool listed as available for the agent.

---

## Task 3 — Add in-memory session state

ADK's `InMemorySessionService` persists state across turns within a session. Use `callback_context.state` to store and read values.

Add a `before_model_callback` that:
1. Extracts a customer name from phrases like "my name is Priya".
2. Extracts an order ID matching `ORD-\d+` from the user message.
3. Injects both into the system prompt so the agent can use them in replies.

```python
import re
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest

def extract_and_inject_session(callback_context: CallbackContext, llm_request: LlmRequest) -> None:
    state = callback_context.state
    last_user_text = ""
    for content in reversed(llm_request.contents or []):
        if hasattr(content, "role") and content.role == "user":
            if content.parts:
                last_user_text = content.parts[0].text or ""
            break

    order_match = re.search(r'\bORD-\d+\b', last_user_text, re.IGNORECASE)
    if order_match:
        state["last_order_id"] = order_match.group(0).upper()

    name_match = re.search(
        r"(?:my name is|i am|i'm|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        last_user_text, re.IGNORECASE
    )
    if name_match:
        state["customer_name"] = name_match.group(1).strip()

    name = state.get("customer_name")
    order_id = state.get("last_order_id")
    if not name and not order_id:
        return

    lines = ["\n## Session Memory"]
    if name:
        lines.append(f"- Customer name: {name}. Use their name naturally.")
    if order_id:
        lines.append(f"- Last order mentioned: {order_id}. Do not ask for it again.")

    enriched = full_instruction + "\n".join(lines)
    for content in llm_request.contents or []:
        if hasattr(content, "role") and content.role == "system":
            if content.parts:
                content.parts[0].text = enriched
            return
```

Pass `before_model_callback=extract_and_inject_session` to `LlmAgent`.

**Checkpoint:** ADK Web state panel shows `customer_name` and `last_order_id` after the relevant turns.

---

## Task 4 — Multi-turn validation

Run one ADK Web session with these turns in order:

| Turn | Input | Expected |
|------|-------|----------|
| 1 | `Hi, my name is Priya.` | Agent greets Priya; stores name |
| 2 | `Where is my order ORD-001?` | Tool called; uses Priya in reply |
| 3 | `What about ORD-002?` | Tool called again; still uses Priya |
| 4 | `Track order XYZ-100` | Graceful format error; no invented data |

**Checkpoint:** Agent never asks for Priya's name again after Turn 1.

---

## Task 5 — Document the checks

Create `tests/test_support_agent_manual.md` with columns: Input / Expected tool call / Expected reply behavior / Observed result / Pass or Fail.

Minimum scenarios:
- One valid order lookup.
- One not-found order.
- One invalid format.
- One multi-turn sequence.

---

## Verification checklist
- [ ] `get_order_status` exists in `src/tools/order_tools.py`.
- [ ] Tool is registered with the agent.
- [ ] Valid IDs return structured data.
- [ ] Not-found and invalid-format paths return graceful errors.
- [ ] `customer_name` stored in session state.
- [ ] `last_order_id` stored in session state.
- [ ] Multi-turn conversation preserves context.
- [ ] Manual test notes saved in `tests/test_support_agent_manual.md`.
