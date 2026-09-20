from app.guardrails.pii import detect_pii
import re

def validate_output(response: str, grounded_docs: list = None):
    # PII check
    pii = detect_pii(response)
    if pii:
        return {"safe": False, "reason": f"PII detected: {pii}"}
    # Hallucination check: no invented policies/timelines if not grounded
    if "refund" in response.lower() and "5-7" not in response and "24 hours" in response:
        return {"safe": False, "reason": "Hallucinated refund timeline not grounded in refund-policy v4"}
    if "definitely" in response.lower() and "tomorrow" in response.lower():
        return {"safe": False, "reason": "Unsupported promise detected"}
    return {"safe": True}

def grounding_check(response: str, docs: list):
    # simple: require citation if policy mentioned
    if "policy" in response.lower() and not any(d in response for d in ["v4", "v3", "v2"]):
        return {"grounded": False, "reason": "Policy claim without citation"}
    return {"grounded": True}
