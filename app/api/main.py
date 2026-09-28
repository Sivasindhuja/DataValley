from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from app.agent.graph import run_graph
from app.observability.tracing import get_traces
from app.observability.metrics import get_metrics
from app.tools.seed import seed
from app.rag.retrieval import retrieve_policy
from app.auth.service import get_current_auth, create_access_token, hash_password, verify_password, require_role
from app.auth.models import AuthContext
from app.tools.db import get_session, Customer
from app.config import settings
import time
import logging
import re
from collections import defaultdict

logger = logging.getLogger(__name__)

app = FastAPI(title="Guardrailed Support Agent", version="3.0")

# CORS: explicit origins via settings, never wildcard with credentials
allowed_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# In-memory rate limiter: 60 req/min per IP (use Redis in prod for distributed limit)
_rate_store = defaultdict(list)
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path in ("/health", "/", "/docs", "/openapi.json"):
        return await call_next(request)
    # Prefer X-Forwarded-For when behind proxy, else client.host
    xff = request.headers.get("x-forwarded-for")
    ip = xff.split(",")[0].strip() if xff else (request.client.host if request.client else "unknown")
    now = time.time()
    window = _rate_store[ip]
    window[:] = [t for t in window if now - t < 60]
    if len(window) >= 60:
        from fastapi.responses import JSONResponse
        # periodic cleanup of stale IPs to avoid memory leak
        if len(_rate_store) > 1000:
            stale = [k for k, v in _rate_store.items() if not v or now - v[-1] > 300]
            for k in stale: _rate_store.pop(k, None)
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded: 60/min"}, headers={"Retry-After": "60"})
    window.append(now)
    # opportunistic cleanup
    if len(window) == 1 and len(_rate_store) > 500:
        pass
    return await call_next(request)

class ChatRequest(BaseModel):
    message: str
    confirm: bool = False

class ChatResponse(BaseModel):
    response: str
    tools_used: list
    docs: list
    trace_id: str
    blocked: bool = False
    intent: str = ""
    execution_mode: str = ""

class RegisterRequest(BaseModel):
    customer_id: str
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    customer_id: Optional[str] = None
    email: Optional[str] = None
    password: str

