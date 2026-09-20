# Fix for `ValueError: 'intent' is already being used as a state key` + pip conflicts

## Root cause
`app/agent/graph.py:365` used node name `intent` which collides with `AgentState.intent` `app/agent/state.py:6`. LangGraph 0.2.39+ raises ValueError (see traceback). Also `pip install -r requirements.txt` downgrades langchain 1.2.15 -> 0.2.16, triggering warnings vs `fastmcp 3.2.4` that expects newer httpx/pydantic/mcp.

## Fix applied (already committed)
- `app/agent/graph.py:365-388` renamed nodes: `intent`->`intent_step`, `memory`->`memory_step`, `rag`->`rag_step`, `tools`->`tool_step` to avoid state-key collision.
- `node_output_guardrail` and `node_store_memory` now return non-empty dicts (`app/agent/graph.py:346`) to satisfy `InvalidUpdateError: Must write to at least one ...` in langgraph pregel.
- Verified: `timeout 15 python -c "from app.agent.graph import run_graph; ..."` -> OK, `pytest tests -q` 21 passed, `52/52 evals` passed.

## How to run now
```bash
# 1. Use clean venv (recommended to avoid fastmcp conflicts)
python -m venv .venv
.venv\Scripts\activate  # Windows MINGW: source .venv/Scripts/activate
pip install -r requirements.txt

# Alternative if fastmcp is installed globally and you see resolver warnings:
pip uninstall -y fastmcp
pip install -r requirements.txt

# 2. Start API
python -m app.api.main
# -> Uvicorn running on http://0.0.0.0:8000

# 3. Test
pytest -q
```

## Pip resolver warnings
Warnings like `fastmcp 3.2.4 requires httpx>=0.28.1` are harmless if you use venv. App tested with `requirements.lock.txt` versions. Do NOT use `langchain 1.x` - code requires `langchain==0.2.16` per `requirements.txt:6`.

## If you still see Chroma download stall
Set `ENABLE_CHROMA=false` (default). Vector search falls back to BM25:
```bash
ENABLE_CHROMA=false python -m app.api.main
```
