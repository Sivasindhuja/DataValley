from app.tools.db import get_session, Ticket
import uuid
from datetime import datetime

def create_support_ticket(customer_id: str, issue: str, order_id: str = None, priority: str = "MEDIUM", summary: str = None):
    s = get_session()
    tid = f"T{uuid.uuid4().hex[:4].upper()}"
    t = Ticket(id=tid, customer_id=customer_id, order_id=order_id, issue=issue, status="OPEN", priority=priority, summary=summary or issue)
    s.add(t)
    s.commit()
    s.close()
    return {"success": True, "ticket_id": tid, "status": "OPEN", "priority": priority}

def update_support_ticket(ticket_id: str, status: str = None, summary: str = None):
    s = get_session()
    t = s.query(Ticket).filter_by(id=ticket_id).first()
    if not t:
        s.close()
        return {"success": False, "error": "Ticket not found"}
    if status: t.status = status
    if summary: t.summary = summary
    s.commit()
    s.close()
    return {"success": True, "ticket_id": ticket_id}

def escalate_to_human(customer_id: str, reason: str, ticket_id: str = None, priority: str = "HIGH"):
    issue = f"Escalation: {reason}"
    res = create_support_ticket(customer_id, issue, priority=priority, summary=reason)
    if ticket_id:
        update_support_ticket(ticket_id, status="ESCALATED")
    return {"escalated": True, "ticket": res, "reason": reason, "message": "Transferred to human agent. Priority HIGH."}

def get_ticket(ticket_id: str):
    s = get_session()
    t = s.query(Ticket).filter_by(id=ticket_id).first()
    s.close()
    if not t: return {"error": "Ticket not found"}
    return {"id": t.id, "customer_id": t.customer_id, "order_id": t.order_id, "issue": t.issue, "status": t.status, "priority": t.priority}
