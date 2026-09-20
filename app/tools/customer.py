from app.tools.db import get_session, Customer, Order, Ticket

def get_customer(customer_id: str):
    s = get_session()
    c = s.query(Customer).filter_by(id=customer_id).first()
    s.close()
    if not c: return {"error": "Customer not found"}
    return {"id": c.id, "name": c.name, "email": c.email, "status": c.status, "communication_preference": c.communication_preference}

def get_customer_orders(customer_id: str):
    s = get_session()
    orders = s.query(Order).filter_by(customer_id=customer_id).all()
    s.close()
    return [{"id": o.id, "status": o.status, "product": o.product, "amount": o.amount} for o in orders]

def get_customer_tickets(customer_id: str):
    s = get_session()
    tickets = s.query(Ticket).filter_by(customer_id=customer_id).all()
    s.close()
    return [{"id": t.id, "issue": t.issue, "status": t.status, "priority": t.priority} for t in tickets]

def verify_customer(customer_id: str, email: str = None):
    s = get_session()
    c = s.query(Customer).filter_by(id=customer_id).first()
    s.close()
    if not c: return {"verified": False, "reason": "not found"}
    if c.status == "LOCKED": return {"verified": False, "reason": "account locked"}
    if email and email != c.email: return {"verified": False, "reason": "email mismatch"}
    return {"verified": True, "customer_id": c.id}
