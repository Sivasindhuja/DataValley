import re
INJECTION_PATTERNS = [
    r"ignore.*previous.*instructions",
    r"system\s*prompt",
    r"admin\s*database",
    r"jailbreak",
    r"do anything now",
    r"ignore.*policy",
    r"reveal.*instructions",
    r"act as.*admin",
    r"bypass.*guardrail",
    r"override.*policy",
]
def detect_injection(text: str):
    low = text.lower()
    for pat in INJECTION_PATTERNS:
        if re.search(pat, low):
            return True
    return False
