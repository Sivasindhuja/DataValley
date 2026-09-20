import os, re, json
from pathlib import Path

try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE=True
except:
    CHROMA_AVAILABLE=False

from rank_bm25 import BM25Okapi
from app.rag.reranker import rerank

KNOWLEDGE_DIR = Path("knowledge")
CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")

_docs_cache = None
_bm25 = None
_corpus_tokens = None
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
        docs.append({"content": text.strip(), "metadata": meta, "path": str(md_path)})
    _docs_cache=docs
    return docs

def _init_bm25():
    global _bm25, _corpus_tokens
    docs=_load_docs()
    corpus=[d["content"] for d in docs]
    _corpus_tokens=[c.lower().split() for c in corpus]
    _bm25=BM25Okapi(_corpus_tokens)
    return docs

def _get_chroma():
    if os.getenv("ENABLE_CHROMA","false").lower()!="true":
        return None
    global _chroma_collection
    if not CHROMA_AVAILABLE: return None
    if _chroma_collection is not None: return _chroma_collection
    try:
        persist=os.getenv("CHROMA_PERSIST_DIR","./data/chroma")
        os.makedirs(persist, exist_ok=True)
        client=chromadb.PersistentClient(path=persist)
        col=client.get_or_create_collection("knowledge")
        if col.count()==0:
            docs=_load_docs()
            for i,d in enumerate(docs):
                col.add(ids=[f"doc_{i}"], documents=[d["content"][:8000]], metadatas=[d["metadata"]])
        _chroma_collection=col
        return col
    except Exception as e:
        print(f"Chroma not available: {e}")
        return None

def hybrid_retrieve(query: str, top_k=5, version_filter: str=None):
    docs=_load_docs()
    if _bm25 is None: _init_bm25()
    # version filtering: only docs with effective_date or prefer latest version
    candidates=docs
    if version_filter:
        candidates=[d for d in docs if version_filter in d["metadata"].get("version","")]
    # BM25 scores
    scores=_bm25.get_scores(query.lower().split())
    # map scores to filtered candidates
    # Build score map for all docs then filter
    scored=list(zip(scores, docs))
    # filter to candidates
    cand_ids=set(id(c) for c in candidates)
    filtered=[(s,d) for s,d in scored if id(d) in cand_ids]
    filtered.sort(key=lambda x: x[0], reverse=True)
    bm25_top=[d for _,d in filtered[:top_k*2]]

    # Optional vector boost
    col=_get_chroma()
    if col and query.strip():
        try:
            qres=col.query(query_texts=[query], n_results=top_k)
            vec_docs=[]
            if qres.get("documents"):
                for meta in qres.get("metadatas",[[]])[0]:
                    # find matching doc
                    for d in docs:
                        if d["metadata"].get("document")==meta.get("document"):
                            vec_docs.append(d)
                            break
            # merge: interleave
            merged=[]
            seen=set()
            for d in vec_docs + bm25_top:
                key=d["metadata"].get("document")
                if key not in seen:
                    merged.append(d)
                    seen.add(key)
                if len(merged)>=top_k*2: break
            bm25_top=merged
        except Exception as e:
            pass

    reranked=rerank(query, bm25_top, top_k=top_k)
    # Final: prefer latest effective_date already in reranker
    return reranked

def search_policy(query: str, top_k=3):
    return hybrid_retrieve(query, top_k=top_k)
