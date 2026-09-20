import os, glob, re, json
from pathlib import Path

# Lightweight hybrid: vector via chroma if available else BM25 only fallback
# For MVP, use simple TF + BM25 without embeddings dependency at runtime - gracefully degrade
try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE=True
except: CHROMA_AVAILABLE=False

from rank_bm25 import BM25Okapi
from app.rag.reranker import rerank

KNOWLEDGE_DIR = Path("knowledge")
CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")

_docs_cache = None
_bm25 = None
_corpus_tokens = None

def _load_docs():
    global _docs_cache
    if _docs_cache is not None: return _docs_cache
    docs=[]
    for md_path in KNOWLEDGE_DIR.rglob("*.md"):
        text = md_path.read_text(encoding="utf-8")
        # parse frontmatter
        meta={}
        if text.startswith("---"):
            parts = text.split("---",2)
            if len(parts)>=3:
                fm, content = parts[1], parts[2]
                for line in fm.strip().splitlines():
                    if ":" in line:
                        k,v=line.split(":",1)
                        meta[k.strip()]=v.strip().strip('"')
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

def hybrid_retrieve(query: str, top_k=5):
    docs=_load_docs()
    if _bm25 is None: _init_bm25()
    # BM25
    scores=_bm25.get_scores(query.lower().split())
    ranked=sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)[:top_k*2]
    candidates=[d for _, d in ranked]
    # Optional vector boost via Chroma if available and embedded
    # For now return BM25 + rerank
    reranked=rerank(query, candidates, top_k=top_k)
    return reranked

def search_policy(query: str, top_k=3):
    return hybrid_retrieve(query, top_k=top_k)
