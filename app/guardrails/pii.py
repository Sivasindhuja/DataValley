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
# Do not flag email as PII unless explicit context asks for redaction? Keep for detection but not block
BLOCK_PII = {"card","card_simple","ssn","password","secret"}
def detect_pii(text: str):
    findings=[]
    for name, pat in PATTERNS.items():
        if pat.search(text):
            findings.append(name)
    return findings

def is_blocking_pii(findings):
    return any(f in BLOCK_PII for f in findings)

def redact_pii(text: str):
    for name, pat in PATTERNS.items():
        if name in BLOCK_PII or name=="phone":
            text = pat.sub("[REDACTED]", text)
    return text
