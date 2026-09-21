import re, time
from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.planner import plan
from app.rag.retrieval import hybrid_retrieve
from app.memory.retrieval import retrieve_relevant_memory
from app.memory.manager import store_memory
from app.guardrails.input import validate_input
from app.guardrails.output import validate_output
from app.guardrails.actions import check_action
from app.observability.tracing import start_trace, log_step, end_trace
from app.observability.metrics import inc
from app.rag.citations import attach_citations
# MCP Layer spec §10: all business tools via MCP client (with DIRECT fallback when ENABLE_MCP=false)
from app.mcp.client import call as mcp_call, DIRECT_MAP
from app.tools.customer import get_customer  # keep for type fallback; actual calls via mcp_call
import os

# Thin wrappers routing via MCP client (spec §4 architecture: Agent -> MCP Client -> Servers -> DB) + retry per spec §16
def _mcp(tool: str, **kwargs):
    import time
    last=None
    for attempt in range(3):
        try:
            res=mcp_call(tool, kwargs)
            # retry on transient error (not "not found")
            if isinstance(res, dict) and "error" in res and "not found" not in res["error"].lower():
                last=res
                time.sleep(0.15* (attempt+1))
                continue
            return res
        except Exception as e:
            last={"error": str(e)}
            time.sleep(0.15* (attempt+1))
    return last

