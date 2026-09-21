"""Ingest knowledge base into ChromaDB (single vector store)"""
import os
from pathlib import Path
from app.config import settings

def ingest():
    from app.rag.retrieval import _load_docs
    docs=_load_docs()
    print(f"Loaded {len(docs)} docs")
    # ChromaDB only - no Qdrant/BM25
    try:
        import chromadb
        persist = settings.chroma_persist_dir
        os.makedirs(persist, exist_ok=True)
        client = chromadb.PersistentClient(path=persist)
        col = client.get_or_create_collection("knowledge")
        try:
            ids = col.get()["ids"]
            if ids: col.delete(ids=ids)
        except: pass
        for i,d in enumerate(docs):
            col.add(ids=[f"doc_{i}"], documents=[d["content"][:8000]], metadatas=[d["metadata"]])
        print(f"Ingested {len(docs)} docs into Chroma at {persist}")
    except Exception as e:
        print(f"Chroma ingestion failed: {e}")
        raise
    for d in docs:
        print(f" - {d['metadata'].get('document')} {d['metadata'].get('version')}")

if __name__=="__main__":
    ingest()
