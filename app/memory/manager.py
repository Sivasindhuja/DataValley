from app.tools.db import get_session, MemoryStore
from datetime import datetime
import os, json

# Redis cache layer (spec §9: PostgreSQL + Redis) - optional
try:
    import redis
    _redis = redis.from_url(os.getenv("REDIS_URL",""), decode_responses=True) if os.getenv("REDIS_URL") else None
    if _redis:
        _redis.ping()
except:
    _redis = None

def get_short_term_history(messages: list, window=6):
    return messages[-window:]

def get_customer_memory(customer_id: str):
    # Redis cache first (1 min TTL)
    if _redis:
        try:
            cached=_redis.get(f"mem:{customer_id}")
            if cached:
                return json.loads(cached)
        except: pass
    s=get_session()
    mems=s.query(MemoryStore).filter_by(customer_id=customer_id).all()
    s.close()
    out=[{"id": m.id, "content": m.content, "type": m.type, "created_at": m.created_at.isoformat() if m.created_at else None} for m in mems]
    if _redis:
        try: _redis.setex(f"mem:{customer_id}", 60, json.dumps(out))
        except: pass
    return out

def get_structured_customer_memory(customer_id: str):
    """Spec §9 Customer Memory: persistent structured snapshot across conversations."""
    from app.tools.customer import get_customer, get_customer_orders, get_customer_tickets
    cust=get_customer(customer_id)
    orders=get_customer_orders(customer_id)
    tickets=get_customer_tickets(customer_id)
    active_orders=[o["id"] for o in orders if o.get("status") in ["PENDING","PROCESSING","SHIPPED"]]
    open_tickets=[t["id"] for t in tickets if t.get("status") in ["OPEN","ESCALATED","IN_PROGRESS"]]
    episodic=get_customer_memory(customer_id)
    return {
        "customer_id": customer_id,
        "communication_preference": cust.get("communication_preference") or cust.get("preference") or "email",
        "active_orders": active_orders,
        "open_tickets": open_tickets,
        "status": cust.get("status"),
        "episodic_count": len([m for m in episodic if m["type"]=="episodic"]),
        "recent_episodic": episodic[-3:] if episodic else []
    }

def _embedding_similarity(a: str, b: str):
    # lightweight: if embeddings enabled use cosine, else fallback to token overlap
    if os.getenv("ENABLE_EMBEDDINGS","false").lower()=="true":
        try:
            from sentence_transformers import SentenceTransformer
            model=SentenceTransformer(os.getenv("EMBEDDING_MODEL","all-MiniLM-L6-v2"))
            import numpy as np
            emb=model.encode([a,b], normalize_embeddings=True)
            return float(emb[0] @ emb[1])
        except: pass
    # token overlap fallback
    sa=set(a.lower().split())
    sb=set(b.lower().split())
    if not sa or not sb: return 0
    return len(sa & sb)/len(sa | sb)

def should_store(candidate: str, existing: list):
    if not candidate or len(candidate)<10: return False
    # exact duplicate
    if any(candidate==e["content"] for e in existing): return False
    # semantic dedup >0.92
    for e in existing:
        if _embedding_similarity(candidate, e["content"]) > 0.92:
            return False
    # reject PII-like
    low=candidate.lower()
    if "card" in low and any(c.isdigit() for c in candidate):
        return False
    if "password" in low or "ssn" in low:
        return False
    # not useful?
    if len(candidate.split())<4:
        return False
    return True

def store_memory(customer_id: str, content: str, type="episodic"):
    s=get_session()
    existing=get_customer_memory(customer_id)
    if not should_store(content, existing):
        s.close()
        return {"stored": False, "reason": "Rejected by policy (duplicate/PII/not useful)"}
    m=MemoryStore(customer_id=customer_id, content=content, type=type)
    s.add(m)
    s.commit()
    s.close()
    # invalidate redis
    if _redis:
        try: _redis.delete(f"mem:{customer_id}")
        except: pass
    return {"stored": True}
