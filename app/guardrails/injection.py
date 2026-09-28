import re
INJECTION_PATTERNS = [
    r"ignore.*previous.*instructions",
    r"ignore.*instructions",
    r"ignore.*above",
    r"system\s*prompt",
    r"system\s*instruction",
    r"admin\s*database",
    r"jailbreak",
    r"do anything now",
    r"dan\s*mode",
    r"ignore.*policy",
    r"reveal.*instructions",
    r"reveal.*system",
    r"act as.*admin",
    r"act as.*root",
    r"act as.*system",
    r"bypass.*guardrail",
    r"bypass.*filter",
    r"override.*policy",
    r"override.*safety",
    r"pretend.*admin",
    r"pretend.*system",
    r"roleplay.*admin",
    r"developer\s*mode",
    r"disregard.*instructions",
    r"you are now",
    r"new instructions",
]

def detect_injection(text: str):
    low = text.lower()
    for pat in INJECTION_PATTERNS:
        if re.search(pat, low):
            return True
    # heuristic: multiple instruction-like verbs + policy bypass intent
    if low.count("ignore") >= 1 and any(w in low for w in ["policy","guardrail","instruction","rule"]):
        return True
    return False
