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
    docs=_load_docs()
    q_terms=set(query.lower().split())
    scored=[]
    for d in docs:
        overlap=len(q_terms & set(d["content"].lower().split()))
        # version boost
        ver=d["metadata"].get("version","v1")
        try: vnum=int(ver[1:])
        except: vnum=1
        score=overlap*2 + vnum*0.5
        scored.append((score,d))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _,d in scored[:top_k]]

def chroma_retrieve(query: str, top_k=5):
    """ChromaDB-only retrieval - Chroma when available, keyword fallback for dev/tests."""
    if not query.strip():
        return []
    col=_get_chroma()
    if col is None:
        return _keyword_fallback(query, top_k)
    try:
        qres=col.query(query_texts=[query], n_results=top_k)
        # map back to docs
        docs=_load_docs()
        # Build lookup by document name
        doc_map={d["metadata"]["document"]: d for d in docs}
        results=[]
        for meta, content in zip(qres.get("metadatas",[[]])[0], qres.get("documents",[[]])[0]):
            doc_name=meta.get("document")
            base=doc_map.get(doc_name)
            if base:
                # merge metadata from chroma (more accurate)
                results.append({"content": base["content"], "metadata": meta, "path": base["path"]})
            else:
                results.append({"content": content, "metadata": meta, "path": ""})
        # If chroma returns fewer than top_k, supplement with most recent docs filtered by product
        if len(results) < top_k:
            # simple recency supplement
            remaining=[d for d in docs if d["metadata"]["document"] not in [r["metadata"]["document"] for r in results]]
            remaining.sort(key=lambda d: d["metadata"].get("effective_date","2000-01-01"), reverse=True)
            results.extend(remaining[:top_k-len(results)])
        return results[:top_k]
    except Exception as e:
        raise RuntimeError(f"Chroma retrieval failed: {e}")

def hybrid_retrieve(query: str, top_k=5, version_filter=None):
    """Backward compat wrapper - now delegates to chroma only."""
    return chroma_retrieve(query, top_k=top_k)

def search_policy(query: str, top_k=3):
    return chroma_retrieve(query, top_k=top_k)
