# Guardrailed AI Customer Support Agent

Production-style memory-augmented agent with RAG + MCP + Policy-based Guardrails + Human Escalation + Evals + Tracing.

> LLM decides what it wants to do; deterministic business logic decides whether it is allowed to.

## Architecture
```
Customer -> Input Guardrails -> Support Agent (LangGraph + Gemini) -> Memory / RAG (Chroma+BM25) / MCP Tools -> Action Policy Engine -> Output Guardrails -> Customer
                                                                                                      -> Human Escalation
```

## Quick Start (Lightweight local)
```bash
pip install -r requirements.txt
cp .env.example .env  # add GOOGLE_API_KEY
python -m app.rag.ingestion
python -m app.api.main  # FastAPI at http://localhost:8000
cd client && npm install && npm run dev  # React at http://localhost:5173
```

## Repo Structure
See spec section 22. Implemented as lightweight SQLite + ChromaDB for dev, swappable to Postgres/Qdrant/Redis.

## Phases
1. Scaffold + Synthetic Data
2. RAG + Tools + Policies
3. Memory + MCP
4. Agent (LangGraph)
5. Guardrails
6. API + UI + Observability + Evals

