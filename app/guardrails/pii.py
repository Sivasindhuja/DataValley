import re
PATTERNS = {
    "card": re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "password": re.compile(r"password\s*[:=]\s*\S+", re.I),
}
def detect_pii(text: str):
    findings = []
    for name, pat in PATTERNS.items():
        if pat.search(text):
            findings.append(name)
    return findings

def redact_pii(text: str):
    for pat in PATTERNS.values():
        text = pat.sub("[REDACTED]", text)
    return text
