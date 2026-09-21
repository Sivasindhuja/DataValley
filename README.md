# Guardrailed AI Customer Support Agent

Production-style memory-augmented agent with RAG + MCP + Policy-based Guardrails + Human Escalation + Evals + Tracing.

> LLM decides what it wants to do; deterministic business logic decides whether it is allowed to.

## Architecture
```
Customer -> Input Guardrails -> Support Agent (LangGraph + Gemini) -> Memory / RAG (Chroma+BM25+Qdrant) / MCP Tools -> Action Policy Engine -> Output Guardrails -> Customer
                                                                                                      -> Human Escalation
                              Memory: PostgreSQL + Redis (cached) | RAG: Qdrant/Chroma+BM25+reranker | MCP: Customer/Order/Support/Knowledge servers
```

## Quick Start (Lightweight local — no Docker required)
```bash
pip install -r requirements.txt
cp .env.example .env  # add GOOGLE_API_KEY=...
python -m app.tools.seed
python -m app.rag.ingestion   # BM25 always; Chroma/Qdrant if ENABLE_CHROMA/QDRANT_URL set
python -m app.api.main        # FastAPI at http://localhost:8000
cd client && npm install && npm run dev  # React at http://localhost:5173
```

## Production (Docker — Postgres + Qdrant + Redis)
```bash
cp .env.example .env  # set GOOGLE_API_KEY, DATABASE_URL=postgresql://postgres:postgres@db:5432/support, QDRANT_URL=http://qdrant:6333, REDIS_URL=redis://redis:6379/0, ENABLE_MCP=false
docker-compose up --build
# API at http://localhost:8000/docs, dashboard at /dashboard, traces at /traces, evals at /evals/run
```

## E2E Example (Spec §23)
`My order #123 hasn't arrived. Can you check and cancel it if possible?` → Input Guardrail ✓ → Memory (C102 active_orders [123,124]) → RAG (shipping-policy v4 + cancellation-policy v3) → MCP get_order/get_order_status → Policy Engine (SHIPPED→CREATE_TICKET) → Output Guardrail ✓ → `Your order #123 has already shipped... support request Txxx for manual review.`

## Repo Structure
See spec §22. Hybrid: SQLite fallback for dev, Postgres/Qdrant/Redis via env toggle.

## Evaluation
```bash
pytest -q                         # 21 unit tests
python -m app.evaluation.runner   # 52 cases across order/cancellation/refund/pii/injection/etc — reports task_success, tool_accuracy, recall@3, MRR, NDCG
curl http://localhost:8000/evals/run
curl http://localhost:8000/dashboard
```

## Phases
1. Scaffold + Synthetic Data
2. RAG + Tools + Policies
3. Memory + MCP (via app/mcp/client.call with stdio fallback)
4. Agent (LangGraph)
5. Guardrails (input/action/output + RAG grounding)
6. API + UI + Observability (OTel) + Evals
