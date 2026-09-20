from app.guardrails.input import validate_input
from app.guardrails.actions import check_action
def test_pii_detection():
    r=validate_input("My card is 4111-1111-1111-1111")
    assert "card" in r["pii"]

def test_high_risk_block():
    r=check_action("cancel_order", {"order_id": "123"}, customer_id="C102")
    assert r["allow"]==False
    assert "suggest_ticket" in r or "need_confirmation" in r

def test_low_risk_allow():
    r=check_action("get_order_status", {"order_id":"123"})
    assert r["allow"]==True
