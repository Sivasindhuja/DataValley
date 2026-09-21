def format_citation(doc_meta: dict):
    return f"{doc_meta.get('document')} {doc_meta.get('version')} ({doc_meta.get('effective_date','')})"

def attach_citations(response: str, docs: list, enforce: bool=True):
    if not docs:
        return response
    cites=", ".join(format_citation(d["metadata"]) for d in docs[:2])
    if cites and cites not in response:
        # enforce citation if response mentions policy/timeline
        needs=False
        low=response.lower()
        if any(k in low for k in ["policy","refund","cancellation","shipping","warranty","business days"]):
            needs=True
        if enforce and needs:
            response+=f"\n\nSources: {cites}"
        elif not enforce:
            response+=f"\n\nSources: {cites}"
    return response

def has_citation(response: str):
    import re
    return bool(re.search(r"v\d", response))
