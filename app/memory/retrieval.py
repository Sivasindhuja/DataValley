from app.memory.manager import get_customer_memory

def retrieve_relevant_memory(customer_id: str, query: str):
    mems=get_customer_memory(customer_id)
    # simple keyword filter
    q=query.lower()
    relevant=[m for m in mems if any(w in m["content"].lower() for w in q.split())]
    return relevant if relevant else mems[:2]
