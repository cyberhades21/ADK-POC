# Day 08 Lab Guide
## eComBot v5 — FastMCP External Integrations

---

### Module alignment
This session wraps the existing SQLite-backed tools behind two FastMCP servers: an **Orders server** and an **Inventory server**. This is the external tool layer that the Support Agent uses in the final system. The mock servers here have the same interface as a real order management system would.

---

### Starting state
- eComBot v4 is working with tools, RAG, session state, and model routing.
- `get_order_status`, `cancel_order`, and `lookup_product` are implemented as direct Python functions.
- No MCP server layer exists yet.

### Target state
- `src/services/orders_server.py` exposes `order_status`, `order_cancel`, and `get_invoice` via FastMCP.
- `src/services/inventory_server.py` exposes `check_stock` via FastMCP.
- Both servers start independently and are reachable via MCP client.
- All tools handle timeouts, 404s, and invalid IDs gracefully.

### New dependency

```
fastmcp
```

Add to `requirements.txt` and install.

---

## Task 1 — Build the Orders MCP server

Create `src/services/orders_server.py`:

```python
"""
FastMCP Orders Server
Run: python -m src.services.orders_server
Exposes order_status, order_cancel, get_invoice as MCP tools.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastmcp import FastMCP
from src.tools.order_tools import get_order_status, cancel_order

mcp = FastMCP("eComBot Orders")

@mcp.tool()
def order_status(order_id: str) -> dict:
    """Get the current status of an order by ID (format: ORD-XXX)."""
    return get_order_status(order_id)

@mcp.tool()
def order_cancel(order_id: str) -> dict:
    """Cancel an order if it has not yet shipped."""
    return cancel_order(order_id)

@mcp.tool()
def get_invoice(order_id: str) -> dict:
    """Return a simple invoice summary for an order."""
    result = get_order_status(order_id)
    if "error" in result:
        return result
    return {
        "invoice_for": order_id,
        "customer":    result.get("customer_name", "Unknown"),
        "status":      result.get("status"),
        "carrier":     result.get("carrier"),
        "note":        "Full invoice sent to registered email within 24 hours.",
    }

if __name__ == "__main__":
    print("Orders MCP server starting...")
    mcp.run()
```

**Checkpoint:** `python -m src.services.orders_server` starts without errors.

---

## Task 2 — Build the Inventory MCP server

Create `src/services/inventory_server.py`:

```python
"""
FastMCP Inventory Server
Run: python -m src.services.inventory_server
Exposes check_stock as an MCP tool.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastmcp import FastMCP
from src.tools.product_tools import lookup_product

mcp = FastMCP("eComBot Inventory")

@mcp.tool()
def check_stock(product_name: str) -> dict:
    """Check current stock level for a product by name."""
    result = lookup_product(product_name)
    if "error" in result:
        return result
    return {
        "matches": [
            {"name": r["name"], "stock": r["stock"], "price": r["price"]}
            for r in result["results"]
        ]
    }

if __name__ == "__main__":
    print("Inventory MCP server starting...")
    mcp.run()
```

**Checkpoint:** `python -m src.services.inventory_server` starts without errors.

---

## Task 3 — Test the servers manually

Create `scripts/test_mcp.py` to call both servers as an MCP client:

```python
"""Quick smoke test for both MCP servers — run each server first."""
import asyncio
from fastmcp import FastMCP

async def test_orders():
    # Call order_status via MCP client
    # (FastMCP in-process testing — no separate process needed for smoke test)
    from src.services.orders_server import mcp as orders_mcp
    result = await orders_mcp.run_tool("order_status", {"order_id": "ORD-001"})
    print("order_status ORD-001:", result)

    result = await orders_mcp.run_tool("order_status", {"order_id": "ORD-999"})
    print("order_status ORD-999 (not found):", result)

    result = await orders_mcp.run_tool("order_cancel", {"order_id": "ORD-002"})
    print("order_cancel ORD-002:", result)

    result = await orders_mcp.run_tool("get_invoice", {"order_id": "ORD-001"})
    print("get_invoice ORD-001:", result)

async def test_inventory():
    from src.services.inventory_server import mcp as inv_mcp
    result = await inv_mcp.run_tool("check_stock", {"product_name": "Samsung"})
    print("check_stock Samsung:", result)

    result = await inv_mcp.run_tool("check_stock", {"product_name": "Flying Car"})
    print("check_stock unknown:", result)

asyncio.run(test_orders())
asyncio.run(test_inventory())
```

**Checkpoint:** All six calls return expected data. Not-found and unknown cases return error dicts, not exceptions.

---

## Task 4 — Error scenario validation

Test these error cases explicitly:

| Scenario | Input | Expected response |
|----------|-------|------------------|
| Invalid order ID format | `order_status("XYZ-001")` | `{"error": "Invalid format..."}` |
| Order not found | `order_status("ORD-999")` | `{"error": "Order ORD-999 not found..."}` |
| Cancel shipped order | `order_cancel("ORD-001")` | `{"error": "...cannot be cancelled (status: Shipped)"}` |
| Cancel already-cancelled | `order_cancel("ORD-004")` | `{"error": "...cannot be cancelled (status: Cancelled)"}` |
| Unknown product | `check_stock("Flying Car X200")` | `{"error": "No product found..."}` |
| Empty product name | `check_stock("")` | Error or empty result — no exception |

**Checkpoint:** All error cases return structured dicts. No raw exceptions reach the caller.

---

## Task 5 — Connect MCP tools to the agent

The agent continues to call the underlying Python functions directly (FastMCP in-process). The MCP servers are the external interface that a real backend would call. Wire the agent to use the same functions:

1. Keep `get_order_status`, `cancel_order`, `lookup_product` registered directly on the agent (in-process for ADK Web testing).
2. The FastMCP servers wrap the same functions for any external MCP client.
3. This means both paths (agent direct call and MCP client) test the same logic.

Confirm in ADK Web that:
- `"Where is my order ORD-001?"` still triggers `get_order_status` tool.
- `"Cancel my order ORD-002."` still triggers `cancel_order` tool.
- `"Do you have the Redmi Note 13 in stock?"` triggers `lookup_product`.

**Checkpoint:** Tool calls work identically through ADK Web and through the MCP test script.

---

## Task 6 — Document the integration

Add a note to `README.md` (or create one) documenting how to start both MCP servers:

```bash
# Terminal 1 — Orders server
python -m src.services.orders_server

# Terminal 2 — Inventory server
python -m src.services.inventory_server

# Terminal 3 — ADK Web
adk web
```

---

## Verification checklist
- [ ] `src/services/orders_server.py` exposes `order_status`, `order_cancel`, `get_invoice`.
- [ ] `src/services/inventory_server.py` exposes `check_stock`.
- [ ] Both servers start independently without errors.
- [ ] All tools return structured dicts for valid inputs.
- [ ] Invalid format, not-found, and cancellation-blocked cases return error dicts.
- [ ] `scripts/test_mcp.py` validates all six scenarios.
- [ ] Agent in ADK Web still calls tools correctly.
- [ ] Server startup documented in README.
