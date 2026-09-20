def format_citation(doc_meta: dict):
    return f"{doc_meta.get('document')} {doc_meta.get('version')} ({doc_meta.get('effective_date','')})"

def attach_citations(response: str, docs: list):
    cites = ", ".join(format_citation(d["metadata"]) for d in docs[:2])
    if cites and cites not in response:
        response += f"\n\nSources: {cites}"
    return response
