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
