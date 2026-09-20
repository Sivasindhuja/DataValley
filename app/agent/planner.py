def plan(intent: str, has_order_id: bool):
    if "cancel" in intent.lower():
        return ["identify order", "get_order", "check cancellation policy", "policy engine", "ask confirmation if needed", "cancel_order or create ticket"]
    if "refund" in intent.lower():
        return ["identify order/refund", "get_refund_status or check eligibility", "retrieve refund policy", "explain"]
    if "order" in intent.lower() or "ship" in intent.lower() or "delivery" in intent.lower():
        return ["identify order", "get_order_status", "retrieve shipping policy", "explain"]
    if "product" in intent.lower() or "warranty" in intent.lower():
        return ["search product docs", "retrieve warranty policy", "explain"]
    return ["understand request", "retrieve relevant knowledge", "select tools", "respond"]
