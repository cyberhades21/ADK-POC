# Day 01 + Day 02 Lab Guide
## eComBot v1 — Basic Support Agent

---

### Module alignment
These two sessions build **eComBot v1** — the Orchestrator agent's foundation. Intent classification and prompt design established here carry forward through the entire capstone.

---

## Part A — Day 01: Environment Setup and First Agent

### Starting state
- Python 3.11+ installed.
- VS Code available.
- OpenRouter API key ready.
- No existing eComBot code.

### Target state
- Working ADK project with a single support agent.
- Agent runs and responds in ADK Web.
- Three prompt behaviors tested.

### Repository structure

```text
ecombot/
├── src/
│   ├── agents/
│   │   └── support_agent.py
│   ├── config/
│   │   └── settings.py
│   └── __init__.py
├── .env
├── .env.example
├── requirements.txt
└── README.md
```

### Tasks

1. Create the repository structure above.
2. Add dependencies to `requirements.txt`:
   ```
   google-adk
   litellm
   python-dotenv
   ```
3. Create `.env` with your OpenRouter key:
   ```
   OPENROUTER_API_KEY=sk-or-...
   OPENROUTER_MODEL=openrouter/google/gemini-2.5-flash
   ```
4. Create `src/config/settings.py` to load env vars.
5. Implement `src/agents/support_agent.py` as an `LlmAgent` using `LiteLlm` pointed at OpenRouter.
6. Set the agent instruction to handle electronics e-commerce support: orders, products, returns.
7. Start ADK Web (`adk web`) and confirm the agent appears.

### Agent skeleton

```python
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
import os
from dotenv import load_dotenv
load_dotenv()

root_agent = LlmAgent(
    name="eComBot_Support",
    model=LiteLlm(
        model=os.getenv("OPENROUTER_MODEL"),
        api_key=os.getenv("OPENROUTER_API_KEY"),
        api_base="https://openrouter.ai/api/v1",
    ),
    instruction="""You are eComBot, a customer support agent for an electronics e-commerce store.
You sell phones, TV decoders, and accessories.
Help customers with order questions, product queries, and returns.
Do not guess order details you do not have. Ask for an order ID if needed.""",
    description="eComBot electronics support agent.",
)
```

### Checkpoints
- `adk web` starts without errors.
- Agent appears in ADK Web and responds.
- An order question gets a relevant (if placeholder) reply.
- An off-topic question is politely declined.

---

## Part B — Day 02: Prompt Refinement and Intent Testing

### Starting state
- Day 01 agent is working in ADK Web.

### Target state
- Agent instruction refined for consistent intent handling.
- Three instruction variants tested and compared.
- Manual test cases documented.

### Repository additions

```text
ecombot/
├── src/
│   └── agents/
│       ├── support_instructions_v1.txt
│       ├── support_instructions_v2.txt
│       └── support_instructions_v3.txt
└── tests/
    └── test_prompt_variants.md
```

### Tasks

1. Extract the instruction string into `support_instructions_v1.txt`.
2. Load instruction from file in `support_agent.py` using `Path(__file__).parent / f"support_instructions_{version}.txt"`.
3. Create `v2.txt` — more formal tone, stricter scope rules.
4. Create `v3.txt` — adds explicit handling for greetings, empathy, and closing.
5. Test each version with the same four prompts (see below).
6. Record results in `tests/test_prompt_variants.md`.

### Test prompts

| Prompt | What to check |
|--------|---------------|
| `Where is my order ORD-001?` | Asks for order ID or acknowledges it; does not invent status |
| `What phones do you have under ₹20,000?` | Stays in scope; does not hallucinate products |
| `Can you help me with my Python homework?` | Politely declines out-of-scope request |
| `Hi, my name is Priya. I need help.` | Friendly acknowledgement; asks how to help |

### Checkpoints
- Agent stays on electronics e-commerce domain across all versions.
- Out-of-scope queries are declined politely.
- Unknown data is not invented.
- Tone visibly differs between v1, v2, and v3.

### Review questions
- Which instruction version produced the most consistent behavior?
- Did the agent ever invent an order status?
- Did tone changes affect accuracy or scope adherence?
