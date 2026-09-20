from app.tools.db import get_session, Refund, Order
import uuid
from datetime import datetime

def get_refund_status(refund_id: str):
    s = get_session()
    r = s.query(Refund).filter_by(id=refund_id).first()
    s.close()
    if not r: return {"error": "Refund not found"}
    return {"id": r.id, "order_id": r.order_id, "status": r.status, "amount": r.amount}

def check_refund_eligibility(order_id: str):
    s = get_session()
    o = s.query(Order).filter_by(id=order_id).first()
    if not o:
        s.close()
        return {"eligible": False, "reason": "Order not found"}
    # simplified policy
    if o.status != "DELIVERED":
        s.close()
        return {"eligible": False, "reason": f"Order status {o.status} not eligible; must be DELIVERED per refund-policy v4"}
    # check delivered date within 30 days (synthetic)
    s.close()
    return {"eligible": True, "reason": "Eligible per refund-policy v4"}

def create_refund_request(order_id: str, customer_id: str, reason: str = ""):
    elig = check_refund_eligibility(order_id)
    if not elig["eligible"]:
        return {"success": False, "error": elig["reason"]}
    s = get_session()
    new_id = f"R{uuid.uuid4().hex[:4].upper()}"
    r = Refund(id=new_id, order_id=order_id, customer_id=customer_id, status="PROCESSING", amount=s.query(Order).filter_by(id=order_id).first().amount, created_at=datetime.utcnow().isoformat())
    s.add(r)
    s.commit()
    s.close()
    return {"success": True, "refund_id": new_id, "status": "PROCESSING", "timeline": "5-7 business days per refund-policy v4"}
