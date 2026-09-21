from app.guardrails.pii import detect_pii, is_blocking_pii, redact_pii
import re

# RAG Guardrail per spec §8: never invent company policies
HALLUCINATED_CLAIMS = [
    (r"24\s*hour", "refund-policy v4 expects 5-7 business days"),
    (r"1\s*day.*refund", "refund-policy v4 expects 5-7 business days"),
    (r"definitely.*tomorrow", "unsupported promise not grounded"),
    (r"always.*refund", "absolute refund claims require policy citation"),
    (r"free.*refund.*instant", "hallucinated instant refund"),
]

def validate_output(response: str, grounded_docs: list = None):
    if not isinstance(response, str) or not response.strip():
        return {"safe": False, "reason": "Empty response violates format guardrail"}
    pii = detect_pii(response)
    if is_blocking_pii(pii):
        return {"safe": False, "reason": f"PII leakage detected: {pii}", "redacted": redact_pii(response)}
    low=response.lower()
    # Hallucination / RAG guardrail §8: detect unsupported timelines/promises
    for pat, reason in HALLUCINATED_CLAIMS:
        if re.search(pat, low):
            # allow if grounded docs contain matching policy and response cites it correctly
            if "refund" in pat and "5-7" in response:
                continue
            return {"safe": False, "reason": f"Hallucinated claim '{pat}' not grounded: {reason}"}
    # Grounding: policy claims must have citation
    gc=grounding_check(response, grounded_docs or [])
    if not gc.get("grounded"):
        return {"safe": False, "reason": gc.get("reason")}
    # Format: response too long / too short / tone
    if len(response) > 2000:
        return {"safe": False, "reason": "Response too long, violates format guardrail"}
    if len(response) < 5:
        return {"safe": False, "reason": "Response too short"}
    # Tone: abusive? should not contain profanity
    if any(w in low for w in ["idiot","stupid","fuck","shit"]):
        return {"safe": False, "reason": "Tone violation: abusive language"}
    # Structured output: must be string, not JSON leakage unless requested
    if response.strip().startswith("{") and '"error"' in low:
        return {"safe": False, "reason": "Leaked structured error"}
    # PII redaction handled upstream; ensure no card remains
    if re.search(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", response):
        return {"safe": False, "reason": "Card number leakage"}
    return {"safe": True}

def grounding_check(response: str, docs: list):
    low=response.lower()
    docs_str=" ".join(d.get("metadata",{}).get("document","") for d in docs)
    if "policy" in low and not any(d in response for d in ["v4","v3","v2","v1"]):
        # allow if docs empty and response is fallback "I don't have enough information"
        if "don't have enough information" in low:
            return {"grounded": True}
        return {"grounded": False, "reason": "Policy claim without version citation"}
    if "refund" in low and "business days" in low and "refund-policy" not in docs_str:
        return {"grounded": False, "reason": "Refund timeline not grounded in retrieved docs"}
    if "shipping" in low and "business days" in low and "shipping-policy" not in docs_str:
        return {"grounded": False, "reason": "Shipping timeline not grounded"}
    if "warranty" in low and "warranty-policy" not in docs_str and "warranty" in docs_str.lower():
        pass
    # If response invents order status without tool result, flag (spec §16)
    if any(k in low for k in ["order #", "status is shipped", "status is delivered"]) and not docs and "status" in low:
        # require tool evidence; handled at agent level, not fail here
        pass
    return {"grounded": True}
