# Guardrailed AI Customer Support Agent

Production-style memory-augmented agent with RAG + MCP + Policy-based Guardrails + Human Escalation + Evals + Tracing.

> LLM decides what it wants to do; deterministic business logic decides whether it is allowed to.

## Architecture
```
Customer -> Input Guardrails -> Support Agent (LangGraph + Gemini) -> Memory / RAG (Chroma + BM25 hybrid + reranker) / MCP Tools -> Action Policy Engine -> Output Guardrails -> Customer
                                                                                                       -> Human Escalation
                               Memory: PostgreSQL + Redis (cached, SQLite fallback) | RAG: Chroma + BM25 hybrid + reranker | MCP: Customer/Order/Support/Knowledge servers (direct|mcp mode)
```

## Quick Start (Lightweight local — no Docker required)
```bash
pip install -r requirements.txt
cp .env.example .env  # add GOOGLE_API_KEY=..., JWT_SECRET, CORS_ORIGINS
python -m app.tools.seed
python -m app.rag.ingestion   # Chroma + BM25 hybrid; reranker applied on retrieve
python -m app.api.main        # FastAPI at http://localhost:8000 (auth required: Bearer JWT)
cd client && npm install && npm run dev  # React at http://localhost:5173
```

## Production (Docker — Postgres + Redis + Chroma)
```bash
cp .env.example .env  # set GOOGLE_API_KEY, DATABASE_URL=postgresql://postgres:postgres@db:5432/support, REDIS_URL=redis://redis:6379/0, TOOL_EXECUTION_MODE=direct, CORS_ORIGINS=https://yourdomain.com
docker-compose up --build
# API at http://localhost:8000/docs, dashboard at /dashboard (auth), traces at /traces (owner/admin), evals at /evals/run (admin only)
```

## E2E Example (Spec §23)
`My order #123 hasn't arrived. Can you check and cancel it if possible?` → Input Guardrail ✓ → Memory (C102 active_orders [123,124]) → RAG (shipping-policy v4 + cancellation-policy v3) → MCP get_order/get_order_status → Policy Engine (SHIPPED→CREATE_TICKET) → Output Guardrail ✓ → `Your order #123 has already shipped... support request Txxx for manual review.`

## Repo Structure
See spec §22. Hybrid: SQLite fallback for dev, Postgres/Redis/Chroma via env toggle. DB engine is singleton (pooled for Postgres). RAG is Chroma + BM25 keyword hybrid + reranker (version/recency weighted). MCP supports `direct` and `mcp` modes with timeout/healthcheck. Guardrails block injection (25+ patterns), PII (card/ssn/phone/email), hallucination; traces are persisted to `data/traces.jsonl` + OTLP optional.

## Auth
```bash
# Register then chat with Bearer token:
curl -X POST http://localhost:8000/auth/register -H "Content-Type: application/json" -d '{"customer_id":"C102","name":"Alex","email":"a@test.com","password":"pass123"}'
curl -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"customer_id":"C102","password":"pass123"}'
TOKEN=<access_token from above>
curl -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"message":"My order #123 hasn'\''t arrived"}' http://localhost:8000/chat
# Frontend stores token in localStorage and sends Authorization: Bearer <token> automatically.
```

## Evaluation
```bash
pytest -q                         # 21 unit tests
python -m app.evaluation.runner   # 52 cases across order/cancellation/refund/pii/injection/etc — reports task_success, tool_accuracy, recall@3, MRR, NDCG
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/evals/run
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/dashboard
```

## Phases
1. Scaffold + Synthetic Data
2. RAG + Tools + Policies
3. Memory + MCP (via app/mcp/client.call with stdio fallback)
4. Agent (LangGraph)
5. Guardrails (input/action/output + RAG grounding)
6. API + UI + Observability (OTel) + Evals