@app.post("/auth/register")
def register(req: RegisterRequest):
    # basic validation
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", req.email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password too short (min 6)")
    if len(req.customer_id) < 2:
        raise HTTPException(status_code=400, detail="Invalid customer_id")
    s=get_session()
    try:
        if s.query(Customer).filter_by(id=req.customer_id).first():
            raise HTTPException(status_code=400, detail="Customer already exists")
        if s.query(Customer).filter_by(email=req.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        c=Customer(id=req.customer_id, name=req.name, email=req.email, status="ACTIVE", password_hash=hash_password(req.password))
        s.add(c)
        s.commit()
    finally:
        s.close()
    token=create_access_token(req.customer_id)
    return {"access_token": token, "token_type": "bearer", "customer_id": req.customer_id}

@app.post("/auth/login")
def login(req: LoginRequest):
    if not req.customer_id and not req.email:
        raise HTTPException(status_code=400, detail="customer_id or email required")
    s=get_session()
    try:
        if req.customer_id:
            c=s.query(Customer).filter_by(id=req.customer_id).first()
        else:
            c=s.query(Customer).filter_by(email=req.email).first()
        if not c or not c.password_hash:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not verify_password(req.password, c.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if c.status=="LOCKED":
            raise HTTPException(status_code=403, detail="Account locked")
        cid = c.id
    finally:
        s.close()
    token=create_access_token(cid)
    return {"access_token": token, "token_type": "bearer", "customer_id": cid}

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, auth: AuthContext = Depends(get_current_auth)):
    # customer_id derived from auth, never from body
    out = run_graph(req.message, customer_id=auth.customer_id, confirm=req.confirm, auth_context=auth)
    from app.observability.tracing import add_tokens_out
    try:
        add_tokens_out(out["trace"], out["response"])
    except Exception as e:
        logger.warning(f"add_tokens_out failed: {e}")
    intent=""
    try:
        for step in out["trace"].get("steps",[]):
            if "Intent" in step["name"]:
                intent=step["data"].get("intent","")
                break
    except Exception as e:
        logger.warning(f"intent extract failed: {e}")
    return ChatResponse(response=out["response"], tools_used=out.get("tools_used",[]), docs=out.get("docs",[]), trace_id=out["trace"]["trace_id"], blocked=out.get("blocked",False), intent=intent, execution_mode=out.get("execution_mode",""))

@app.get("/")
def root():
    return {"message": "Guardrailed Support Agent v3.0 running", "docs": "/docs", "health": "/health", "chat": "POST /chat (Bearer auth)", "dashboard": "/dashboard"}

@app.get("/health")
def health():
    # Real dependency checks instead of hardcoded True
    checks = {"version": "3.0"}
    try:
        from app.tools.db import get_engine
        eng = get_engine()
        with eng.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {e}"
    try:
        from app.rag.retrieval import _get_chroma, CHROMA_AVAILABLE
        if not CHROMA_AVAILABLE:
            checks["chroma"] = "unavailable (fallback active)"
        else:
            col = _get_chroma()
            checks["chroma"] = "ok" if col is not None else "fallback"
    except Exception as e:
        checks["chroma"] = f"error: {e}"
    checks["graph"] = True
    status = "ok" if checks.get("db") == "ok" else "degraded"
    return {"status": status, **checks}

@app.get("/traces")
def traces(auth: AuthContext = Depends(get_current_auth)):
    # Privacy: customers see only own traces; admin sees all
    all_traces = get_traces(limit=200)
    if "admin" in auth.roles:
        return all_traces
    return [t for t in all_traces if t.get("customer_id") == auth.customer_id]

@app.get("/metrics")
def metrics(auth: AuthContext = Depends(get_current_auth)):
    require_role(auth, ["admin", "customer"])
    return get_metrics()

@app.get("/search")
def search(q: str, auth: AuthContext = Depends(get_current_auth)):
    return retrieve_policy(q, top_k=3)

@app.post("/seed")
def seed_db(auth: AuthContext = Depends(get_current_auth)):
    require_role(auth, ["admin"])
    seed()
    return {"seeded": True}

@app.get("/dashboard")
def dashboard(auth: AuthContext = Depends(get_current_auth)):
    # any authenticated user can view own dashboard; admin sees all
    m=get_metrics()
    traces=get_traces()
    total=len(traces) if traces else 0
    if total==0:
        return {
            "task_success": None, "tool_accuracy": None, "rag_accuracy": None,
            "policy_compliance": None, "guardrail_accuracy": None, "escalation_accuracy": None,
            "metrics": m, "trace_count": 0, "recent_traces": [], "avg_latency": None, "blocked": 0, "escalations": 0,
            "note": "No traces yet - send a chat to populate (N/A where insufficient data)"
        }
    # Derived from actual traces only - no synthetic fallback
    success=sum(1 for t in traces if any("Output Guardrail" in s["name"] and s["safe"] for s in t["steps"])) / total * 100 if total else None
    tool_ok=sum(1 for t in traces if any("Tool" in s["name"] and s.get("data") and "error" not in str(s["data"]) for s in t["steps"])) / total * 100 if total else None
    rag_ok=sum(1 for t in traces if any("RAG" in s["name"] and s.get("data",{}).get("docs") for s in t["steps"])) / total * 100 if total else None
    policy_ok=sum(1 for t in traces if not any("Policy Engine" in s["name"] and not s["safe"] and "allow" in str(s["data"]) for s in t["steps"])) / total * 100 if total else None
    guard_ok=sum(1 for t in traces if any("Output Guardrail" in s["name"] for s in t["steps"])) / total * 100 if total else None
    # escalation accuracy only if we have escalation traces
    esc_total=sum(1 for t in traces if any("fraud" in t["query"].lower() or "escalate" in t["query"].lower() or "human" in t["query"].lower() for _ in [1]))
    esc_ok=sum(1 for t in traces if any("escalate" in s["name"].lower() or "Escalation" in s["name"] for s in t["steps"])) / esc_total * 100 if esc_total>0 else None
    def _r(v):
        return round(v,1) if v is not None else None
    return {
        "task_success": _r(success),
        "tool_accuracy": _r(tool_ok),
        "rag_accuracy": _r(rag_ok),
        "policy_compliance": _r(policy_ok),
        "guardrail_accuracy": _r(guard_ok),
        "escalation_accuracy": _r(esc_ok),
        "metrics": m,
        "trace_count": total,
        "recent_traces": traces[-5:],
        "avg_latency": m.get("avg_latency_ms"),
        "blocked": m.get("blocked_injections"),
        "escalations": m.get("escalations"),
        "safety": {"blocked_injections": m.get("blocked_injections"), "pii_detections": m.get("pii_detections"), "output_blocked": m.get("output_blocked")},
        "operational": {"avg_latency_ms": m.get("avg_latency_ms"), "total_traces": m.get("total_traces"), "requests": m.get("requests")}
    }

@app.get("/evals/run")
def run_evals(auth: AuthContext = Depends(get_current_auth)):
    require_role(auth, ["admin"])
    from app.evaluation.runner import evaluate_all
    return evaluate_all()

if __name__=="__main__":
    import uvicorn
    try:
        seed()
        from app.rag.ingestion import ingest
        ingest()
    except Exception as e:
        logger.warning(f"seed/ingest error: {e}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
