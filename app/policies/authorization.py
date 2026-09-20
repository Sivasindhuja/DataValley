def is_authorized(customer: dict, order: dict):
    if not customer or "error" in customer:
        return {"authorized": False, "reason": "Customer not found"}
    if customer.get("status") == "LOCKED":
        return {"authorized": False, "reason": "Account locked per account-policy v3"}
    if order and order.get("customer_id") != customer.get("id"):
        return {"authorized": False, "reason": "Order does not belong to customer"}
    return {"authorized": True}
