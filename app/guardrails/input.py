from app.guardrails.pii import detect_pii, redact_pii
from app.guardrails.injection import detect_injection

SCOPE_KEYWORDS = ["order", "refund", "shipping", "cancel", "ticket", "account", "product", "warranty", "delivery", "payment", "login", "address", "human", "support", "escalate"]

def validate_input(text: str):
    if detect_injection(text):
        return {"safe": False, "reason": "Prompt injection detected", "action": "BLOCK"}
    pii = detect_pii(text)
    out_of_scope = not any(k in text.lower() for k in SCOPE_KEYWORDS)
    abuse = any(w in text.lower() for w in ["idiot", "stupid agent"])
    result = {"safe": True, "pii": pii, "out_of_scope": out_of_scope, "abuse": abuse}
    if pii:
        result["redacted"] = redact_pii(text)
    # out_of_scope not unsafe, just flag for agent to redirect
    return result
