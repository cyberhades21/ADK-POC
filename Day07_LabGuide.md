# Day 07 Lab Guide
## eComBot v4 — LiteLLM Model Routing and Fallback

---

### Module alignment
This session adds cost-aware model routing. Simple FAQ queries go to a cheaper model; complex flows (complaints, comparisons, cancellations) go to a more capable model. If the primary model fails, the system falls back automatically. The model badge in the final UI and cost tracking in LangSmith both depend on what is built here.

---

### Starting state
- eComBot v3 is working with tools, session state, and RAG.
- All LLM calls use a single OpenRouter model hard-coded in `.env`.
- No routing or fallback logic exists yet.

### Target state
- `src/services/llm_router.py` classifies query complexity and selects a model.
- Simple queries route to a fast/cheap model (e.g. `gemini-2.5-flash`).
- Complex queries route to a more capable model (e.g. `gemini-2.5-pro` or `gpt-4o-mini`).
- A fallback model is tried if the primary call fails.
- Routing decisions are logged for later cost analysis.

### New `.env` keys

```
FAST_MODEL=openrouter/google/gemini-2.5-flash
DEEP_MODEL=openrouter/openai/gpt-4o-mini
FALLBACK_MODEL=openrouter/google/gemini-2.5-flash
```

---

## Task 1 — Build the router module

Create `src/services/llm_router.py`:

```python
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

FAST_MODEL     = os.getenv("FAST_MODEL",     "openrouter/google/gemini-2.5-flash")
DEEP_MODEL     = os.getenv("DEEP_MODEL",     "openrouter/openai/gpt-4o-mini")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "openrouter/google/gemini-2.5-flash")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOG_DIR / "routing.log"),
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)

COMPLEX_KEYWORDS = {
    "compare", "recommend", "complaint", "refund",
    "cancel", "broken", "damage", "vs", "better",
    "worse", "difference", "which", "should i"
}

def classify(message: str) -> str:
    words = set(message.lower().split())
    return "deep" if words & COMPLEX_KEYWORDS else "fast"

def route(user_message: str) -> str:
    """Return the model name to use for this message."""
    complexity = classify(user_message)
    model = DEEP_MODEL if complexity == "deep" else FAST_MODEL
    logging.info(f"complexity={complexity} model={model} query={user_message[:60]}")
    return model
```

**Checkpoint:** `route("Compare Samsung A55 vs Redmi Note 13")` returns `DEEP_MODEL`. `route("Where is my order?")` returns `FAST_MODEL`.

---

## Task 2 — Use the router in the agent

Update `src/agent.py` (the main `root_agent` entrypoint) to select the model dynamically. Since ADK's `LlmAgent` takes a model at init time, apply routing in the `before_model_callback`:

```python
from src.services.llm_router import route, OPENROUTER_KEY
from google.adk.models.lite_llm import LiteLlm

def apply_model_routing(callback_context, llm_request):
    # Extract last user message
    last_user_text = ""
    for content in reversed(llm_request.contents or []):
        if hasattr(content, "role") and content.role == "user":
            if content.parts:
                last_user_text = content.parts[0].text or ""
            break

    selected_model = route(last_user_text)
    # Store selected model in state for UI badge later
    callback_context.state["last_model_used"] = selected_model

    # Override the model on the request
    llm_request.model = selected_model
```

Chain this with the existing session callback using a combined `before_model_callback`.

**Checkpoint:** After asking "Compare Samsung A55 vs Redmi Note 13", `callback_context.state["last_model_used"]` shows the deep model name.

---

## Task 3 — Add fallback on model failure

Wrap the LiteLLM call with a fallback. The cleanest approach is to catch errors at the `before_model_callback` level and switch models:

```python
import litellm

def call_with_fallback(messages: list, user_message: str) -> str:
    """Direct LiteLLM call with fallback — use for standalone testing."""
    from src.services.llm_router import route, FALLBACK_MODEL, OPENROUTER_KEY
    primary = route(user_message)
    try:
        resp = litellm.completion(
            model=primary,
            messages=messages,
            api_key=OPENROUTER_KEY,
            api_base="https://openrouter.ai/api/v1",
        )
        return resp.choices[0].message.content
    except Exception as e:
        logging.warning(f"Primary model {primary} failed ({e}), falling back to {FALLBACK_MODEL}")
        resp = litellm.completion(
            model=FALLBACK_MODEL,
            messages=messages,
            api_key=OPENROUTER_KEY,
            api_base="https://openrouter.ai/api/v1",
        )
        return resp.choices[0].message.content
```

For ADK agent flows, configure LiteLLM's `fallbacks` parameter when constructing `LiteLlm`:

```python
LiteLlm(
    model=FAST_MODEL,
    api_key=OPENROUTER_KEY,
    api_base="https://openrouter.ai/api/v1",
    fallbacks=[FALLBACK_MODEL],
)
```

**Checkpoint:** Temporarily set `FAST_MODEL=openrouter/this-model-does-not-exist` and confirm the fallback fires.

---

## Task 4 — Validate routing behavior

Run these queries in ADK Web and check `logs/routing.log`:

| Query | Expected route | Check in log |
|-------|---------------|--------------|
| `Where is my order ORD-001?` | fast | `complexity=fast` |
| `What products do you have?` | fast | `complexity=fast` |
| `Compare Samsung A55 vs Redmi Note 13` | deep | `complexity=deep` |
| `I want to cancel my order` | deep | `complexity=deep` |
| `Which phone should I buy?` | deep | `complexity=deep` |
| `What is the return policy?` | fast | `complexity=fast` |

**Checkpoint:** At least 5 of 6 queries route to the correct model. Log file shows each decision.

---

## Task 5 — Verify consistency across models

Ask the same question twice — once routed to the fast model, once to the deep model — and compare:

1. `"What is the warranty on the Samsung TV?"` → fast model → check answer matches FAQ.
2. Temporarily set `FAST_MODEL` to the deep model → re-ask → compare answers.

Both answers should be grounded and accurate. The deep model may give more detail, but neither should hallucinate.

**Checkpoint:** Both routing paths return grounded, consistent answers.

---

## Verification checklist
- [ ] `src/services/llm_router.py` classifies queries as fast or deep.
- [ ] `FAST_MODEL`, `DEEP_MODEL`, and `FALLBACK_MODEL` read from `.env`.
- [ ] Routing decisions written to `logs/routing.log`.
- [ ] Complex queries (compare, cancel, recommend) route to deep model.
- [ ] Simple queries (status, list, policy) route to fast model.
- [ ] Fallback fires when primary model is unavailable.
- [ ] Existing tools and RAG still work with routing active.
- [ ] `last_model_used` stored in session state for later UI display.
