import time, uuid, json, os
from datetime import datetime

_traces = []

# OpenTelemetry optional - support OTLP when configured, else console
try:
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
    # If OTEL_EXPORTER_OTLP_ENDPOINT is set, use OTLP exporter
    _provider = TracerProvider()
    _otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if _otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            _provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint=_otlp_endpoint)))
        except Exception as e:
            print(f"OTLP exporter failed, fallback to console: {e}")
            _provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    else:
        _provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    # Only set if not already set
    try:
        otel_trace.set_tracer_provider(_provider)
    except: pass
    OTEL_AVAILABLE=True
    tracer=otel_trace.get_tracer("support-agent")
except:
    OTEL_AVAILABLE=False
    tracer=None

def _load_persisted_traces():
    # Load from file on startup if memory empty
    if _traces:
        return
    try:
        path = "data/traces.jsonl"
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    try:
                        # full trace persisted in extended format
                        t = json.loads(line.strip())
                        if isinstance(t, dict) and "trace_id" in t:
                            _traces.append(t)
                    except: continue
    except: pass

def start_trace(customer_id: str, query: str, auth_context=None):
    trace_id = str(uuid.uuid4())[:8]
    trace = {"trace_id": trace_id, "customer_id": customer_id, "query": query, "steps": [], "start": time.time(), "timestamp": datetime.utcnow().isoformat(), "tokens_in": len(query.split()), "tokens_out": 0, "otel_span": None, "auth": {"customer_id": customer_id, "authenticated": bool(auth_context.is_authenticated()) if auth_context else False, "roles": auth_context.roles if auth_context else []}, "execution_mode": None}
    if OTEL_AVAILABLE:
        span=tracer.start_span(f"agent.run {trace_id}")
        span.set_attribute("customer_id", customer_id)
        span.set_attribute("query", query[:200])
        trace["otel_span"]=span
    _traces.append(trace)
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
    # persist full trace (without otel_span) to file
    try:
        os.makedirs("data", exist_ok=True)
        persist = {k: v for k, v in trace.items() if k != "otel_span"}
        # make json serializable: convert start float
        persist_copy = json.loads(json.dumps(persist, default=str))
        with open("data/traces.jsonl","a", encoding="utf-8") as f:
            f.write(json.dumps(persist_copy)+"\n")
    except: pass
    return trace

def get_traces(limit: int = 50):
    _load_persisted_traces()
    # sanitize: remove otel_span before returning
    out=[]
    for t in _traces[-limit:]:
        out.append({k: v for k, v in t.items() if k != "otel_span"})
    return out

def add_tokens_out(trace: dict, text: str):
    trace["tokens_out"] = len(text.split())
