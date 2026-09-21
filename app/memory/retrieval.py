from app.memory.manager import get_customer_memory
import os

def retrieve_relevant_memory(customer_id: str, query: str, top_k=3):
    mems=get_customer_memory(customer_id)
    if not mems: return []
    # if embeddings enabled, semantic ranking
    if os.getenv("ENABLE_EMBEDDINGS","false").lower()=="true":
        try:
            from sentence_transformers import SentenceTransformer
            model=SentenceTransformer(os.getenv("EMBEDDING_MODEL","all-MiniLM-L6-v2"))
            import numpy as np
            q_emb=model.encode([query], normalize_embeddings=True)[0]
            texts=[m["content"] for m in mems]
            d_embs=model.encode(texts, normalize_embeddings=True)
            sims=d_embs @ q_emb
            ranked=sorted(zip(sims, mems), key=lambda x: x[0], reverse=True)
            # filter >0.3
            filtered=[m for s,m in ranked if s>0.3]
            return filtered[:top_k] if filtered else [m for _,m in ranked[:1]]
        except: pass
    # fallback keyword filter
    q=query.lower()
    # score by token overlap
    scored=[]
    for m in mems:
        overlap=len(set(q.split()) & set(m["content"].lower().split()))
        scored.append((overlap,m))
    scored.sort(key=lambda x: x[0], reverse=True)
    relevant=[m for s,m in scored if s>0]
    return relevant[:top_k] if relevant else mems[:1]
