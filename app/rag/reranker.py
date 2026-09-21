# Reranker: embedding cosine already fused, now keyword overlap + recency + version precedence
from datetime import datetime

def rerank(query: str, docs: list, top_k=3):
    q_terms = set(query.lower().split())
    scored=[]
    for d in docs:
        content=d.get("content","").lower()
        overlap=len(q_terms & set(content.split())) / (len(q_terms)+1)
        # version weight: v4 > v3 > v2 > v1
        ver=d.get("metadata",{}).get("version","v1")
        try:
            vnum=int(ver[1:])
            ver_score=vnum/10
        except: ver_score=0
        date_str=d.get("metadata",{}).get("effective_date","2000-01-01")
        try:
            date=datetime.fromisoformat(date_str)
            recency=(date - datetime(2000,1,1)).days/10000
        except: recency=0
        # citation-ready boost: docs with product=all slightly preferred for general queries
        score=overlap*0.5 + ver_score*0.3 + recency*0.2
        scored.append((score,d))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _,d in scored[:top_k]]
