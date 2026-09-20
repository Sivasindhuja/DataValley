from app.rag.retrieval import hybrid_retrieve
def eval_retrieval(query: str, expected_doc: str, top_k=3):
    docs=hybrid_retrieve(query, top_k=top_k)
    docs_names=[d["metadata"].get("document") for d in docs]
    return {"recall@k": expected_doc in docs_names, "docs": docs_names, "mrr": 1/(docs_names.index(expected_doc)+1) if expected_doc in docs_names else 0}
