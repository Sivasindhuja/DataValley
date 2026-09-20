from app.policies.cancellation import can_cancel, can_update_address
from app.policies.refunds import can_refund
from app.policies.authorization import is_authorized
from app.tools.customer import get_customer
from app.tools.orders import get_order

RISK = {
    "get_order": "low",
    "get_order_status": "low",
    "get_customer": "low",
    "get_customer_orders": "low",
    "get_customer_tickets": "low",
    "verify_customer": "low",
    "search_policy": "low",
    "hybrid_retrieve": "low",
    "get_product": "low",
    "get_product_status": "low",
    "get_warranty": "low",
    "get_refund_status": "low",
    "check_refund_eligibility": "low",
    "create_support_ticket": "medium",
    "update_support_ticket": "medium",
    "send_email": "medium",
    "send_notification": "medium",
    "update_account": "medium",
    "cancel_order": "high",
    "create_refund_request": "high",
    "update_delivery_address": "high",
    "change_account_information": "high",
}

def check_action(tool: str, args: dict, customer_id: str = None):
    risk = RISK.get(tool, "medium")
    if risk == "low":
        return {"allow": True, "risk": risk}
    if tool in ["cancel_order","create_refund_request","update_delivery_address","update_account","change_account_information"]:
        order = None
        if args.get("order_id"):
            order = get_order(args.get("order_id"))
            if "error" in order: return {"allow": False, "reason": "Order not found"}
        cust = get_customer(customer_id) if customer_id else None
        if cust and order:
            auth = is_authorized(cust, order)
            if not auth["authorized"]: return {"allow": False, "reason": auth["reason"], "escalate": True}
        if cust and cust.get("status")=="LOCKED":
            return {"allow": False, "reason": "Account locked per account-policy v3", "escalate": True}
        if tool=="cancel_order":
            pol=can_cancel(order, confirmation=args.get("confirmation", False))
            if not pol["allowed"]:
                if pol.get("action")=="ASK_CONFIRMATION": return {"allow": False, "reason": pol["reason"], "need_confirmation": True, "risk": risk}
                if pol.get("action")=="CREATE_TICKET": return {"allow": False, "reason": pol["reason"], "suggest_ticket": True, "risk": risk}
                return {"allow": False, "reason": pol["reason"], "risk": risk}
        if tool=="create_refund_request":
            pol=can_refund(order)
            if not pol["allowed"]: return {"allow": False, "reason": pol["reason"], "risk": risk}
            # fraud/dispute -> escalate not auto refund
            if any(k in args.get("reason","").lower() for k in ["fraud","dispute"]):
                return {"allow": False, "reason": "Disputed refunds must be escalated per refund-policy v4", "escalate": True}
        if tool=="update_delivery_address":
            pol=can_update_address(order)
            if not pol["allowed"]: return {"allow": False, "reason": pol["reason"], "suggest_ticket": True, "risk": risk}
        if tool in ["update_account","change_account_information"]:
            if not args.get("verify"):
                return {"allow": False, "reason": "Requires verification via verify_customer per account-policy v3", "need_verification": True}
        return {"allow": True, "risk": risk}
    # medium risk default allow but require auth
    if tool in ["create_support_ticket","send_email","send_notification"]:
        return {"allow": True, "risk": risk}
    return {"allow": True, "risk": risk}
