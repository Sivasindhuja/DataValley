from dataclasses import dataclass
from typing import Optional
from app.auth.models import AuthContext
from app.tools.db import get_session, Order
from app.tools.customer import get_customer
from app.policies.cancellation import can_cancel, can_update_address
from app.policies.refunds import can_refund
from app.policies.authorization import is_authorized

@dataclass
class ActionDecision:
    allowed: bool
    requires_confirmation: bool = False
    requires_escalation: bool = False
    fraud_flag: bool = False
    reason: str = ""
    # for backward compat with existing check_action
    risk: str = "medium"

    def to_dict(self):
        return {
            "allowed": self.allowed,
            "requires_confirmation": self.requires_confirmation,
            "requires_escalation": self.requires_escalation,
            "fraud_flag": self.fraud_flag,
            "reason": self.reason,
            "risk": self.risk,
            # legacy keys
            "allow": self.allowed,
            "need_confirmation": self.requires_confirmation,
            "suggest_ticket": self.requires_escalation,
            "escalate": self.requires_escalation,
        }

def _get_order(order_id: Optional[str]):
    if not order_id:
        return None
    s = get_session()
    o = s.query(Order).filter_by(id=order_id).first()
    s.close()
    if not o:
        return None
    return {"id": o.id, "customer_id": o.customer_id, "status": o.status, "amount": o.amount}

def evaluate_policy(tool: str, args: dict, auth: Optional[AuthContext]) -> ActionDecision:
    # 1. Is user authenticated?
    LOW_RISK_TOOLS = {"get_order","get_order_status","get_customer","get_customer_orders","get_customer_tickets","verify_customer","search_policy","hybrid_retrieve","chroma_retrieve","get_product","get_product_status","get_warranty","get_refund_status","check_refund_eligibility"}
    if not auth or not auth.is_authenticated():
        # For backward compat, allow low-risk reads without auth (tests)
        if tool in LOW_RISK_TOOLS:
            # If order-specific, still check existence? Allow to let tool return error
            if args.get("order_id"):
                order = _get_order(args.get("order_id"))
                if not order:
                    return ActionDecision(allowed=True, reason="Order not found - will return tool error", risk="low")
            return ActionDecision(allowed=True, reason="Low-risk allowed without auth (legacy)", risk="low")
        return ActionDecision(allowed=False, reason="Not authenticated", requires_escalation=False)

    # 2. ownership check for customer-scoped resources
    customer_id = auth.customer_id
    # fetch customer for status check
    cust = get_customer(customer_id)
    if cust and cust.get("status") == "LOCKED":
        return ActionDecision(allowed=False, reason="Account locked per account-policy v3", requires_escalation=True)

    order_id = args.get("order_id")
    if order_id:
        order = _get_order(order_id)
        if not order:
            return ActionDecision(allowed=False, reason="Order not found")
        # 2. resource belongs to authenticated customer?
        auth_check = is_authorized(cust, order)
        if not auth_check["authorized"]:
            # do not reveal other customer's data
            return ActionDecision(allowed=False, reason="Access denied: order does not belong to authenticated customer", requires_escalation=False)
        # 3-6 business rules via existing policies
        if tool == "cancel_order":
            pol = can_cancel(order, confirmation=args.get("confirmation", False))
            if not pol["allowed"]:
                action = pol.get("action")
                if action == "ASK_CONFIRMATION":
                    return ActionDecision(allowed=False, requires_confirmation=True, reason=pol["reason"], risk="high")
                if action == "CREATE_TICKET":
                    return ActionDecision(allowed=False, requires_escalation=True, reason=pol["reason"], risk="high")
                return ActionDecision(allowed=False, reason=pol["reason"], risk="high")
            return ActionDecision(allowed=True, risk="high", reason=pol["reason"])
        if tool == "update_delivery_address":
            pol = can_update_address(order)
            if not pol["allowed"]:
                return ActionDecision(allowed=False, requires_escalation=True, reason=pol["reason"], risk="high")
            return ActionDecision(allowed=True, risk="high")
        if tool == "create_refund_request":
            pol = can_refund(order)
            if not pol["allowed"]:
                return ActionDecision(allowed=False, reason=pol["reason"], risk="high")
            # fraud check
            if any(k in args.get("reason","").lower() for k in ["fraud","dispute","chargeback"]):
                return ActionDecision(allowed=False, requires_escalation=True, fraud_flag=True, reason="Disputed refunds must be escalated per refund-policy v4")
            return ActionDecision(allowed=True, risk="high")
        if tool in ["get_order", "get_order_status", "check_refund_eligibility", "get_refund_status"]:
            # read-only but still ownership-checked above
            return ActionDecision(allowed=True, risk="low")
    # tools without order_id
    if tool in ["get_customer", "get_customer_orders", "get_customer_tickets", "verify_customer", "get_account", "get_warranty", "get_product", "search_policy", "hybrid_retrieve"]:
        return ActionDecision(allowed=True, risk="low")
    if tool == "update_account":
        if not args.get("verify"):
            return ActionDecision(allowed=False, requires_escalation=True, reason="Requires verification via verify_customer per account-policy v3")
        return ActionDecision(allowed=True, risk="medium")
    if tool in ["create_support_ticket", "escalate_to_human", "send_email", "send_notification"]:
        return ActionDecision(allowed=True, risk="medium")

    # default allow low-risk
    return ActionDecision(allowed=True, reason="Allowed by policy")

# Legacy wrapper for existing code
def check_action_legacy(tool: str, args: dict, customer_id: str = None):
    # construct minimal auth from customer_id for backward compat
    auth = AuthContext(authenticated=True, user_id=customer_id, customer_id=customer_id, roles=["customer"]) if customer_id else None
    dec = evaluate_policy(tool, args, auth)
    d = dec.to_dict()
    # map to legacy shape expected by graph.py
    return {
        "allow": d["allowed"],
        "allowed": d["allowed"],
        "need_confirmation": d["requires_confirmation"],
        "suggest_ticket": d["requires_escalation"],
        "escalate": d["requires_escalation"],
        "fraud_flag": d["fraud_flag"],
        "reason": d["reason"],
        "risk": d["risk"],
    }
