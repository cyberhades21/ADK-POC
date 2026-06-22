"""Verify MCP servers respond before starting eComBot: python -m scripts.test_mcp"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.tools.order_tools import get_order_status, cancel_order
from src.tools.product_tools import lookup_product

print("=== Order Tools ===")
print(get_order_status("ORD-001"))
print(get_order_status("ORD-999"))
print(get_order_status("BAD-ID"))
print(cancel_order("ORD-002"))
print(cancel_order("ORD-003"))

print("\n=== Product Tools ===")
print(lookup_product("Classic"))
print(lookup_product("Nonexistent"))
