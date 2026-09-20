"""Ingest knowledge base into ChromaDB if available + build BM25 index"""
import os
from pathlib import Path

def ingest():
    from app.rag.retrieval import _load_docs
    docs=_load_docs()
    print(f"Loaded {len(docs)} docs")
    # Try Chroma ingestion
    try:
        import chromadb
        persist = os.getenv("CHROMA_PERSIST_DIR","./data/chroma")
        os.makedirs(persist, exist_ok=True)
        client = chromadb.PersistentClient(path=persist)
        col = client.get_or_create_collection("knowledge")
        # clear existing
        try:
            ids = col.get()["ids"]
            if ids: col.delete(ids=ids)
        except: pass
        for i,d in enumerate(docs):
            col.add(ids=[f"doc_{i}"], documents=[d["content"][:8000]], metadatas=[d["metadata"]])
        print(f"Ingested {len(docs)} docs into Chroma at {persist}")
    except Exception as e:
        print(f"Chroma ingestion skipped: {e}")
    # BM25 built lazily on retrieval
    print("BM25 ready (lazy)")
    for d in docs:
        print(f" - {d['metadata'].get('document')} {d['metadata'].get('version')}")

if __name__=="__main__":
    ingest()
