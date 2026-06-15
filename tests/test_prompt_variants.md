# Day 02 — Prompt Variant Manual Test Notes

Test the same prompts against v1 (friendly), v2 (formal), v3 (minimal).
Change `INSTRUCTION_VERSION` in `support_agent.py` to switch.

---

## Test 1 — Greeting

**Input:** `Hi there!`

| Version | Expected behavior | Observed | Pass? |
|---------|------------------|----------|-------|
| v1 | Warm, personal greeting | | |
| v2 | Professional acknowledgement | | |
| v3 | Short direct reply | | |

---

## Test 2 — Product query

**Input:** `What products do you sell?`

| Version | Expected behavior | Observed | Pass? |
|---------|------------------|----------|-------|
| v1 | Enthusiastic list with descriptions | | |
| v2 | Precise product catalogue | | |
| v3 | Bullet list, no extras | | |

---

## Test 3 — Order query without ID

**Input:** `Where is my order?`

| Version | Expected behavior | Observed | Pass? |
|---------|------------------|----------|-------|
| v1 | Warmly asks for ORD-XXX | | |
| v2 | Formally requests order ID | | |
| v3 | Asks for ID, nothing else | | |

---

## Test 4 — Out-of-scope query

**Input:** `Can you write me Python code?`

| Version | Expected behavior | Observed | Pass? |
|---------|------------------|----------|-------|
| v1 | Politely redirects with warmth | | |
| v2 | Firmly redirects, stays professional | | |
| v3 | Short redirect only | | |

---

## Test 5 — Unknown information (hallucination trap)

**Input:** `What are the exact ingredients of the Classic Formula?`

| Version | Expected behavior | Observed | Pass? |
|---------|------------------|----------|-------|
| v1 | Admits it doesn't know, stays honest | | |
| v2 | States information not available | | |
| v3 | Short honest reply | | |

---

## Test 6 — Multi-turn context

**Turn 1:** `Hi, my name is Arjun.`
**Turn 2:** `What's the cheapest product?`

| Version | Expected behavior | Observed | Pass? |
|---------|------------------|----------|-------|
| v1 | Uses name "Arjun" in reply | | |
| v2 | May or may not use name | | |
| v3 | Direct answer, no extras | | |

---

## Notes

- Best overall instruction for tone: ____
- Best for conciseness: ____
- Saved as current version: ____
