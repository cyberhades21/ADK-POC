"""
FastMCP Inventory Server — run separately: python -m src.services.inventory_server
Exposes check_stock as an MCP tool.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

try:
    from fastmcp import FastMCP
except ImportError:
    print("Run: pip install fastmcp")
    sys.exit(1)

from src.tools.product_tools import lookup_product
from src.services.db import get_conn

mcp = FastMCP("eComBot Inventory")


@mcp.tool()
def check_stock(product_name: str) -> dict:
    """Check current stock level for a product by name."""
    result = lookup_product(product_name)
    if "error" in result:
        return result
    items = result["results"]
    return {
        "matches": [
            {"name": r["name"], "stock": r["stock"], "price": r["price"]}
            for r in items
        ]
    }


if __name__ == "__main__":
    print("Inventory MCP server starting...")
    mcp.run()
