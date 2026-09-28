# Guardrailed AI Customer Support Agent

![Python](https://img.shields.io/badge/python-3.11-3776ab)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2.39-1c3c3c)
![LangChain](https://img.shields.io/badge/LangChain-0.2.16-1c3c3c)
![Chroma](https://img.shields.io/badge/ChromaDB-0.5.5-646cff)
![React](https://img.shields.io/badge/React-18.3-61dafb)

Production-style memory-augmented customer support agent with **RAG + MCP + policy-based guardrails + human escalation + evals + tracing**.

> The LLM decides *what* it wants to do. Deterministic business logic decides whether it is *allowed* to.

---

## Table of Contents

- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Running with Docker](#running-with-docker)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Tools & MCP Servers](#tools--mcp-servers)
- [Knowledge Base](#knowledge-base)
- [Seed Data](#seed-data)
- [Testing](#testing)
- [Evaluations](#evaluations)
- [Observability](#observability)
- [Project Layout](#project-layout)
- [Build Phases](#build-phases)
- [Setup Gotchas](#setup-gotchas)

---

## Architecture

```
                          ┌───────────────┐
   Customer ──message──▶  │Input Guardrail│──unsafe──▶ 🔒 Blocked response
                          └───────┬───────┘
                                  │ safe
                          ┌───────▼───────┐
                          │  LangGraph    │
                          │  + Gemini     │
                          └───┬───┬───┬───┘
              ┌───────────────┘   │   └───────────────┐
              ▼                   ▼                   ▼
      ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
      │ Memory        │   │ RAG           │   │ MCP Tools     │
      │ Postgres/Redis│   │ Chroma+BM25   │   │ 4 servers     │
      │ SQLite fb     │   │ + reranker    │   │ direct | mcp  │
      └───────┬───────┘   └───────┬───────┘   └───────┬───────┘
              └───────────────────┼───────────────────┘
                          ┌───────▼────────┐
                          │  Policy Engine │  ← deterministic ALLOW / BLOCK
                          └───────┬────────┘
                                  │
                          ┌───────▼────────┐
                          │Output Guardrail│──unsafe──▶ 🔒 Redacted response
                          └───────┬────────┘
                                  │ safe
                          ┌───────▼────────┐
                          │  Respond       │──▶ Customer
                          └───────┬────────┘
                                  │
                                  ├──▶ 🚨 Human Escalation
                                  └──▶ 💾 Memory (episodic + customer)
```

**Agent graph nodes** (`app/agent/graph.py:542-549`):

```
input_guardrail → intent_step → memory_step → rag_step → tool_step
                → respond → output_guardrail → store_memory
```

Design notes:

- **Guardrails wrap the graph, not a single node.** Input guardrails run before any LLM call; output guardrails run after the response is composed.
- **Policy Engine is not the LLM.** It receives `(tool, args, auth)` and returns a deterministic `ActionDecision`. A model that hallucinates a tool call still gets blocked.
- **Every authenticated call is traced** to `data/traces.jsonl` and optionally to OTLP.
- **Node names avoid state-key collisions.** `intent_step` / `memory_step` / `rag_step` / `tool_step` are suffixed because LangGraph rejects nodes sharing a name with a state key (see [FIX.md](FIX.md)).

---

## Quick Start

Local, lightweight — no Docker required.

```bash
pip install -r requirements.txt
cp .env.example .env      # set GOOGLE_API_KEY, JWT_SECRET, CORS_ORIGINS

python -m app.tools.seed       # seed customers, orders, refunds, tickets, memories
python -m app.rag.ingestion    # index knowledge/ into Chroma + BM25
python -m app.api.main         # FastAPI on http://localhost:8000
```

Frontend:

```bash
cd client
npm install
npm run dev                    # React + Vite on http://localhost:5173
```

The frontend stores its JWT in `localStorage` and sends `Authorization: Bearer <token>` automatically.

> Read [FIX.md](FIX.md) **before** troubleshooting — it documents the venv setup, `langchain==0.2.16` pinning, and the known `fastmcp` resolver warnings.

---

## Running with Docker

Postgres + Redis + Chroma.

```bash
cp .env.example .env
# set GOOGLE_API_KEY
#      DATABASE_URL=postgresql://postgres:postgres@db:5432/support
#      REDIS_URL=redis://redis:6379/0
#      TOOL_EXECUTION_MODE=direct
#      CORS_ORIGINS=https://yourdomain.com

docker-compose up --build
```

| Service | URL |
| --- | --- |
| API + interactive docs | http://localhost:8000/docs |
| Dashboard | http://localhost:8000/dashboard |
| Traces | http://localhost:8000/traces |
| Evals (admin) | http://localhost:8000/evals/run |

---

## Configuration

All settings live in `app/config.py` (a `pydantic-settings` `BaseSettings` class) and are read from `.env`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `GOOGLE_API_KEY` | — | Gemini API key (required for the LLM) |
| `LLM_MODEL` | `gemini-1.5-flash` | Chat model. Legacy `LM_MODEL` is auto-mapped |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence embeddings for Chroma |
| `DATABASE_URL` | `sqlite:///./data/app.db` | SQLAlchemy URL. Postgres via `postgresql://…` |
| `CHROMA_PERSIST_DIR` | `./data/chroma` | Vector store persistence dir |
| `REDIS_URL` | *(unset)* | Memory cache. Unset ⇒ in-process cache |
| `TOOL_EXECUTION_MODE` | `direct` | `direct` (in-process) or `mcp` (stdio servers) |
| `JWT_SECRET` | `dev-secret-…` | HS256 signing key — **change in production** |
| `JWT_ALGORITHM` | `HS256` | Token algorithm |
| `JWT_EXPIRE_MINUTES` | `1440` | Access token lifetime |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated; never `*` with credentials |
| `OTEL_ENABLED` | `true` | Emit OpenTelemetry spans |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | *(unset)* | OTLP collector URL (optional) |
| `ENABLE_GUARDRAILS` | `true` | Master switch for guardrails |

`DATABASE_URL` accepts `sqlite+aiosqlite://` and legacy `postgres://` and normalises both automatically (`app/config.py:45-51`).

---

## API Reference

All endpoints except `/`, `/health`, and `/docs` require `Authorization: Bearer <jwt>`. Rate limit is **60 req/min per IP** (in-memory; use Redis for distributed limiting in production).

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `POST` | `/auth/register` | public | Create customer + return access token |
| `POST` | `/auth/login` | public | Login by `customer_id` **or** email |
| `POST` | `/chat` | bearer | Run the agent graph |
| `GET` | `/` | public | Service banner + links |
| `GET` | `/health` | public | Live checks: DB, Chroma, graph |
| `GET` | `/traces` | bearer | Own traces; `admin` sees all |
| `GET` | `/metrics` | bearer | Counters and latency |
| `GET` | `/search?q=` | bearer | Direct RAG retrieval (top-3) |
| `POST` | `/seed` | admin | Re-seed the database |
| `GET` | `/dashboard` | bearer | Derived metrics from real traces |
| `GET` | `/evals/run` | admin | Execute the full eval suite |

### Register and chat

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"customer_id":"C102","name":"Alex","email":"a@test.com","password":"pass123"}'

curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"customer_id":"C102","password":"password123"}'
# => {"access_token":"…","token_type":"bearer","customer_id":"C102"}

TOKEN=<access_token>

curl -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"message":"My order #123 hasn'"'"'t arrived"}' \
  http://localhost:8000/chat
```

`/chat` returns `response`, `tools_used`, `docs`, `trace_id`, `blocked`, `intent`, and `execution_mode`. The `customer_id` is always derived from the token — never from the request body.

---

## Tools & MCP Servers

Business tools are plain Python functions in `app/tools/`, exposed through four MCP servers (`app/mcp/client.py:44-47`).

| Server | Tools |
| --- | --- |
| `customer-mcp` | `get_customer`, `get_customer_orders`, `get_customer_tickets`, `verify_customer`, `get_account`, `update_account` |
| `order-mcp` | `get_order`, `get_order_status`, `cancel_order`, `update_delivery_address` |
| `support-mcp` | `create_support_ticket`, `update_support_ticket`, `escalate_to_human`, `get_ticket`, `send_email`, `send_notification` |
| `knowledge-mcp` | `retrieve_policy`, `get_product`, `get_warranty`, `get_product_status` |

`TOOL_EXECUTION_MODE=direct` calls them in-process (no server overhead). `TOOL_EXECUTION_MODE=mcp` spawns each server over stdio with healthcheck and timeout. `execution_mode` is echoed on every trace and chat response.

### Policy engine

`app/policies/engine.py` evaluates every tool call before execution. Representative rules:

- `SHIPPED` orders **cannot** be cancelled → routes to `create_support_ticket`
- `SHIPPED` orders **cannot** have their delivery address changed → manual review
- Refunds and orders are ownership-scoped: `C102` reading `C103`'s refund gets `Access denied`
- `LOCKED` accounts (`C104`) are blocked from `cancel_order`, `update_delivery_address`, `create_refund_request`
- High-risk intents require explicit confirmation

### Guardrails

- **Input** — 26 injection patterns, PII detection (card / SSN / phone / email), scope checks (`app/guardrails/`)
- **Output** — groundedness against retrieved policy docs, plus version citation checks
- Toggle with `ENABLE_GUARDRAILS=false` (not recommended outside tests)

---

## Knowledge Base

13 Markdown documents under `knowledge/`, indexed by `python -m app.rag.ingestion`:

```
knowledge/
├── faq/faq.md
├── policies/       account · cancellation · refund · shipping · warranty
├── products/       product-a · product-b · product-c
└── troubleshooting/ delivery · login · payment · product
```

Retrieval is a hybrid of Chroma vector search and a BM25-style keyword scorer, followed by a version/recency-weighted reranker (`app/rag/retrieval.py`, `app/rag/reranker.py`). If Chroma is unavailable, retrieval falls back to the keyword path automatically — no flag required.

Canonical entry point: `retrieve_policy(query, top_k=5)`. (`hybrid_retrieve` and `chroma_retrieve` are deprecated aliases and emit `DeprecationWarning`.)

---

## Seed Data

`python -m app.tools.seed` creates 3 customers, 4 orders, 2 refunds, 1 ticket, and 2 memory records.

| Customer | Name | Email | Status | Orders |
| --- | --- | --- | --- | --- |
| `C102` | Alex Johnson | alex@example.com | ACTIVE | `123` SHIPPED, `124` PENDING |
| `C103` | Priya Singh | priya@example.com | ACTIVE | `125` DELIVERED, `126` PROCESSING |
| `C104` | John Locked | john@example.com | LOCKED | — |

All three use password `password123`.

- Refunds: `R421` (order 125, C103, PROCESSING), `R422` (order 123, C102, COMPLETED)
- Ticket: `T42` (order 123, C102, OPEN)
- Memories: both belong to C102 (episodic + customer)

C104 exists specifically to exercise the locked-account policy path; C102/C103 exist to exercise cross-customer ownership denial.

---

## Testing

```bash
pytest -q        # 35 tests
```

| File | Covers |
| --- | --- |
| `tests/test_graph.py` | End-to-end graph: order status, cancellation, address updates, refunds, escalation, warranty, guardrails, tool failure |
| `tests/test_agent.py` | Agent entry-point contract |
| `tests/test_security.py` | JWT auth, customer isolation, policy enforcement, confirmation gating, order-ID parsing, password hashing, MCP mode |
| `tests/conftest.py` | Session-scoped seed + `AuthContext` fixtures |

Tests require a real `GOOGLE_API_KEY` — they exercise the live agent graph.

---

## Evaluations

```bash
python -m app.evaluation.runner       # CLI
curl -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8000/evals/run
```

**52 cases across 11 categories:**

| Category | Cases | Focus |
| --- | --- | --- |
| `account` | 5 | Account lookups and preference updates |
| `cancellation` | 7 | Cancel eligibility by order state |
| `escalation` | 4 | Human-handoff triggers (fraud, out of policy) |
| `memory` | 3 | Recall of prior conversation state |
| `order` | 6 | Status and tracking lookups |
| `pii` | 4 | PII refusal in both directions |
| `policy_conflict` | 3 | Conflicting policy resolution |
| `product` | 4 | Product specs and warranty |
| `prompt_injection` | 7 | Injection attempt resistance |
| `refund` | 6 | Refund status, ownership, requests |
| `tool_failure` | 3 | Graceful degradation on tool errors |

Reported metrics:

- `task_success` — percentage of cases passing every assertion
- `tool_accuracy` — expected tools invoked, and no extras under `strict_tools`
- `retrieval` — `avg_recall@3`, `avg_mrr`, `avg_ndcg`
- `safety` — injection, PII, and output-guardrail checks

Per-case schema supports `expected_tools`, `strict_tools`, `expected_policy`, `strict_retrieval`, and `expected_behavior.action` (`BLOCK` / `ALLOW`).

---

## Observability

- **Traces** — every request produces a trace with named steps (Authentication, Intent, RAG, Tools, Policy Engine, Output Guardrail), persisted to `data/traces.jsonl` and optionally exported via OTLP when `OTEL_ENABLED=true` and an OTLP endpoint is set.
- **Metrics** — request count, blocked injections, PII detections, output blocks, escalations, average latency.
- **Dashboard** — `GET /dashboard` derives task success, tool accuracy, RAG accuracy, policy compliance, guardrail accuracy, and escalation accuracy **from real traces only**. With no traces it returns `null` and a note rather than synthetic numbers.
- **Privacy** — `/traces` filters to the caller's own traces unless the token carries the `admin` role.

---

## Project Layout

```
app/
├── agent/          LangGraph nodes, planner, router, prompts, state
├── api/            FastAPI app, middleware, routes
├── auth/           JWT issue/verify, roles, AuthContext
├── evaluation/     Dataset runner, retrieval/tool/safety scoring
├── guardrails/     input · injection (26 patterns) · pii · output
├── mcp/            client + customer/order/support/knowledge servers
├── memory/         manager, policy, retrieval, service
├── policies/       engine, authorization, cancellation, refunds
├── rag/            ingestion, retrieval (Chroma+BM25), reranker, citations
├── tools/          business tools + SQLAlchemy models + seed
└── observability/  tracing, metrics

client/             React 18 + Vite frontend
knowledge/          13 policy/FAQ/product/troubleshooting docs
evals/              52 cases in 11 categories
tests/              35 pytest tests
data/               app.db, chroma/, traces.jsonl, *.log
```

**Deployment shape:** hybrid. SQLite fallback for local dev, Postgres + Redis + Chroma via env toggle in production. The DB engine is a singleton (pooled when Postgres). MCP supports `direct` and `mcp` modes with timeout and healthcheck.

---

## Build Phases

1. Scaffold + synthetic data
2. RAG + tools + policies
3. Memory + MCP (via `app/mcp/client.py` with stdio fallback)
4. Agent (LangGraph)
5. Guardrails (input / action / output + RAG grounding)
6. API + UI + observability (OTel) + evals

### End-to-end example

```
"My order #123 hasn't arrived. Can you check and cancel it if possible?"

Input Guardrail        ✓ safe
Memory                 C102 active_orders [123, 124]
RAG                    shipping-policy v4 + cancellation-policy v3
MCP tools              get_order, get_order_status
Policy Engine          SHIPPED → not cancellable → CREATE_TICKET
Output Guardrail       ✓ grounded, cites policy version

→ "Your order #123 has already shipped… I've created support request T42
   for manual review."
```

---

## Setup Gotchas

Setup, venv creation, dependency pinning, and resolver warnings are documented in **[FIX.md](FIX.md)**. Start there if:

- `pip install -r requirements.txt` reports `fastmcp` / `httpx` / `pydantic` conflicts
- you hit `ValueError: 'intent' is already being used as a state key`
- Chroma's embedding model download stalls on first run
- the eval or test suite fails at import time

**Do not install `langchain 1.x`** — the code requires `langchain==0.2.16` per `requirements.txt`.
