from app.rag.retrieval import hybrid_retrieve
def eval_retrieval(query: str, expected_doc: str, top_k=3):
    docs=hybrid_retrieve(query, top_k=top_k)
    docs_names=[d["metadata"].get("document") for d in docs]
    hit=expected_doc in docs_names
    mrr=1/(docs_names.index(expected_doc)+1) if hit else 0
    return {"recall@k": 1 if hit else 0, "precision@k": (1/top_k if hit else 0), "mrr": mrr, "ndcg": mrr, "docs": docs_names, "citation_accuracy": hit, "groundedness": hit}

def eval_retrieval_batch(cases):
    results=[eval_retrieval(c["query"], c["expected_doc"]) for c in cases]
    avg_recall=sum(r["recall@k"] for r in results)/len(results) if results else 0
    avg_mrr=sum(r["mrr"] for r in results)/len(results) if results else 0
    return {"avg_recall@3": avg_recall, "avg_mrr": avg_mrr, "details": results}
