from app.policies.cancellation import can_cancel, can_update_address
from app.policies.refunds import can_refund
from app.policies.authorization import is_authorized
from app.tools.db import get_session
from app.tools.customer import get_customer
from app.tools.orders import get_order

# Risk levels
RISK = {
    "get_order": "low",
    "get_order_status": "low",
    "get_customer": "low",
    "search_policy": "low",
    "get_product": "low",
    "create_support_ticket": "medium",
    "send_email": "medium",
    "cancel_order": "high",
    "create_refund_request": "high",
    "update_delivery_address": "high",
}

def check_action(tool: str, args: dict, customer_id: str = None):
    risk = RISK.get(tool, "medium")
    if risk == "low":
        return {"allow": True, "risk": risk}
    # For high-risk, enforce policy engine
    if tool == "cancel_order":
        order = get_order(args.get("order_id"))
        if "error" in order: return {"allow": False, "reason": "Order not found"}
        cust = get_customer(customer_id) if customer_id else None
        auth = is_authorized(cust, order) if cust else {"authorized": True}
        if not auth["authorized"]: return {"allow": False, "reason": auth["reason"], "escalate": True}
        pol = can_cancel(order, confirmation=args.get("confirmation", False))
        if not pol["allowed"]:
            if pol.get("action") == "ASK_CONFIRMATION": return {"allow": False, "reason": pol["reason"], "need_confirmation": True}
            if pol.get("action") == "CREATE_TICKET": return {"allow": False, "reason": pol["reason"], "suggest_ticket": True}
            return {"allow": False, "reason": pol["reason"]}
        return {"allow": True, "risk": risk}
    if tool == "create_refund_request":
        order = get_order(args.get("order_id"))
        if "error" in order: return {"allow": False, "reason": "Order not found"}
        pol = can_refund(order)
        if not pol["allowed"]: return {"allow": False, "reason": pol["reason"]}
        return {"allow": True, "risk": risk}
    if tool == "update_delivery_address":
        order = get_order(args.get("order_id"))
        if "error" in order: return {"allow": False, "reason": "Order not found"}
        pol = can_update_address(order)
        if not pol["allowed"]: return {"allow": False, "reason": pol["reason"], "suggest_ticket": True}
        return {"allow": True, "risk": risk}
    # medium risk default allow but log
    return {"allow": True, "risk": risk}

