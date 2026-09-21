import os

def _llm_plan(user_input: str, intent: str, has_order_id: bool):
    try:
        import google.generativeai as genai
        if not os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")=="your_gemini_api_key_here":
            return None
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model=genai.GenerativeModel(os.getenv("LLM_MODEL","gemini-1.5-flash"))
        prompt=f"""You are a support agent planner. Given intent={intent}, has_order_id={has_order_id}, user says: "{user_input}"
Return a JSON list of 3-6 steps like ["identify order", "get_order_status", "retrieve shipping-policy", "reason", "respond"].
Keep steps concise, include tool names where relevant."""
        resp=model.generate_content(prompt)
        text=resp.text.strip()
        # try parse
        import json, re
        m=re.search(r"\[.*\]", text, re.S)
        if m:
            return json.loads(m.group(0))
        return None
    except Exception as e:
        return None

def plan(intent: str, has_order_id: bool, user_input: str=""):
    # try LLM first
    if user_input:
        llm=_llm_plan(user_input, intent, has_order_id)
        if llm: return llm
    # fallback deterministic
    if "cancel" in intent.lower():
        return ["identify order", "get_order", "check cancellation policy", "policy engine", "ask confirmation if needed", "cancel_order or create ticket"]
    if "refund" in intent.lower():
        return ["identify order/refund", "get_refund_status or check eligibility", "retrieve refund policy", "explain"]
    if "order" in intent.lower() or "ship" in intent.lower() or "delivery" in intent.lower() or "address" in intent.lower():
        return ["identify order", "get_order_status", "retrieve shipping/cancellation policy", "reason over results", "respond"]
    if "product" in intent.lower() or "warranty" in intent.lower():
        return ["search product docs", "retrieve warranty policy", "explain"]
    if "account" in intent.lower():
        return ["verify_customer if needed", "get_account", "reason", "respond"]
    return ["understand request", "retrieve relevant knowledge", "select tools", "reason", "respond"]
