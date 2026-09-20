from app.tools.db import get_session, MemoryStore
from datetime import datetime

def get_short_term_history(messages: list, window=6):
    return messages[-window:]

def get_customer_memory(customer_id: str):
    s=get_session()
    mems=s.query(MemoryStore).filter_by(customer_id=customer_id).all()
    s.close()
    return [{"content": m.content, "type": m.type, "created_at": m.created_at.isoformat() if m.created_at else None} for m in mems]

def should_store(candidate: str, existing: list):
    if not candidate or len(candidate)<10: return False
    if any(candidate==e["content"] for e in existing): return False
    # reject PII-like
    if "card" in candidate.lower() and any(c.isdigit() for c in candidate): return False
    return True

def store_memory(customer_id: str, content: str, type="episodic"):
    s=get_session()
    existing=get_customer_memory(customer_id)
    if not should_store(content, existing):
        s.close()
        return {"stored": False, "reason": "Rejected by policy"}
    m=MemoryStore(customer_id=customer_id, content=content, type=type)
    s.add(m)
    s.commit()
    s.close()
    return {"stored": True}
