from collections import Counter
_metrics = Counter()
def inc(key: str, n=1):
    _metrics[key]+=n
def get_metrics():
    # compute derived metrics from traces
    from app.observability.tracing import get_traces
    traces=get_traces(limit=200)
    total=len(traces) if traces else 0
    denom = total if total else 1
    blocked=sum(1 for t in traces if any("Input Guardrail"==s["name"] and not s["safe"] for s in t["steps"]))
    escalated=sum(1 for t in traces if any("escalate" in s["name"].lower() or "Escalation" in s["name"] for s in t["steps"]) or any("create_support_ticket" in str(s.get("data")) for s in t["steps"] if "Tool" in s["name"]))
    pii_blocked=sum(1 for t in traces if any("PII" in s["name"] for s in t["steps"]))
    output_blocked=sum(1 for t in traces if any("Output Guardrail" in s["name"] and not s["safe"] for s in t["steps"]))
    # count failed tool calls robustly (str or dict)
    failed_tools=0
    for t in traces:
        for s in t["steps"]:
            if "Tool" in s["name"]:
                d=s.get("data")
                if isinstance(d, dict) and "error" in str(d).lower():
                    failed_tools+=1
                elif isinstance(d, str) and "error" in d.lower():
                    failed_tools+=1
    avg_latency=sum(t.get("latency_ms",0) for t in traces)/denom if total else 0
    total_tokens=sum(t.get("tokens_in",0)+t.get("tokens_out",0) for t in traces)
    base=dict(_metrics)
    base.update({
        "total_traces": total,
        "avg_latency_ms": round(avg_latency,1),
        "blocked_injections": blocked,
        "escalations": escalated,
        "pii_detections": pii_blocked,
        "output_blocked": output_blocked,
        "failed_tool_calls": failed_tools,
        "total_tokens": total_tokens,
        "avg_tokens": round(total_tokens/denom,1) if total else 0,
        "policy_compliance_rate": round(100 - (failed_tools/max(denom,1))*10,1) if total else None,
        "guardrail_accuracy": round(100 - (output_blocked/max(denom,1))*100,1) if total and output_blocked else (100.0 if total else None),
    })
    return base
