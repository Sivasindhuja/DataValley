def can_refund(order: dict):
    if order.get("status") != "DELIVERED":
        return {"allowed": False, "reason": f"Order status {order.get('status')} not eligible; must be DELIVERED per refund-policy v4"}
    return {"allowed": True}

def requires_escalation(reason: str):
    keywords = ["dispute", "fraud", "chargeback"]
    return any(k in reason.lower() for k in keywords)
