# Day 09 Lab Guide
## eComBot v6 — Multi-Agent Orchestration

---

### Module alignment
This session splits eComBot into three agents: an **Orchestrator** that classifies intent and delegates, a **Support Agent** for orders and returns, and a **Sales Agent** for product discovery and recommendations. This is the core architectural pattern of the final system — everything from Day 10 onward builds on top of it.

---

### Starting state
- eComBot v5 is a single agent with all tools, RAG, session state, and model routing.
- One agent handles both support and sales queries.

### Target state
- `src/agents/orchestrator.py` — classifies intent and delegates to sub-agents.
- `src/agents/support_agent.py` — handles orders, cancellations, and return queries using tools.
- `src/agents/sales_agent.py` — handles product discovery, comparisons, and recommendations using RAG.
- Routing is traceable: ADK Web shows which agent handled each turn.

### Repository additions

```text
ecombot/
└── src/
    └── agents/
        ├── orchestrator.py     ← new
        ├── support_agent.py    ← refactored
        └── sales_agent.py      ← new
```

Update `src/agent.py` so `root_agent` points to the Orchestrator.

---

## Task 1 — Build the Support Agent

Refactor the existing agent into a focused Support Agent. It keeps all tools and the session callback; it loses general product-discovery responsibility.

`src/agents/support_agent.py`:

```python
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from src.tools.order_tools import get_order_status, cancel_order
from src.tools.product_tools import lookup_product
import os
from dotenv import load_dotenv
load_dotenv()

support_agent = LlmAgent(
    name="Support_Agent",
    model=LiteLlm(
        model=os.getenv("FAST_MODEL", "openrouter/google/gemini-2.5-flash"),
        api_key=os.getenv("OPENROUTER_API_KEY"),
        api_base="https://openrouter.ai/api/v1",
    ),
    instruction="""You are the eComBot Support Agent for an electronics e-commerce store.
Handle: order status, order cancellations, return requests, and product availability.
- Use get_order_status when asked about order status or tracking.
- Use cancel_order when asked to cancel an order.
- Use lookup_product when asked about product availability or price.
- Ask for missing order IDs before calling a tool.
- Never invent order details.
- Do not handle product comparisons or purchase recommendations — those go to Sales.""",
    description="Handles order management, cancellations, and returns.",
    tools=[get_order_status, cancel_order, lookup_product],
)
```

**Checkpoint:** Support Agent answers "Where is my order ORD-001?" correctly in isolation.

---

## Task 2 — Build the Sales Agent

Create `src/agents/sales_agent.py`. This agent uses RAG to answer product questions and make recommendations.

```python
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from src.rag.retriever import retrieve
import os
from dotenv import load_dotenv
load_dotenv()

SALES_INSTRUCTION = """You are the eComBot Sales Agent for an electronics e-commerce store.
Handle: product discovery, comparisons, recommendations, and upsells.
- Answer from the product knowledge base. Do not invent specs or prices.
- When comparing products, list key differences clearly.
- When recommending, ask about the customer's budget and use case first.
- Do not handle order status or cancellations — those go to Support."""

sales_agent = LlmAgent(
    name="Sales_Agent",
    model=LiteLlm(
        model=os.getenv("DEEP_MODEL", "openrouter/openai/gpt-4o-mini"),
        api_key=os.getenv("OPENROUTER_API_KEY"),
        api_base="https://openrouter.ai/api/v1",
    ),
    instruction=SALES_INSTRUCTION,
    description="Handles product discovery, comparisons, and purchase recommendations.",
)
```

**Checkpoint:** Sales Agent answers "Compare Samsung A55 vs Redmi Note 13" with a structured comparison.

---

## Task 3 — Build the Orchestrator

Create `src/agents/orchestrator.py`. The Orchestrator classifies intent and delegates to the correct sub-agent using ADK's sub-agent routing.

```python
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from src.agents.support_agent import support_agent
from src.agents.sales_agent import sales_agent
import os
from dotenv import load_dotenv
load_dotenv()

ORCHESTRATOR_INSTRUCTION = """You are the eComBot Orchestrator for an electronics e-commerce store.
Your only job is to classify the customer's intent and delegate to the right agent.

Delegate to Support_Agent for:
- Order status or tracking ("Where is my order?")
- Order cancellation ("Cancel my order")
- Return requests ("I want to return this")
- Product availability or stock check

Delegate to Sales_Agent for:
- Product discovery ("What phones do you have?")
- Product comparisons ("Compare A vs B")
- Purchase recommendations ("Which phone should I buy?")
- Upsell or accessory suggestions

For greetings or unclear intent, ask a clarifying question before delegating.
Never answer order or product questions yourself — always delegate."""

orchestrator = LlmAgent(
    name="Orchestrator",
    model=LiteLlm(
        model=os.getenv("FAST_MODEL", "openrouter/google/gemini-2.5-flash"),
        api_key=os.getenv("OPENROUTER_API_KEY"),
        api_base="https://openrouter.ai/api/v1",
    ),
    instruction=ORCHESTRATOR_INSTRUCTION,
    description="Routes customer queries to Support or Sales agent.",
    sub_agents=[support_agent, sales_agent],
)
```

Update `src/agent.py`:

```python
from src.agents.orchestrator import orchestrator
root_agent = orchestrator
```

**Checkpoint:** ADK Web shows the Orchestrator as `root_agent` with two sub-agents listed.

---

## Task 4 — Validate routing

Run one ADK Web session and confirm each query reaches the correct agent:

| Query | Expected agent | Check |
|-------|---------------|-------|
| `Where is my order ORD-001?` | Support_Agent | Tool called; order returned |
| `Cancel my order ORD-002.` | Support_Agent | Tool called; cancellation confirmed |
| `What phones do you have under ₹20,000?` | Sales_Agent | RAG; Redmi Note 13 mentioned |
| `Compare Samsung A55 vs Redmi Note 13` | Sales_Agent | Structured comparison returned |
| `What is the return policy?` | Sales_Agent or Support_Agent | Grounded FAQ answer |
| `Hi, I need help.` | Orchestrator | Asks clarifying question |

ADK Web's trace panel should show the agent name for each response.

**Checkpoint:** "Where is my order?" always goes to Support. "Compare" always goes to Sales.

---

## Task 5 — Session state across agents

The session callback from Day 03 should still work at the Orchestrator level. Confirm:

1. Introduce yourself: `"Hi, I'm Priya."` → Orchestrator stores `customer_name`.
2. Ask for order status → Support Agent receives the enriched prompt with Priya's name.
3. Ask for a recommendation → Sales Agent also has access to `customer_name` in session state.

**Checkpoint:** The sub-agents use the customer name without the customer repeating it.

---

## Task 6 — Trace the delegation

ADK Web provides a trace view showing the full agent call chain. For each of the validation queries above:
- Note which agent handled the response.
- Note any tool calls made by the sub-agent.
- Note the model used (from `last_model_used` in session state).

Write the routing results to `tests/test_routing.md` with columns: Query / Agent delegated to / Tool called / Correct routing (Y/N).

---

## Verification checklist
- [ ] `src/agents/orchestrator.py` exists with both sub-agents registered.
- [ ] `src/agents/support_agent.py` handles order and cancellation tools.
- [ ] `src/agents/sales_agent.py` handles product discovery via RAG.
- [ ] `root_agent` in `src/agent.py` points to the Orchestrator.
- [ ] "Where is my order?" routes to Support_Agent.
- [ ] "What phone should I buy?" routes to Sales_Agent.
- [ ] Session state (customer name, last order ID) visible across agent turns.
- [ ] Routing results documented in `tests/test_routing.md`.
