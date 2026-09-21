import time, uuid, json, os
from datetime import datetime

_traces = []

# OpenTelemetry optional
try:
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
    otel_trace.set_tracer_provider(TracerProvider())
    otel_trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    OTEL_AVAILABLE=True
    tracer=otel_trace.get_tracer("support-agent")
except:
    OTEL_AVAILABLE=False
    tracer=None

def start_trace(customer_id: str, query: str, auth_context=None):
    trace_id = str(uuid.uuid4())[:8]
    trace = {"trace_id": trace_id, "customer_id": customer_id, "query": query, "steps": [], "start": time.time(), "timestamp": datetime.utcnow().isoformat(), "tokens_in": len(query.split()), "tokens_out": 0, "otel_span": None, "auth": {"customer_id": customer_id, "authenticated": bool(auth_context.is_authenticated()) if auth_context else False, "roles": auth_context.roles if auth_context else []}, "execution_mode": None}
    if OTEL_AVAILABLE:
        span=tracer.start_span(f"agent.run {trace_id}")
        span.set_attribute("customer_id", customer_id)
        span.set_attribute("query", query[:200])
        trace["otel_span"]=span
    _traces.append(trace)
    # also persist to file for dashboard
    try:
        os.makedirs("data", exist_ok=True)
        with open("data/traces.jsonl","a", encoding="utf-8") as f:
            f.write(json.dumps({"trace_id":trace_id,"customer_id":customer_id,"query":query,"timestamp":trace["timestamp"]})+"\n")
    except: pass
    return trace

def log_step(trace: dict, name: str, data: dict, safe: bool = True):
    trace["steps"].append({"name": name, "data": data, "safe": safe, "at": datetime.utcnow().isoformat()})
    if OTEL_AVAILABLE and trace.get("otel_span"):
        trace["otel_span"].add_event(name, attributes={"safe": safe, "data": str(data)[:500]})

def end_trace(trace: dict):
    trace["latency_ms"] = int((time.time() - trace["start"])*1000)
    ti=trace.get("tokens_in",0)
    to=trace.get("tokens_out",0)
    trace["cost_usd"] = round((ti+to)/1000*0.001,6)
    if OTEL_AVAILABLE and trace.get("otel_span"):
        trace["otel_span"].set_attribute("latency_ms", trace["latency_ms"])
        trace["otel_span"].set_attribute("cost_usd", trace["cost_usd"])
        trace["otel_span"].end()
        trace["otel_span"]=None
    return trace

def get_traces():
    return _traces[-50:]

def add_tokens_out(trace: dict, text: str):
    trace["tokens_out"] = len(text.split())
