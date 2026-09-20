from app.tools.db import get_session, Customer

def get_account(customer_id: str):
    s=get_session()
    c=s.query(Customer).filter_by(id=customer_id).first()
    s.close()
    if not c: return {"error":"Customer not found"}
    return {"id":c.id,"name":c.name,"email":c.email,"status":c.status,"preference":c.communication_preference}

def update_account(customer_id: str, email: str=None, communication_preference: str=None, verify: bool=False):
    s=get_session()
    c=s.query(Customer).filter_by(id=customer_id).first()
    if not c:
        s.close()
        return {"success":False,"error":"Customer not found"}
    if c.status=="LOCKED":
        s.close()
        return {"success":False,"error":"Account locked per account-policy v3"}
    if not verify:
        s.close()
        return {"success":False,"error":"Requires verification via verify_customer per account-policy v3","need_verification":True}
    if email: c.email=email
    if communication_preference: c.communication_preference=communication_preference
    s.commit()
    s.close()
    return {"success":True,"customer_id":customer_id}
