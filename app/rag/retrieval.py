from pathlib import Path
from datetime import datetime
from app.config import settings

try:
    import chromadb
    CHROMA_AVAILABLE=True
except:
    CHROMA_AVAILABLE=False

KNOWLEDGE_DIR = Path("knowledge")
_docs_cache = None
_chroma_collection = None

def _load_docs():
    global _docs_cache
    if _docs_cache is not None: return _docs_cache
    docs=[]
    for md_path in KNOWLEDGE_DIR.rglob("*.md"):
        text = md_path.read_text(encoding="utf-8")
        meta={}
        if text.startswith("---"):
            parts = text.split("---",2)
            if len(parts)>=3:
                fm, content = parts[1], parts[2]
                for line in fm.strip().splitlines():
                    if ":" in line:
                        k,v=line.split(":",1)
                        meta[k.strip()]=v.strip().strip('"').strip("'")
                text = content
        meta.setdefault("version","v1")
        meta.setdefault("effective_date","2000-01-01")
        meta.setdefault("product","all")
        meta.setdefault("document", md_path.stem)
        docs.append({"content": text.strip(), "metadata": meta, "path": str(md_path)})
    _docs_cache=docs
    return docs

def _get_chroma():
    global _chroma_collection
    if _chroma_collection is not None: return _chroma_collection
    if not CHROMA_AVAILABLE:
        return None
    persist=settings.chroma_persist_dir
    import os
    os.makedirs(persist, exist_ok=True)
    try:
        client=chromadb.PersistentClient(path=persist)
        col=client.get_or_create_collection("knowledge")
        if col.count()==0:
            docs=_load_docs()
            for i,d in enumerate(docs):
                col.add(ids=[f"doc_{i}"], documents=[d["content"][:8000]], metadatas=[d["metadata"]])
        _chroma_collection=col
        return col
    except Exception as e:
        # Fail clearly in production, but allow fallback for tests
        print(f"Chroma unavailable, fallback to keyword search: {e}")
        return None

def _keyword_fallback(query: str, top_k=5):
    """Lightweight BM25-like fallback: TF-IDF-ish scoring + version/recency."""
    import math, re
    docs=_load_docs()
    q_terms=[t for t in re.findall(r"\w+", query.lower()) if len(t) > 2]
    if not q_terms:
        q_terms = query.lower().split()
    # compute doc frequencies for IDF
    N = len(docs) or 1
    df = {}
    for term in set(q_terms):
        df[term] = sum(1 for d in docs if term in d["content"].lower())
    scored=[]
    for d in docs:
        content_lower = d["content"].lower()
        tokens = re.findall(r"\w+", content_lower)
        tf_len = len(tokens) or 1
        score = 0
        for term in q_terms:
            tf = content_lower.count(term) / tf_len
            idf = math.log((N + 1) / (df.get(term, 0) + 1)) + 1
            # BM25-ish k1=1.2
            score += (tf * (1.2 + 1) / (tf + 1.2)) * idf
            # bonus if term in title/document name
            if term in d["metadata"].get("document","").lower():
                score += 0.5
        # version boost
        ver=d["metadata"].get("version","v1")
        try: vnum=int(ver[1:])
        except: vnum=1
        score += vnum * 0.15
        # recency boost (days since 2000)
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(d["metadata"].get("effective_date","2000-01-01"))
            recency = (dt - datetime(2000,1,1)).days / 20000
            score += recency
        except: pass
        scored.append((score,d))
    scored.sort(key=lambda x: x[0], reverse=True)
    # apply reranker for final ordering
    top_candidates = [d for _, d in scored[: max(top_k*2, 10)]]
    try:
        from app.rag.reranker import rerank
        reranked = rerank(query, top_candidates, top_k=top_k)
        if reranked:
            return reranked
    except: pass
    return [d for _,d in scored[:top_k]]

def retrieve_policy(query: str, top_k=5):
    """Canonical policy retrieval: Chroma + BM25 keyword fallback + reranker (version/recency weighted). Single source of truth."""
    return _retrieve_policy_impl(query, top_k=top_k)

def _retrieve_policy_impl(query: str, top_k=5):
    """Implementation: ChromaDB retrieval with BM25 fallback and reranking."""
    if not query.strip():
        return []
    col=_get_chroma()
    if col is None:
        return _keyword_fallback(query, top_k)
    try:
        # fetch more candidates then rerank
        fetch_k = max(top_k*2, 8)
        qres=col.query(query_texts=[query], n_results=fetch_k)
        docs=_load_docs()
        doc_map={d["metadata"]["document"]: d for d in docs}
        results=[]
        for meta, content in zip(qres.get("metadatas",[[]])[0], qres.get("documents",[[]])[0]):
            doc_name=meta.get("document")
            base=doc_map.get(doc_name)
            if base:
                results.append({"content": base["content"], "metadata": meta, "path": base["path"]})
            else:
                results.append({"content": content, "metadata": meta, "path": ""})
        # rerank chroma candidates
        try:
            from app.rag.reranker import rerank
            results = rerank(query, results, top_k=top_k)
        except: results = results[:top_k]
        if len(results) < top_k:
            remaining=[d for d in docs if d["metadata"]["document"] not in [r["metadata"]["document"] for r in results]]
            # rank remaining via keyword fallback scoring
            remaining_scored = _keyword_fallback(query, top_k=len(remaining))
            # filter to not duplicate
            for r in remaining_scored:
                if r["metadata"]["document"] not in [x["metadata"]["document"] for x in results]:
                    results.append(r)
                    if len(results) >= top_k: break
        return results[:top_k]
    except Exception as e:
        # fallback to keyword
        try:
            return _keyword_fallback(query, top_k)
        except: raise RuntimeError(f"Chroma retrieval failed: {e}")

def hybrid_retrieve(query: str, top_k=5, version_filter=None):
    """Deprecated alias -> use retrieve_policy"""
    import warnings; warnings.warn("hybrid_retrieve is deprecated, use retrieve_policy", DeprecationWarning, stacklevel=2)
    return retrieve_policy(query, top_k=top_k)

def search_policy(query: str, top_k=3):
    """Deprecated alias -> use retrieve_policy"""
    import warnings; warnings.warn("search_policy is deprecated, use retrieve_policy", DeprecationWarning, stacklevel=2)
    return retrieve_policy(query, top_k=top_k)

def chroma_retrieve(query: str, top_k=5):
    """Deprecated alias -> use retrieve_policy"""
    import warnings; warnings.warn("chroma_retrieve is deprecated, use retrieve_policy", DeprecationWarning, stacklevel=2)
    return retrieve_policy(query, top_k=top_k)
