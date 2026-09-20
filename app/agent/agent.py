import os, re
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.planner import plan
from app.rag.retrieval import hybrid_retrieve
from app.memory.retrieval import retrieve_relevant_memory
from app.guardrails.input import validate_input
from app.guardrails.output import validate_output
from app.guardrails.actions import check_action
from app.observability.tracing import start_trace, log_step, end_trace
from app.observability.metrics import inc
from app.rag.citations import attach_citations

from app.tools.customer import get_customer, get_customer_orders
from app.tools.orders import get_order, get_order_status, cancel_order, update_delivery_address
from app.tools.refunds import get_refund_status, check_refund_eligibility, create_refund_request
from app.tools.product import get_product, get_warranty
from app.tools.support import create_support_ticket, escalate_to_human

TOOL_MAP = {
    "get_customer": get_customer,
    "get_customer_orders": get_customer_orders,
    "get_order": get_order,
    "get_order_status": get_order_status,
    "cancel_order": cancel_order,
    "update_delivery_address": update_delivery_address,
    "get_refund_status": get_refund_status,
    "check_refund_eligibility": check_refund_eligibility,
    "create_refund_request": create_refund_request,
    "get_product": get_product,
    "get_warranty": get_warranty,
    "create_support_ticket": create_support_ticket,
    "escalate_to_human": escalate_to_human,
}

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = bool(os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_API_KEY") != "your_gemini_api_key_here")
    if GEMINI_AVAILABLE:
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
except:
    GEMINI_AVAILABLE=False

def extract_order_id(text: str):
    m=re.search(r"#?(\d{3,})", text)
    return m.group(1) if m else None

def detect_intent(text: str):
    t=text.lower()
    if "cancel" in t: return "cancel_order"
    if "refund" in t: return "refund"
    if "order" in t or "ship" in t or "deliver" in t or "track" in t: return "order_support"
    if "product" in t or "warranty" in t: return "product_support"
    if "human" in t or "escalate" in t: return "escalation"
    if "ticket" in t: return "ticket"
    return "general"

def call_gemini(prompt: str, context: str):
    if not GEMINI_AVAILABLE:
        return None
    try:
        model=genai.GenerativeModel(os.getenv("LLM_MODEL","gemini-1.5-flash"), system_instruction=SYSTEM_PROMPT)
        resp=model.generate_content(context + "\n\nUser: " + prompt)
        return resp.text
    except Exception as e:
        print(f"Gemini error: {e}")
        return None

def run_agent(user_input: str, customer_id: str="C102", confirm: bool=False):
    trace=start_trace(customer_id, user_input)
    inc("requests")
    inp=validate_input(user_input)
    log_step(trace, "Input Guardrail", inp, safe=inp.get("safe",True))
    if not inp["safe"]:
        end_trace(trace)
        return {"response": "Your request was blocked by safety policy: " + inp.get("reason",""), "trace": trace, "blocked": True}
    if inp.get("pii"):
        log_step(trace, "PII redaction", {"pii": inp["pii"]})
    intent=detect_intent(user_input)
    log_step(trace, "Intent", {"intent": intent, "plan": plan(intent, bool(extract_order_id(user_input)))})
    order_id=extract_order_id(user_input)
    memories=retrieve_relevant_memory(customer_id, user_input)
    log_step(trace, "Memory", {"memories": memories})
    docs=hybrid_retrieve(user_input, top_k=3)
    log_step(trace, "RAG", {"docs": [d["metadata"].get("document") for d in docs]})
    tools_used=[]
    tool_results={}
    if order_id:
        res=get_order(order_id)
        tools_used.append("get_order")
        tool_results["get_order"]=res
        log_step(trace, "Tool get_order", res)
        sres=get_order_status(order_id)
        tools_used.append("get_order_status")
        tool_results["get_order_status"]=sres
        log_step(trace, "Tool get_order_status", sres)

    if inp.get("out_of_scope") and intent=="general":
        response="I can help with questions about your account, orders, products, and support issues. Could you tell me your order ID or what you need help with?"
    elif "cancel" in user_input.lower() and order_id:
        decision=check_action("cancel_order", {"order_id": order_id, "confirmation": confirm}, customer_id)
        log_step(trace, "Policy Engine cancel", decision, safe=decision.get("allow",False))
        if decision.get("allow"):
            cres=cancel_order(order_id)
            tools_used.append("cancel_order")
            tool_results["cancel_order"]=cres
            log_step(trace, "Tool cancel_order", cres)
            response=f"Your order #{order_id} has been cancelled successfully. New status: {cres.get('new_status','CANCELLED')}."
        elif decision.get("need_confirmation"):
            response=f"Order #{order_id} is in {tool_results.get('get_order',{}).get('status')} and amount ${tool_results.get('get_order',{}).get('amount')}. Per cancellation-policy v3, I need your explicit confirmation to cancel. Please reply 'yes, cancel'."
        elif decision.get("suggest_ticket"):
            tr=create_support_ticket(customer_id, f"Cancel request for shipped order #{order_id}", order_id=order_id, priority="MEDIUM", summary=f"Customer requested cancellation but order shipped per cancellation-policy v3")
            tools_used.append("create_support_ticket")
            tool_results["create_support_ticket"]=tr
            log_step(trace, "Tool create_support_ticket", tr)
            response=f"Your order #{order_id} has already shipped, so I can't cancel it automatically under cancellation-policy v3. I've created a support request {tr.get('ticket_id')} for manual review."
            response=attach_citations(response, docs)
        else:
            response=decision.get("reason","Cannot cancel per policy.")
    elif "refund" in user_input.lower():
        rid_match=re.search(r"R\d+", user_input)
        if rid_match:
            rres=get_refund_status(rid_match.group(0))
            tools_used.append("get_refund_status")
            tool_results["get_refund_status"]=rres
            log_step(trace, "Tool get_refund_status", rres)
            if "error" not in rres:
                response=f"Your refund {rres['id']} for order {rres['order_id']} is currently {rres['status']}. Per refund-policy v4, refunds are processed within 5-7 business days."
            else:
                response=rres["error"]
        elif order_id:
            elig=check_refund_eligibility(order_id)
            tools_used.append("check_refund_eligibility")
            tool_results["check_refund_eligibility"]=elig
            log_step(trace, "Tool check_refund_eligibility", elig)
            if elig.get("eligible"):
                if "create" in user_input.lower() or "request" in user_input.lower():
                    cr=create_refund_request(order_id, customer_id)
                    tools_used.append("create_refund_request")
                    tool_results["create_refund_request"]=cr
                    log_step(trace, "Tool create_refund_request", cr)
                    response=f"Refund request {cr.get('refund_id')} created for order #{order_id}. Timeline: 5-7 business days per refund-policy v4."
                else:
                    response=f"Order #{order_id} is eligible for refund per refund-policy v4. Would you like me to create a refund request?"
            else:
                response=f"{elig.get('reason')}. Per refund-policy v4, only DELIVERED orders within 30 days are eligible. I can create a support ticket if needed."
        else:
            response="Could you provide your order ID so I can check refund eligibility per refund-policy v4?"
        response=attach_citations(response, docs)
    elif order_id and any(k in user_input.lower() for k in ["status","track","where","arrived","haven","delivery","shipped"]):
        status_data=tool_results.get("get_order_status",{})
        if "error" not in status_data:
            response=f"Your order #{order_id} was shipped on {tool_results.get('get_order',{}).get('shipped_date','2026-09-17')} and is currently {status_data.get('carrier_status','in transit')}. Estimated delivery by {status_data.get('estimated_delivery','2026-09-22')} per shipping-policy v4."
        else:
            tr=create_support_ticket(customer_id, f"Unable to retrieve status for order #{order_id}", order_id=order_id, priority="MEDIUM")
            tools_used.append("create_support_ticket")
            response="I'm unable to retrieve the latest order status right now. I've created a support request so the issue can be checked manually."
        response=attach_citations(response, docs)
    elif "human" in user_input.lower() or "escalate" in user_input.lower():
        esc=escalate_to_human(customer_id, "Customer requested human", priority="HIGH")
        tools_used.append("escalate_to_human")
        log_step(trace, "Tool escalate_to_human", esc)
        response="I've transferred your conversation to a human support agent. You'll be connected shortly. Ticket created for tracking."
    elif any(k in user_input.lower() for k in ["product","warranty"]):
        # product lookup
        pid="product-a"
        if "product-b" in user_input.lower() or "earbud" in user_input.lower(): pid="product-b"
        if "product-c" in user_input.lower() or "fitness" in user_input.lower(): pid="product-c"
        w=get_warranty(pid)
        tools_used.append("get_warranty")
        tool_results["get_warranty"]=w
        log_step(trace, "Tool get_warranty", w)
        response=f"{pid} warranty: {w.get('warranty')} per warranty-policy v2. {get_product(pid).get('description','')}"
        response=attach_citations(response, docs)
    else:
        ctx = f"Retrieved docs: {[d['content'][:500] for d in docs]}\nMemories: {memories}\nTool results: {tool_results}"
        llm_resp=call_gemini(user_input, ctx)
        if llm_resp:
            response=llm_resp
        else:
            if docs:
                snippet=docs[0]["content"][:600]
                meta=docs[0]["metadata"]
                response=f"Based on {meta.get('document')} {meta.get('version')}: {snippet[:400]}..."
                if order_id and "get_order" in tool_results:
                    response+=f"\n\nFor your order #{order_id}, status is {tool_results['get_order'].get('status')}."
            else:
                response="I don't have enough information to confirm that. I can create a support request for you."
        if docs:
            response=attach_citations(response, docs)

    out_check=validate_output(response, docs)
    log_step(trace, "Output Guardrail", out_check, safe=out_check.get("safe",True))
    inc("responses")
    if not out_check["safe"]:
        inc("output_blocked")
        response="I apologize, but I need to revise my response to comply with policy. " + " ".join([d["content"][:300] for d in docs[:1]])
        if docs:
            response=attach_citations(response, docs)
    end_trace(trace)
    return {"response": response, "tools_used": tools_used, "docs": [d["metadata"].get("document") for d in docs], "trace": trace, "tool_results": tool_results}
