from app.policies.engine import evaluate_policy, ActionDecision
from app.auth.models import AuthContext

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

def check_action(tool: str, args: dict, customer_id: str = None, auth_context: AuthContext = None):
    # Central policy engine - single source of truth
    if auth_context is None and customer_id:
        auth_context = AuthContext(authenticated=True, user_id=customer_id, customer_id=customer_id, roles=["customer"])
    decision = evaluate_policy(tool, args, auth_context)
    d = decision.to_dict()
    legacy = {"allow": d["allowed"], "allowed": d["allowed"], "need_confirmation": d["requires_confirmation"], "suggest_ticket": d["requires_escalation"], "escalate": d["requires_escalation"], "fraud_flag": d["fraud_flag"], "reason": d["reason"], "risk": d["risk"]}
    # preserve need_verification for update_account
    if tool in ["update_account","change_account_information"] and not args.get("verify"):
        legacy["need_verification"] = True
    return legacy
