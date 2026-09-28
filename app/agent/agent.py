"""Deprecated alias: use app.agent.graph.run_graph. Kept for backward compat with tests/legacy imports."""
from app.agent.graph import run_graph

def run_agent(user_input: str, customer_id: str = "C102", confirm: bool = False, auth_context=None):
    return run_graph(user_input, customer_id=customer_id, confirm=confirm, auth_context=auth_context)

__all__ = ["run_agent", "run_graph"]
