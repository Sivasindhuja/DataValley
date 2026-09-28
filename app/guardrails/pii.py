import re
PATTERNS = {
    "card": re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
    "card_simple": re.compile(r"\b\d{13,16}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone": re.compile(r"\+?\d{1,3}[- ]?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}"),
    "email": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "password": re.compile(r"password\s*[:=]\s*\S+", re.I),
    "secret": re.compile(r"(api[_-]?key|secret)\s*[:=]\s*\S+", re.I),
}
# Central PII policy - single source of truth for input & output guardrails
# Decision A: BLOCK sensitive PII, REDACT ordinary contact PII and continue
BLOCK_PII = {"card","card_simple","ssn","password","secret"}
REDACT_PII = {"phone","email"}
LEAK_PII = BLOCK_PII | REDACT_PII  # for output leakage check

PII_POLICY = {
    "BLOCK": BLOCK_PII,
    "REDACT": REDACT_PII,
    "LEAK": LEAK_PII,
}

def detect_pii(text: str):
    findings=[]
    for name, pat in PATTERNS.items():
        if pat.search(text):
            findings.append(name)
    return findings

def is_blocking_pii(findings):
    return any(f in BLOCK_PII for f in findings)

def is_redact_pii(findings):
    return any(f in REDACT_PII for f in findings) and not is_blocking_pii(findings)

def is_leak_pii(findings):
    return any(f in LEAK_PII for f in findings)

def redact_pii(text: str):
    for name, pat in PATTERNS.items():
        if name in BLOCK_PII or name in REDACT_PII:
            text = pat.sub("[REDACTED]", text)
    return text
