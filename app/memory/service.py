from app.memory.manager import get_short_term_history, get_structured_customer_memory, get_customer_memory
from app.memory.retrieval import retrieve_relevant_memory

class MemoryService:
    def retrieve(self, customer_id: str, query: str, top_k=3):
        # Single entry point: returns structured + semantic memories
        structured = get_structured_customer_memory(customer_id)
        relevant = retrieve_relevant_memory(customer_id, query, top_k=top_k)
        return {"structured": structured, "memories": relevant}

    def get_short_term(self, messages, window=6):
        return get_short_term_history(messages, window=window)

memory_service = MemoryService()
