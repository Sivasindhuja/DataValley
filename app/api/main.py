from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from app.agent.graph import run_graph
from app.observability.tracing import get_traces
from app.observability.metrics import get_metrics
from app.tools.seed import seed
from app.rag.retrieval import chroma_retrieve
from app.auth.service import get_current_auth, create_access_token, hash_password, verify_password
from app.auth.models import AuthContext
from app.tools.db import get_session, Customer
from app.config import settings

app = FastAPI(title="Guardrailed Support Agent", version="3.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

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
    s=get_session()
    if s.query(Customer).filter_by(id=req.customer_id).first():
        s.close()
        raise HTTPException(status_code=400, detail="Customer already exists")
    if s.query(Customer).filter_by(email=req.email).first():
        s.close()
        raise HTTPException(status_code=400, detail="Email already registered")
    c=Customer(id=req.customer_id, name=req.name, email=req.email, status="ACTIVE", password_hash=hash_password(req.password))
    s.add(c)
    s.commit()
    s.close()
    token=create_access_token(req.customer_id)
    return {"access_token": token, "token_type": "bearer", "customer_id": req.customer_id}

@app.post("/auth/login")
def login(req: LoginRequest):
    s=get_session()
    c=None
    if req.customer_id:
        c=s.query(Customer).filter_by(id=req.customer_id).first()
    elif req.email:
        c=s.query(Customer).filter_by(email=req.email).first()
    else:
        s.close()
        raise HTTPException(status_code=400, detail="customer_id or email required")
    s.close()
    if not c or not c.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(req.password, c.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if c.status=="LOCKED":
        raise HTTPException(status_code=403, detail="Account locked")
    token=create_access_token(c.id)
    return {"access_token": token, "token_type": "bearer", "customer_id": c.id}

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, auth: AuthContext = Depends(get_current_auth)):
    # customer_id derived from auth, never from body
    out = run_graph(req.message, customer_id=auth.customer_id, confirm=req.confirm, auth_context=auth)
    from app.observability.tracing import add_tokens_out
    try:
        add_tokens_out(out["trace"], out["response"])
    except: pass
    # extract intent safely
    intent=""
    try:
        for step in out["trace"].get("steps",[]):
            if "Intent" in step["name"]:
                intent=step["data"].get("intent","")
                break
    except: pass
    return ChatResponse(response=out["response"], tools_used=out.get("tools_used",[]), docs=out.get("docs",[]), trace_id=out["trace"]["trace_id"], blocked=out.get("blocked",False), intent=intent, execution_mode=out.get("execution_mode",""))

@app.get("/")
def root():
    return {"message": "Guardrailed Support Agent v3.0 running", "docs": "/docs", "health": "/health", "chat": "POST /chat (Bearer auth)", "dashboard": "/dashboard"}

@app.get("/health")
def health():
    return {"status": "ok", "version": "3.0", "graph": True, "chroma": True}

@app.get("/traces")
def traces(auth: AuthContext = Depends(get_current_auth)):
    # For demo allow any authenticated user; in prod restrict to admin role
    return get_traces()

@app.get("/metrics")
def metrics():
    return get_metrics()

@app.get("/search")
def search(q: str, auth: AuthContext = Depends(get_current_auth)):
    return chroma_retrieve(q, top_k=3)

@app.post("/seed")
def seed_db():
    seed()
    return {"seeded": True}

@app.get("/dashboard")
def dashboard():
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
    from app.evaluation.runner import evaluate_all
    return evaluate_all()

if __name__=="__main__":
    import uvicorn
    try:
        seed()
        from app.rag.ingestion import ingest
        ingest()
    except Exception as e:
        print("seed error", e)
    uvicorn.run(app, host="0.0.0.0", port=8000)
