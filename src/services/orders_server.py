"""
FastMCP Orders Server — run separately: python -m src.services.orders_server
Exposes get_order_status, cancel_order, get_invoice as MCP tools.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

try:
    from fastmcp import FastMCP
except ImportError:
    print("Run: pip install fastmcp")
    sys.exit(1)

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
