# Day 04 Lab Guide
## eComBot v2 — SQLite Tools and Product Lookup

---

### Module alignment
This session replaces the mock order dictionary with a real SQLite database and adds the `cancel_order` and `lookup_product` tools. The SQLite-backed tool layer is the durable foundation that FastMCP servers will wrap in Module 5.

---

### Starting state
- eComBot v2 from Day 03 is working with `get_order_status` and in-memory session state.
- Mock order data lives in a Python dictionary.
- No product tool exists yet.

### Target state
- `get_order_status`, `cancel_order`, and `lookup_product` are all backed by SQLite.
- A seed script creates and populates the database.
- Session state callback still works with the real tool layer.
- Failure cases (invalid ID, cancelled order, missing product) return clean error dicts.

### Repository layout

```text
ecombot/
├── src/
│   ├── agents/
│   │   └── support_agent.py
│   ├── tools/
│   │   ├── order_tools.py
│   │   └── product_tools.py
│   ├── services/
│   │   └── db.py
│   └── config/
│       └── settings.py
├── scripts/
│   └── init_db.py
├── tests/
│   └── test_support_agent_manual.md
├── ecombot.db       ← created by init_db.py
├── .env
└── requirements.txt
```

---

## Task 1 — Database connection layer

Create `src/services/db.py`:

```python
import sqlite3
import os
from dotenv import load_dotenv
load_dotenv()

DB_PATH = os.getenv("DB_PATH", "ecombot.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
```

Add `DB_PATH=ecombot.db` to `.env.example`.

**Checkpoint:** `from src.services.db import get_conn` imports cleanly.

---

## Task 2 — Seed the database

Create `scripts/init_db.py` that creates `orders` and `products` tables and inserts sample data.

**Orders table columns:** `order_id`, `customer_name`, `status`, `eta`, `carrier`, `can_cancel`

**Products table columns:** `id`, `name`, `price`, `stock`, `description`

Sample orders:

| order_id | customer_name | status | eta | carrier | can_cancel |
|----------|--------------|--------|-----|---------|------------|
| ORD-001 | Priya Sharma | Shipped | 5 Jun 2026 | BlueDart | 0 |
| ORD-002 | Arjun Mehta | Processing | 7 Jun 2026 | DTDC | 1 |
| ORD-003 | Sunita Rao | Delivered | Already delivered | FedEx | 0 |
| ORD-004 | Rahul Das | Cancelled | — | — | 0 |
| ORD-005 | Meera Nair | Processing | 10 Jun 2026 | BlueDart | 1 |

Sample products (electronics):

| name | price | stock | description |
|------|-------|-------|-------------|
| Samsung Galaxy A55 | 32999 | 15 | Mid-range Android, 6.6" AMOLED |
| Redmi Note 13 | 17999 | 28 | Budget Android, 6.67" AMOLED |
| Samsung 43" 4K TV | 42999 | 7 | 4K UHD Smart TV |
| DStv Decoder HD | 3499 | 40 | HD satellite decoder |
| USB-C Charging Cable | 499 | 120 | 2m braided cable |

Run `python scripts/init_db.py` to create `ecombot.db`.

**Checkpoint:** Running the script creates the file and tables. Query returns 5 orders.

---

## Task 3 — Update order tools

Rewrite `src/tools/order_tools.py` to query SQLite instead of the mock dict:

```python
from src.services.db import get_conn

def get_order_status(order_id: str) -> dict:
    """Look up the current status of an order by its ID (format: ORD-XXX)."""
    order_id = order_id.strip().upper()
    if not order_id.startswith("ORD-"):
        return {"error": "Invalid format. Use ORD-XXX (e.g. ORD-001)."}
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM orders WHERE order_id = ?", (order_id,)
        ).fetchone()
    if not row:
        return {"error": f"Order {order_id} not found. Please check the ID."}
    return dict(row)

def cancel_order(order_id: str) -> dict:
    """Cancel an order. Only possible if the order has not yet shipped."""
    order_id = order_id.strip().upper()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM orders WHERE order_id = ?", (order_id,)
        ).fetchone()
        if not row:
            return {"error": f"Order {order_id} not found."}
        if not row["can_cancel"]:
            return {"error": f"Order {order_id} cannot be cancelled (status: {row['status']})."}
        conn.execute(
            "UPDATE orders SET status = 'Cancelled', can_cancel = 0 WHERE order_id = ?",
            (order_id,)
        )
    return {"success": True, "order_id": order_id, "message": "Order successfully cancelled."}
```

**Checkpoint:** `get_order_status("ORD-001")` returns the row from SQLite. `cancel_order("ORD-002")` sets status to Cancelled.

---

## Task 4 — Add product tool

Create `src/tools/product_tools.py`:

```python
from src.services.db import get_conn

def lookup_product(product_name: str) -> dict:
    """Search for a product by name. Returns price, stock, and description."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM products WHERE name LIKE ?",
            (f"%{product_name}%",)
        ).fetchall()
    if not rows:
        return {"error": f"No product found matching '{product_name}'."}
    return {"results": [dict(r) for r in rows]}
```

**Checkpoint:** `lookup_product("Samsung")` returns both the Galaxy A55 and the Samsung TV.

---

## Task 5 — Register all three tools

Update `support_agent.py` to import and register `get_order_status`, `cancel_order`, and `lookup_product`.

Update the instruction to cover when to use each tool:
```text
- Use get_order_status when the customer asks about order status or tracking.
- Use cancel_order when the customer asks to cancel an order.
- Use lookup_product when the customer asks about product details, price, or availability.
- Always ask for missing order IDs or product names before calling a tool.
- Never invent order or product details.
```

**Checkpoint:** ADK Web lists all three tools as available.

---

## Task 6 — Validate the full flow

Run one ADK Web session:

| Turn | Input | Expected |
|------|-------|----------|
| 1 | `Hi, I'm Priya.` | Name stored |
| 2 | `Where is my order ORD-001?` | Tool returns Shipped / BlueDart |
| 3 | `Can you cancel it?` | Tool returns "cannot be cancelled — already shipped" |
| 4 | `Cancel ORD-002 instead.` | Tool cancels; confirms success |
| 5 | `Do you have the Redmi Note 13?` | Product lookup returns price and stock |
| 6 | `What about ORD-FAKE99?` | Graceful not-found error |

**Checkpoint:** All six turns behave as expected with no invented data.

---

## Task 7 — Failure case tests

Test these edge cases and confirm each returns a clean error message:
- Invalid format: `ORD-XYZ`
- Already cancelled: `ORD-004`
- Missing product name: `lookup_product("")`
- Unknown product: `lookup_product("Flying Car")`

---

## Verification checklist
- [ ] `scripts/init_db.py` creates and seeds `ecombot.db`.
- [ ] `src/services/db.py` provides reusable SQLite access.
- [ ] `get_order_status` queries SQLite and handles not-found.
- [ ] `cancel_order` validates cancellability before updating.
- [ ] `lookup_product` searches by name and handles no-match.
- [ ] All three tools registered in the agent.
- [ ] Session callback still extracts name and order ID correctly.
- [ ] Failure cases return safe error messages.
