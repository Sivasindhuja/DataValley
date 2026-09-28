from app.guardrails.input import validate_input
from app.policies.engine import evaluate_policy
from app.auth.models import AuthContext
def make_auth(cid="C102"):
    return AuthContext(authenticated=True, user_id=cid, customer_id=cid, roles=["customer"])
def test_pii_detection():
    r=validate_input("My card is 4111-1111-1111-1111")
    assert "card" in r["pii"]

def test_high_risk_block():
    dec=evaluate_policy("cancel_order", {"order_id": "123"}, make_auth("C102"))
    d=dec.to_dict()
    assert d["allowed"]==False
    assert d["requires_escalation"]==True or d["requires_confirmation"]==True

def test_low_risk_allow():
    dec=evaluate_policy("get_order_status", {"order_id":"123"}, make_auth("C102"))
    assert dec.allowed==True
