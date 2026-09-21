import re
from typing import Optional

# Context-aware routing to fix "ends with ?" bug
# Previous naive: META_QUESTION_RE = re.compile(r"\?$") -> any utterance ending with ? was treated as new question
# Fix: use conversational context (awaiting_answer) + intent heuristics, not punctuation alone.

QUESTION_KEYWORDS = {"what", "when", "where", "who", "why", "how", "can", "could", "would", "should", "is", "are", "do", "does", "did", "will", "have", "has"}
META_QUESTION_RE = re.compile(r"\?\s*$")

def is_meta_question(utterance: str, context: Optional[dict] = None) -> bool:
    """
    Context-aware router: only treat '?' as question when conversational context indicates
    the agent is awaiting an answer and the user is clarifying.
    Spec §9: do not use 'ends with ?' as sufficient evidence.
    """
    if not utterance or not utterance.strip():
        return False
    text = utterance.strip()
    awaiting = False
    if context:
        awaiting = bool(context.get("awaiting_confirmation") or context.get("awaiting_order_id") or context.get("needs_confirmation"))
    # If not awaiting, never classify as meta-question - legitimate user queries with ? are normal intents
    if not awaiting:
        return False
    low = text.lower()
    if low in ["yes", "yes, cancel", "confirm", "no", "cancel"]:
        return False
    if re.match(r"^(R\d+|#?\d{3,})\??$", text.strip(), re.I):
        return False
    # When awaiting, check if utterance is a clarification question like "What do you mean?"
    if META_QUESTION_RE.search(text):
        words = low.split()
        if not words:
            return False
        first = words[0].strip("?")
        if first in QUESTION_KEYWORDS:
            return True
        if any(w in QUESTION_KEYWORDS for w in words[:3]):
            return True
        # Bare hesitation "R421?" already handled
        if re.match(r"^(R\d+|order|#\d+)", text, re.I):
            return False
        # In awaiting context, any ? with sufficient words -> treat as clarification question
        if len(words) >= 3 and "?" in text:
            return True
        return False
    return False

def extract_order_id(text: str):
    """
    Deterministic order ID extraction preserving complete identifier.
    Supports actual formats: R\d+ (refund/order with R prefix) and numeric 123 style with explicit context.
    Do not let arbitrary numbers become IDs.
    """
    if not text:
        return None
    # Prefer R-prefixed IDs: R421, R900
    m = re.search(r"\b(R\d+)\b", text, re.I)
    if m:
        return m.group(1).upper()
    # Explicit order pattern: order R421, order #123, order 123
    m = re.search(r"order\s*#?\s*(R?\d{3,})\b", text, re.I)
    if m:
        val = m.group(1).upper()
        # ensure not capturing bare number without R unless preceded by order/#
        return val
    # Hash pattern: #123, #R421
    m = re.search(r"#\s*(R?\d{3,})\b", text, re.I)
    if m:
        return m.group(1).upper()
    # Fallback: standalone R\d+ already handled, don't match bare digits
    return None

def extract_refund_id(text: str):
    m = re.search(r"\b(R\d+)\b", text, re.I)
    return m.group(1).upper() if m else None
