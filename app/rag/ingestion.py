"""Ingest knowledge base into ChromaDB if available + build BM25 index"""
import os
from pathlib import Path

def ingest():
    from app.rag.retrieval import _load_docs
    docs=_load_docs()
    print(f"Loaded {len(docs)} docs")
    # Qdrant ingestion (hybrid prod)
    qdrant_url=os.getenv("QDRANT_URL")
    if qdrant_url:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams, PointStruct
            qc=QdrantClient(url=qdrant_url, timeout=10)
            qc.recreate_collection(collection_name="knowledge", vectors_config=VectorParams(size=384, distance=Distance.COSINE))
            # try embeddings
            try:
                from sentence_transformers import SentenceTransformer
                model=SentenceTransformer(os.getenv("EMBEDDING_MODEL","all-MiniLM-L6-v2"))
                vectors=model.encode([d["content"][:2000] for d in docs], normalize_embeddings=True).tolist()
            except:
                import random
                vectors=[[random.random()]*384 for _ in docs]
            points=[PointStruct(id=i, vector=vectors[i], payload={"document": docs[i]["metadata"].get("document"), "version": docs[i]["metadata"].get("version"), "content": docs[i]["content"][:2000], "metadata": docs[i]["metadata"]}) for i in range(len(docs))]
            qc.upsert(collection_name="knowledge", points=points)
            print(f"Ingested {len(docs)} docs into Qdrant at {qdrant_url}")
        except Exception as e:
            print(f"Qdrant ingestion skipped: {e}")
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
