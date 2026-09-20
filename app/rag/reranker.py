# Simple reranker: score by keyword overlap + metadata recency
from datetime import datetime

def rerank(query: str, docs: list, top_k=3):
    q_terms = set(query.lower().split())
    scored = []
    for d in docs:
        content = d.get("content","").lower()
        overlap = len(q_terms & set(content.split()))
        # prefer newer effective_date
        date_str = d.get("metadata",{}).get("effective_date","2000-01-01")
        try:
            date = datetime.fromisoformat(date_str)
            recency = (date - datetime(2000,1,1)).days / 10000
        except: recency = 0
        score = overlap + recency
        scored.append((score, d))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored[:top_k]]
