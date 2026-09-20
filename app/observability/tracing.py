import time, uuid, json
from datetime import datetime

_traces = []

def start_trace(customer_id: str, query: str):
    trace_id = str(uuid.uuid4())[:8]
    trace = {"trace_id": trace_id, "customer_id": customer_id, "query": query, "steps": [], "start": time.time(), "timestamp": datetime.utcnow().isoformat(), "tokens_in": len(query.split()), "tokens_out": 0}
    _traces.append(trace)
    return trace

def log_step(trace: dict, name: str, data: dict, safe: bool = True):
    trace["steps"].append({"name": name, "data": data, "safe": safe, "at": datetime.utcnow().isoformat()})

def end_trace(trace: dict):
    trace["latency_ms"] = int((time.time() - trace["start"])*1000)
    # estimate cost: 0.001 per 100 tokens
    ti=trace.get("tokens_in",0)
    to=trace.get("tokens_out",0)
    trace["cost_usd"] = round((ti+to)/1000*0.001,6)
    # tokens_out from response length if available
    return trace

def get_traces():
    return _traces[-50:]

def add_tokens_out(trace: dict, text: str):
    trace["tokens_out"] = len(text.split())
