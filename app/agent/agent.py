"""DEPRECATED - Use app.agent.graph.run_graph instead. Kept for reference only.
This legacy implementation is NOT used in production. The canonical agent is LangGraph (graph.py).
It is retained only for backward compat in tests but should not be called via API (use_legacy removed).
"""
import warnings
warnings.warn("app.agent.agent is deprecated, use app.agent.graph", DeprecationWarning)

from app.agent.graph import run_graph as _run_graph

def run_agent(user_input: str, customer_id: str="C102", confirm: bool=False):
    # Delegates to canonical graph for backward compat
    return _run_graph(user_input, customer_id=customer_id, confirm=confirm)

def extract_order_id(text: str):
    from app.agent.router import extract_order_id as _ex
    return _ex(text)

def detect_intent(text: str):
    from app.agent.graph import detect_intent as _di
    return _di(text)

def call_gemini(prompt: str, context: str):
    from app.agent.graph import call_gemini as _cg
    return _cg(prompt, context)
