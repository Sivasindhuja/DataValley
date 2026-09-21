import os, re
from pathlib import Path
from datetime import datetime

try:
    import chromadb
    CHROMA_AVAILABLE=True
except:
    CHROMA_AVAILABLE=False

from rank_bm25 import BM25Okapi
from app.rag.reranker import rerank

KNOWLEDGE_DIR = Path("knowledge")
_docs_cache = None
_bm25 = None
_corpus_tokens = None
_chroma_collection = None
_embed_model = None
_doc_embeddings = None

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
        # normalize
        meta.setdefault("version","v1")
        meta.setdefault("effective_date","2000-01-01")
        meta.setdefault("product","all")
        meta.setdefault("document", md_path.stem)
        docs.append({"content": text.strip(), "metadata": meta, "path": str(md_path)})
    # keep only latest version per document (by effective_date)
    latest={}
    for d in docs:
        key=d["metadata"]["document"]
        cur=latest.get(key)
        if not cur or d["metadata"]["effective_date"] > cur["metadata"]["effective_date"]:
            latest[key]=d
    # but keep all for candidate pool, reranker will prefer latest; store filtered list as cache but keep all
    _docs_cache=docs
    return docs

def _init_bm25():
    global _bm25, _corpus_tokens
    docs=_load_docs()
    corpus=[d["content"] for d in docs]
    _corpus_tokens=[c.lower().split() for c in corpus]
    _bm25=BM25Okapi(_corpus_tokens)

def _get_embed_model():
    global _embed_model
    if _embed_model is not None: return _embed_model
    if os.getenv("ENABLE_EMBEDDINGS","false").lower()=="false":
        return None
    try:
        from sentence_transformers import SentenceTransformer
        _embed_model = SentenceTransformer(os.getenv("EMBEDDING_MODEL","all-MiniLM-L6-v2"))
        return _embed_model
    except Exception as e:
        print(f"Embeddings disabled: {e}")
        return None

def _get_doc_embeddings():
    global _doc_embeddings
    if _doc_embeddings is not None: return _doc_embeddings
    model=_get_embed_model()
    if not model: return None
    docs=_load_docs()
    try:
        texts=[d["content"][:2000] for d in docs]
        _doc_embeddings = model.encode(texts, normalize_embeddings=True)
        return _doc_embeddings
    except Exception as e:
        print(f"Embedding encode failed: {e}")
        return None

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

def _filter_candidates(query: str, docs: list, version_filter: str=None):
    cands=docs
    # version filter
    if version_filter:
        cands=[d for d in cands if version_filter in d["metadata"].get("version","")]
    # product filter: if query mentions product-a/b/c, prefer those + all
    qlow=query.lower()
    prod=None
    for p in ["product-a","product-b","product-c"]:
        if p in qlow:
            prod=p
            break
    if prod:
        cands=[d for d in cands if d["metadata"].get("product") in [prod, "all"]]
    return cands

def hybrid_retrieve(query: str, top_k=5, version_filter: str=None):
    docs=_load_docs()
    if _bm25 is None: _init_bm25()
    candidates=_filter_candidates(query, docs, version_filter)

    # BM25 scores
    scores=_bm25.get_scores(query.lower().split())
    scored=list(zip(scores, docs))
    cand_ids=set(id(c) for c in candidates)
    filtered=[(s,d) for s,d in scored if id(d) in cand_ids]
    filtered.sort(key=lambda x: x[0], reverse=True)
    bm25_top=[d for _,d in filtered[:top_k*2]]
    # normalize BM25 scores 0-1
    if filtered:
        max_s=max(s for s,_ in filtered) or 1
        bm25_norm={id(d): s/max_s for s,d in filtered}
    else:
        bm25_norm={}

    # Embedding cosine
    emb_model=_get_embed_model()
    vec_scores={}
    if emb_model and query.strip():
        try:
            import numpy as np
            q_emb=emb_model.encode([query], normalize_embeddings=True)[0]
            doc_embs=_get_doc_embeddings()
            if doc_embs is not None:
                sims = (doc_embs @ q_emb)  # cosine since normalized
                for d, sim in zip(docs, sims):
                    if id(d) in cand_ids:
                        vec_scores[id(d)] = float(sim)
        except Exception as e:
            pass

    # Optional Qdrant boost (spec §7: Qdrant as vector DB)
    qdrant_url=os.getenv("QDRANT_URL")
    if qdrant_url and query.strip():
        try:
            from qdrant_client import QdrantClient
            qc=QdrantClient(url=qdrant_url, timeout=2)
            # quick check collection exists
            cols=[c.name for c in qc.get_collections().collections]
            if "knowledge" in cols:
                hits=qc.search(collection_name="knowledge", query_vector=[0]*384, limit=top_k, with_payload=True)  # placeholder; real embed would query
                # fallback: if we have embedding, use vector search helper would be here; for now boost via payload match
                pass
        except: pass
    # Optional Chroma boost
    col=_get_chroma()
    if col and query.strip():
        try:
            qres=col.query(query_texts=[query], n_results=top_k)
            for meta in qres.get("metadatas",[[]])[0]:
                for d in docs:
                    if d["metadata"].get("document")==meta.get("document") and id(d) in cand_ids:
                        vec_scores[id(d)] = vec_scores.get(id(d),0) + 0.3
        except: pass

    # Hybrid fusion: 0.4 BM25 + 0.6 embedding (if available) else BM25
    fused=[]
    for d in candidates:
        b=bm25_norm.get(id(d),0)
        v=vec_scores.get(id(d),0)
        if vec_scores:
            score=0.4*b + 0.6*v
        else:
            score=b
        # recency boost for latest version already in reranker, but add slight
        try:
            date=datetime.fromisoformat(d["metadata"].get("effective_date","2000-01-01"))
            recency=(date - datetime(2000,1,1)).days/10000
            score+=recency
        except: pass
        fused.append((score,d))
    fused.sort(key=lambda x: x[0], reverse=True)
    top=[d for _,d in fused[:top_k*2]]

    # Reranker (cross-encoder style: embedding already used, now recency + exact overlap)
    reranked=rerank(query, top, top_k=top_k)
    return reranked

def search_policy(query: str, top_k=3):
    return hybrid_retrieve(query, top_k=top_k)
