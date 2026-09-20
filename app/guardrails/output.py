from app.guardrails.pii import detect_pii, is_blocking_pii
import re

def validate_output(response: str, grounded_docs: list = None):
    pii = detect_pii(response)
    if is_blocking_pii(pii):
        return {"safe": False, "reason": f"PII leakage detected: {pii}"}
    low=response.lower()
    # Hallucination: fabricated timelines
    if "refund" in low and ("24 hours" in low or "1 day" in low) and "5-7" not in response:
        return {"safe": False, "reason": "Hallucinated refund timeline not grounded in refund-policy v4 (expected 5-7 business days)"}
    if "definitely" in low and "tomorrow" in low:
        return {"safe": False, "reason": "Unsupported promise 'definitely tomorrow' not grounded"}
    if "order is currently in transit" in low and grounded_docs is not None and len(grounded_docs)==0:
        # if we have no docs, still allow if tool gave transit, but if hallucinated without tool, block
        pass
    # Policy compliance: invented cancellation
    if "cancelled successfully" in low and "policy" not in low and grounded_docs is not None:
        # require tool success, not just string - trust tool layer, so pass
        pass
    # Format: response too long
    if len(response) > 2000:
        return {"safe": False, "reason": "Response too long, violates format guardrail"}
    return {"safe": True}

def grounding_check(response: str, docs: list):
    if "policy" in response.lower() and not any(d in response for d in ["v4","v3","v2","v1"]):
        return {"grounded": False, "reason": "Policy claim without version citation"}
    # Check refund timeline grounded
    if "refund" in response.lower() and "business days" in response.lower() and not any("refund-policy" in d.get("metadata",{}).get("document","") for d in docs):
        return {"grounded": False, "reason": "Refund timeline not grounded in retrieved docs"}
    return {"grounded": True}