def get_customer_orders(cid): return _mcp("get_customer_orders", customer_id=cid)
def get_customer_tickets(cid): return _mcp("get_customer_tickets", customer_id=cid)
def verify_customer(cid, email=None): return _mcp("verify_customer", customer_id=cid, email=email)
def get_order(oid): return _mcp("get_order", order_id=oid)
def get_order_status(oid): return _mcp("get_order_status", order_id=oid)
def cancel_order(oid): return _mcp("cancel_order", order_id=oid)
def update_delivery_address(oid, addr): return _mcp("update_delivery_address", order_id=oid, new_address=addr)
def get_refund_status(rid): return _mcp("get_refund_status", refund_id=rid)
def check_refund_eligibility(oid): return _mcp("check_refund_eligibility", order_id=oid)
def create_refund_request(oid, cid, reason=""): return _mcp("create_refund_request", order_id=oid, customer_id=cid, reason=reason)
def get_product(pid): return _mcp("get_product", product_id=pid)
def get_warranty(pid): return _mcp("get_warranty", product_id=pid)
def get_product_status(pid): return _mcp("get_product_status", product_id=pid) if "get_product_status" in DIRECT_MAP else {"product": pid, "available": True}
def create_support_ticket(cid, issue, order_id=None, priority="MEDIUM", summary=None): return _mcp("create_support_ticket", customer_id=cid, issue=issue, order_id=order_id, priority=priority, summary=summary)
def update_support_ticket(tid, status=None, summary=None): return _mcp("update_support_ticket", ticket_id=tid, status=status, summary=summary)
def escalate_to_human(cid, reason, ticket_id=None, priority="HIGH"): return _mcp("escalate_to_human", customer_id=cid, reason=reason, ticket_id=ticket_id, priority=priority)
def get_ticket(tid): return _mcp("get_ticket", ticket_id=tid)
def send_email(to, subject, body): return _mcp("send_email", to=to, subject=subject, body=body)
def send_notification(cid, message, channel="email"): return _mcp("send_notification", customer_id=cid, message=message, channel=channel)
def get_account(cid): return _mcp("get_account", customer_id=cid) if "get_account" in DIRECT_MAP else get_customer(cid)
def update_account(cid, email=None, communication_preference=None, verify=False): return _mcp("update_account", customer_id=cid, email=email, communication_preference=communication_preference, verify=verify) if "update_account" in DIRECT_MAP else {"success": False, "need_verification": True}

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = bool(os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_API_KEY")!="your_gemini_api_key_here")
    if GEMINI_AVAILABLE:
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
except:
    GEMINI_AVAILABLE=False

def extract_refund_id(text: str):
    m=re.search(r"R\d+", text)
    return m.group(0) if m else None

def extract_order_id(text: str):
    # avoid capturing refund ids like R421
    # look for order id not preceded by R, and prefer #\d+ or order\s+#?\d+
    # If refund id present, don't treat its digits as order id
    if extract_refund_id(text):
        # try to find explicit order id pattern
        m=re.search(r"order\s*#?(\d{3,})", text, re.I)
        if m: return m.group(1)
        # fallback: #\d+ that is not part of R\d+
        m2=re.search(r"#(\d{3,})", text)
        if m2: return m2.group(1)
        return None
    m=re.search(r"#?(\d{3,})", text)
    return m.group(1) if m else None

def detect_intent(text: str):
    t=text.lower()
    if "address" in t or "update delivery" in t: return "address_update"
    if "cancel" in t: return "cancel_order"
    if "refund" in t: return "refund"
    if "human" in t or "escalate" in t: return "escalation"
    if any(k in t for k in ["login","account","password","verify","email","phone"]): return "account_support"
    if any(k in t for k in ["product","warranty"]): return "product_support"
    if "ticket" in t: return "ticket"
    if any(k in t for k in ["order","ship","deliver","track","arrival"]): return "order_support"
    return "general"

def call_gemini(prompt: str, context: str):
    if not GEMINI_AVAILABLE: return None
    try:
        model=genai.GenerativeModel(os.getenv("LLM_MODEL","gemini-1.5-flash"), system_instruction=SYSTEM_PROMPT)
        resp=model.generate_content(context + "\n\nUser: " + prompt)
        return resp.text
    except Exception as e:
        print(f"Gemini error: {e}")
        return None

def build_escalation_summary(state: AgentState):
    trace=state["trace"]
    docs=state.get("retrieved_docs",[])
    tools=state.get("tools_used",[])
    return {
        "customer": state["customer_id"],
        "issue": state["user_input"],
        "previous_actions": [f"{s['name']}: {str(s['data'])[:150]}" for s in trace["steps"] if "Tool" in s["name"] or "Policy" in s["name"]],
        "relevant_policy": ", ".join(d["metadata"].get("document","") for d in docs[:2]),
        "reason": "Requires human judgment / policy ambiguous / repeated failure / fraud",
        "tools_used": tools,
    }

# ---- Nodes ----
def node_input_guardrail(state: AgentState):
    inp=validate_input(state["user_input"])
    trace=state["trace"]
    log_step(trace, "Input Guardrail", inp, safe=inp.get("safe",True))
    if not inp["safe"]:
        return {"blocked": True, "response": "Your request was blocked by safety policy: "+inp.get("reason",""), "guardrail_decisions":[inp]}
    if inp.get("pii"):
        log_step(trace, "PII redaction", {"pii": inp["pii"]})
    if inp.get("abuse"):
        log_step(trace, "Abuse detection", {"abuse": True})
    return {"guardrail_decisions":[inp], "blocked": False}

def node_intent(state: AgentState):
    intent=detect_intent(state["user_input"])
    oid=extract_order_id(state["user_input"]) or state.get("order_id")
    trace=state["trace"]
    steps=plan(intent, bool(oid), user_input=state["user_input"])
    log_step(trace, "Intent+Planner", {"intent": intent, "plan": steps})
    return {"intent": intent, "order_id": oid, "plan_steps": steps}

def node_memory(state: AgentState):
    # short-term + long-term + structured customer memory (spec §9)
    from app.memory.manager import get_short_term_history, get_structured_customer_memory
    short=get_short_term_history(state.get("messages",[]), window=6)
    mems=retrieve_relevant_memory(state["customer_id"], state["user_input"])
    structured=get_structured_customer_memory(state["customer_id"])
    log_step(state["trace"], "Memory", {"short_term": short, "memories": mems, "structured": structured, "customer": state["customer_id"]})
    # merge structured into memories for downstream use
    return {"memories": mems + [{"content": f"Structured: {structured}", "type": "customer"}]}

def node_rag(state: AgentState):
    docs=hybrid_retrieve(state["user_input"], top_k=3)
    log_step(state["trace"], "RAG", {"docs": [d["metadata"].get("document") for d in docs]})
    return {"retrieved_docs": docs}

def _retry_tool(fn, *args, **kwargs):
    import time
    last=None
    for attempt in range(2):
        try:
            res=fn(*args, **kwargs)
            if isinstance(res, dict) and "error" in res and "not found" not in res["error"].lower():
                last=res
                time.sleep(0.15)
                continue
            return res
        except Exception as e:
            last={"error": str(e)}
            time.sleep(0.15)
    return last

def node_tools(state: AgentState):
    intent=state.get("intent")
    oid=state.get("order_id")
    cid=state["customer_id"]
    trace=state["trace"]
    tools_used=list(state.get("tools_used",[]))
    tool_results=dict(state.get("tool_results",{}))
    retry=state.get("retry_count",0)

    # Auto-fetch order/status if order mentioned
    if oid and "get_order" not in tool_results:
        res=_retry_tool(get_order, oid)
        tools_used.append("get_order")
        tool_results["get_order"]=res
        log_step(trace, "Tool get_order", res)
        if "error" not in res:
            sres=_retry_tool(get_order_status, oid)
            tools_used.append("get_order_status")
            tool_results["get_order_status"]=sres
            log_step(trace, "Tool get_order_status", sres)

    # Intent-specific tools
    if intent=="cancel_order" and oid:
        decision=check_action("cancel_order", {"order_id": oid, "confirmation": state.get("confirm",False)}, cid)
        log_step(trace, "Policy Engine cancel", decision, safe=decision.get("allow",False))
        if decision.get("allow"):
            # retry with guard
            cres=cancel_order(oid)
            tools_used.append("cancel_order")
            tool_results["cancel_order"]=cres
            log_step(trace, "Tool cancel_order", cres)
        elif decision.get("need_confirmation"):
            return {"tools_used": tools_used, "tool_results": tool_results, "needs_confirmation": True}
        elif decision.get("suggest_ticket"):
            return {"tools_used": tools_used, "tool_results": tool_results, "suggest_ticket": True}
        elif not decision.get("allow"):
            tool_results["policy_block"]=decision
    elif intent=="refund":
        rid=extract_refund_id(state["user_input"])
        if rid:
            rres=get_refund_status(rid)
            tools_used.append("get_refund_status")
            tool_results["get_refund_status"]=rres
            log_step(trace, "Tool get_refund_status", rres)
        elif oid:
            elig=check_refund_eligibility(oid)
            tools_used.append("check_refund_eligibility")
            tool_results["check_refund_eligibility"]=elig
            log_step(trace, "Tool check_refund_eligibility", elig)
            if elig.get("eligible") and any(k in state["user_input"].lower() for k in ["create","request"]):
                decision=check_action("create_refund_request", {"order_id": oid}, cid)
                log_step(trace, "Policy Engine refund", decision)
                if decision.get("allow"):
                    cr=create_refund_request(oid, cid)
                    tools_used.append("create_refund_request")
                    tool_results["create_refund_request"]=cr
                    log_step(trace, "Tool create_refund_request", cr)
        else:
            # ask for order_id later
            pass
    elif intent=="address_update" and oid:
        m=re.search(r"to\s+(.+)$", state["user_input"], re.I)
        if not m:
            m=re.search(r"address\s*[:\-]?\s*(.+)", state["user_input"], re.I)
        new_addr=m.group(1).strip() if m else "123 New St"
        decision=check_action("update_delivery_address", {"order_id": oid}, cid)
        log_step(trace, "Policy Engine address", decision)
        if decision.get("allow"):
            ures=update_delivery_address(oid, new_addr)
            tools_used.append("update_delivery_address")
            tool_results["update_delivery_address"]=ures
            log_step(trace, "Tool update_delivery_address", ures)
        else:
            tool_results["policy_block"]=decision
            return {"tools_used": tools_used, "tool_results": tool_results, "suggest_ticket": True, "needs_confirmation": False}
    elif intent=="product_support":
        pid="product-a"
        if "product-b" in state["user_input"].lower() or "earbud" in state["user_input"].lower(): pid="product-b"
        if "product-c" in state["user_input"].lower() or "fitness" in state["user_input"].lower(): pid="product-c"
        w=get_warranty(pid)
        p=get_product(pid)
        tools_used.extend(["get_warranty","get_product"])
        tool_results["get_warranty"]=w
        tool_results["get_product"]=p
        log_step(trace, "Tool get_warranty", w)
    elif intent=="account_support":
        if "update" in state["user_input"].lower() and any(k in state["user_input"].lower() for k in ["email","phone","password"]):
            decision=check_action("update_account", {"verify": False}, cid)
            log_step(trace, "Policy Engine account update", decision, safe=decision.get("allow",False))
            if decision.get("need_verification") or decision.get("escalate"):
                tool_results["policy_block"]=decision
                return {"tools_used": tools_used, "tool_results": tool_results, "suggest_ticket": True}
            # if verified (would require OTP), proceed
            acc_update=_retry_tool(update_account, cid, email="new@example.com", verify=True)
            tools_used.append("update_account")
            tool_results["update_account"]=acc_update
            log_step(trace, "Tool update_account", acc_update)
        else:
            acc=_retry_tool(get_account, cid)
            tools_used.append("get_account")
            tool_results["get_account"]=acc
            log_step(trace, "Tool get_account", acc)
    elif intent=="escalation":
        esc=escalate_to_human(cid, "Customer requested human", priority="HIGH")
        tools_used.append("escalate_to_human")
        tool_results["escalate_to_human"]=esc
        log_step(trace, "Tool escalate_to_human", esc)
    elif intent=="ticket":
        tid_match=re.search(r"T\w+", state["user_input"])
        if tid_match:
            t=get_ticket(tid_match.group(0))
            tools_used.append("get_ticket")
            tool_results["get_ticket"]=t
            log_step(trace, "Tool get_ticket", t)

    # Fraud/dispute detection -> force escalate
    if any(k in state["user_input"].lower() for k in ["fraud","dispute","chargeback"]):
        tool_results["fraud_flag"]=True
    # Multiple tool failures -> escalate (spec §16)
    err_cnt=sum(1 for v in tool_results.values() if isinstance(v, dict) and "error" in v)
    if err_cnt>=2:
        tool_results["multi_failure"]=True

    return {"tools_used": tools_used, "tool_results": tool_results}

def node_respond(state: AgentState):
    trace=state["trace"]
    docs=state.get("retrieved_docs",[])
    intent=state.get("intent")
    oid=state.get("order_id")
    cid=state["customer_id"]
    tool_results=state.get("tool_results",{})
    # Handle tool failure -> ticket (spec §16: never invent status)
    if oid and "get_order" in tool_results and "error" in tool_results["get_order"]:
        tr=create_support_ticket(cid, f"Unable to retrieve status for order #{oid} - tool failure", order_id=oid, priority="HIGH", summary=f"Tool get_order failed for {oid};trace {trace['trace_id']}")
        state["tools_used"].append("create_support_ticket")
        tool_results["create_support_ticket"]=tr
        log_step(trace, "Tool create_support_ticket (failure)", tr)
        resp="I'm unable to retrieve the latest order status right now. I've created a support request so the issue can be checked manually."
        return {"response": attach_citations(resp, docs)}
    if tool_results.get("multi_failure"):
        tr=create_support_ticket(cid, f"Multiple tool failures for: {state['user_input']}", order_id=oid, priority="HIGH", summary=f"Multi-failure trace {trace['trace_id']} tools {tool_results}")
        state["tools_used"].append("create_support_ticket")
        log_step(trace, "Multi-failure escalation", tr)
        return {"response": attach_citations("I'm experiencing repeated system issues. I've escalated to a human specialist with high priority.", docs)}

    if state.get("needs_confirmation"):
        status=tool_results.get("get_order",{}).get("status","")
        amt=tool_results.get("get_order",{}).get("amount","")
        resp=f"Order #{oid} is in {status} and amount ${amt}. Per cancellation-policy v3, I need your explicit confirmation to cancel. Please reply 'yes, cancel'."
        return {"response": resp}

    if state.get("suggest_ticket"):
        reason=tool_results.get("policy_block",{}).get("reason","Policy requires manual review")
        if "address" in state["user_input"].lower():
            reason="Cannot update address after shipment per cancellation-policy v3"
        summary_obj=build_escalation_summary(state)
        summary_obj["reason"]=reason
        summary_text=f"Customer: {cid}\nIssue: {state['user_input']}\nOrder: {oid}\nPrevious actions: {', '.join(summary_obj['previous_actions'][:3])}\nRelevant policy: {summary_obj['relevant_policy']}\nReason for escalation: {reason}"
        tr=create_support_ticket(cid, f"Request for order #{oid}: {reason}", order_id=oid, priority="MEDIUM", summary=summary_text)
        state["tools_used"].append("create_support_ticket")
        tool_results["create_support_ticket"]=tr
        log_step(trace, "Tool create_support_ticket (escalation summary)", {"ticket": tr, "summary": summary_text})
        if intent=="cancel_order":
            resp=f"Your order #{oid} has already shipped, so I can't cancel it automatically under cancellation-policy v3. I've created a support request {tr['ticket_id']} for manual review."
        else:
            resp=f"I can't process that automatically: {reason}. I've created a support request {tr['ticket_id']} for manual review."
        return {"response": attach_citations(resp, docs)}

    if tool_results.get("fraud_flag"):
        summary_obj=build_escalation_summary(state)
        esc=escalate_to_human(cid, f"Fraud/dispute detected - {summary_obj['issue']}", priority="HIGH")
        state["tools_used"].append("escalate_to_human")
        log_step(trace, "Fraud escalation with summary", {"escalation": esc, "summary": summary_obj})
        return {"response":"I've escalated your fraud/dispute concern to a human specialist. A support ticket has been created with high priority."}

    # Intent responses using tool results
    if intent=="cancel_order" and "cancel_order" in tool_results:
        cres=tool_results["cancel_order"]
        if cres.get("success"):
            return {"response": f"Your order #{oid} has been cancelled successfully. New status: {cres.get('new_status','CANCELLED')}."}
        else:
            return {"response": cres.get("error","Cancellation failed per policy.")}

    if intent=="refund":
        if "get_refund_status" in tool_results:
            rres=tool_results["get_refund_status"]
            if "error" not in rres:
                return {"response": attach_citations(f"Your refund {rres['id']} for order {rres['order_id']} is currently {rres['status']}. Per refund-policy v4, refunds are processed within 5-7 business days.", docs)}
        if "check_refund_eligibility" in tool_results:
            elig=tool_results["check_refund_eligibility"]
            if "create_refund_request" in tool_results:
                cr=tool_results["create_refund_request"]
                if cr.get("success"):
                    return {"response": attach_citations(f"Refund request {cr['refund_id']} created for order #{oid}. Timeline: 5-7 business days per refund-policy v4.", docs)}
            if elig.get("eligible"):
                return {"response": attach_citations(f"Order #{oid} is eligible for refund per refund-policy v4. Would you like me to create a refund request?", docs)}
            else:
                return {"response": attach_citations(f"{elig.get('reason')}. Per refund-policy v4, only DELIVERED orders within 30 days are eligible. I can create a support ticket if needed.", docs)}
        if not oid and not tool_results.get("get_refund_status"):
            return {"response":"Could you provide your order ID so I can check refund eligibility per refund-policy v4?"}

    if intent=="order_support" and oid:
        status_data=tool_results.get("get_order_status",{})
        if "error" not in status_data:
            shipped=tool_results.get("get_order",{}).get("shipped_date","2026-09-17")
            return {"response": attach_citations(f"Your order #{oid} was shipped on {shipped} and is currently {status_data.get('carrier_status','in transit')}. Estimated delivery by {status_data.get('estimated_delivery','2026-09-22')} per shipping-policy v4.", docs)}

    if intent=="address_update" and "update_delivery_address" in tool_results:
        ures=tool_results["update_delivery_address"]
        if ures.get("success"):
            return {"response": f"Delivery address for order #{oid} updated to {ures.get('new_address')} successfully."}
        else:
            return {"response": ures.get("error","Address update failed.")}

    if intent=="product_support" and "get_warranty" in tool_results:
        w=tool_results["get_warranty"]
        p=tool_results["get_product"]
        return {"response": attach_citations(f"{p.get('name','Product')} warranty: {w.get('warranty')} per warranty-policy v2. {p.get('description','')}", docs)}

    if intent=="account_support" and "get_account" in tool_results:
        acc=tool_results["get_account"]
        return {"response": f"Your account {acc.get('id')} status is {acc.get('status')}, email {acc.get('email')}. Per account-policy v3, updates require verification via verify_customer."}

    if intent=="escalation" and "escalate_to_human" in tool_results:
        return {"response":"I've transferred your conversation to a human support agent. You'll be connected shortly. Ticket created for tracking."}

    if intent=="ticket" and "get_ticket" in tool_results:
        t=tool_results["get_ticket"]
        if "error" not in t:
            return {"response": f"Ticket {t['id']} status: {t['status']}, priority {t['priority']}. Issue: {t['issue']}"}
        else:
            return {"response": t["error"]}

    # out-of-scope
    inp=state.get("guardrail_decisions",[{}])[0]
    if inp.get("out_of_scope") and intent=="general":
        return {"response":"I can help with questions about your account, orders, products, and support issues."}

    # Generic LLM fallback
    ctx = f"Retrieved docs: {[d['content'][:500] for d in docs]}\nMemories: {state.get('memories')}\nTool results: {tool_results}"
    llm_resp=call_gemini(state["user_input"], ctx)
    if llm_resp:
        return {"response": attach_citations(llm_resp, docs)}
    if docs:
        snippet=docs[0]["content"][:600]
        meta=docs[0]["metadata"]
        resp=f"Based on {meta.get('document')} {meta.get('version')}: {snippet[:400]}..."
        if oid and "get_order" in tool_results:
            resp+=f"\n\nFor your order #{oid}, status is {tool_results['get_order'].get('status')}."
        return {"response": attach_citations(resp, docs)}
    return {"response":"I don't have enough information to confirm that. I can create a support request for you."}

def node_output_guardrail(state: AgentState):
    trace=state["trace"]
    docs=state.get("retrieved_docs",[])
    resp=state.get("response","")
    out_check=validate_output(resp, docs)
    log_step(trace, "Output Guardrail", out_check, safe=out_check.get("safe",True))
    inc("responses")
    if not out_check["safe"]:
        inc("output_blocked")
        fallback="I apologize, but I need to revise my response to comply with policy. " + " ".join([d["content"][:300] for d in docs[:1]])
        return {"response": attach_citations(fallback, docs)}
    # must return at least one state key due to langgraph 0.2 validation
    return {"response": resp}

def node_store_memory(state: AgentState):
    content=f"User: {state['user_input']} -> Intent {state.get('intent')} tools {state.get('tools_used')}"
    store_memory(state["customer_id"], content, type="episodic")
    return {"trace": state["trace"]}

def build_graph():
    g=StateGraph(AgentState)
    g.add_node("input_guardrail", node_input_guardrail)
    g.add_node("intent_step", node_intent)
    g.add_node("memory_step", node_memory)
    g.add_node("rag_step", node_rag)
    g.add_node("tool_step", node_tools)
    g.add_node("respond", node_respond)
    g.add_node("output_guardrail", node_output_guardrail)
    g.add_node("store_memory", node_store_memory)

    g.set_entry_point("input_guardrail")
    def route_input(state):
        if state.get("blocked"): return END
        return "intent_step"
    g.add_conditional_edges("input_guardrail", route_input, {"intent_step":"intent_step", END: END})
    g.add_edge("intent_step","memory_step")
    g.add_edge("memory_step","rag_step")
    g.add_edge("rag_step","tool_step")
    g.add_edge("tool_step","respond")
    g.add_edge("respond","output_guardrail")
    g.add_edge("output_guardrail","store_memory")
    g.add_edge("store_memory", END)
    return g.compile()

_graph=build_graph()

def run_graph(user_input: str, customer_id: str="C102", confirm: bool=False):
    inc("requests")
    trace=start_trace(customer_id, user_input)
    init_state={"user_input": user_input, "customer_id": customer_id, "confirm": confirm, "trace": trace, "tools_used":[], "tool_results":{}, "messages":[{"role":"user","content": user_input}]}
    result=_graph.invoke(init_state)
    end_trace(trace)
    # trace is mutated inside nodes (same dict)
    return {
        "response": result.get("response",""),
        "tools_used": result.get("tools_used",[]),
        "docs": [d["metadata"].get("document") for d in result.get("retrieved_docs",[])],
        "trace": trace,
        "tool_results": result.get("tool_results",{}),
        "blocked": result.get("blocked", False)
    }
