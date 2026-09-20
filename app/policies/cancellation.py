def can_cancel(order: dict, confirmation: bool = False):
    status = order.get("status")
    amount = order.get("amount", 0)
    if status in ["SHIPPED", "DELIVERED", "CANCELLED"]:
        return {"allowed": False, "reason": f"Cannot cancel order with status {status} per cancellation-policy v3", "action": "CREATE_TICKET"}
    if status == "PROCESSING" and amount > 100 and not confirmation:
        return {"allowed": False, "reason": "Requires explicit confirmation for PROCESSING orders over $100", "action": "ASK_CONFIRMATION"}
    if status == "PENDING" and amount > 100 and not confirmation:
        return {"allowed": False, "reason": "Requires confirmation for orders over $100", "action": "ASK_CONFIRMATION"}
    return {"allowed": True, "reason": "Eligible per cancellation-policy v3"}

def can_update_address(order: dict):
    if order.get("status") == "SHIPPED":
        return {"allowed": False, "reason": "Cannot update address after shipment per cancellation-policy v3"}
    return {"allowed": True}
