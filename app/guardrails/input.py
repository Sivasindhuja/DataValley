from app.guardrails.pii import detect_pii, redact_pii, is_blocking_pii
from app.guardrails.injection import detect_injection

SCOPE_KEYWORDS = ["order", "refund", "shipping", "cancel", "ticket", "account", "product", "warranty", "delivery", "payment", "login", "address", "human", "support", "escalate", "email", "verify", "fraud", "dispute", "track", "status"]

ABUSE_TERMS = ["idiot","stupid agent","useless","fuck","shit"]

def validate_input(text: str):
    if detect_injection(text):
        return {"safe": False, "reason": "Prompt injection detected", "action": "BLOCK"}
    pii = detect_pii(text)
    # Only block if high-risk PII like card/ssn/password; email alone not block
    if is_blocking_pii(pii):
        return {"safe": False, "reason": f"Blocking PII detected: {pii}", "action": "REDACT_AND_BLOCK", "pii": pii}
    # ultra-short or empty is not automatically out_of_scope - treat as scope check only for longer queries
    out_of_scope = not any(k in text.lower() for k in SCOPE_KEYWORDS)
    # but very short greetings like "hello", "hi", "thanks" are not out_of_scope
    if len(text.strip().split()) <= 2 and text.lower().strip() in ["hello","hi","hey","thanks","thank you","help"]:
        out_of_scope = False
    abuse = any(w in text.lower() for w in ABUSE_TERMS)
    result = {"safe": True, "pii": pii, "out_of_scope": out_of_scope, "abuse": abuse}
    if pii:
        result["redacted"] = redact_pii(text)
    return result
