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
