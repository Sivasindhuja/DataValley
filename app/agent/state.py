from typing import TypedDict, List, Dict, Annotated, Optional
from langgraph.graph import add_messages

class AgentState(TypedDict, total=False):
    messages: Annotated[List[Dict], add_messages]
    customer_id: Optional[str]
    order_id: Optional[str]
    intent: Optional[str]
    plan_steps: List[str]
    tools_used: List[str]
    tool_results: Dict
    retrieved_docs: List[Dict]
    memories: List[Dict]
    guardrail_decisions: List[Dict]
    trace: Dict
    user_input: str
    confirm: bool
    response: str
    blocked: bool
    needs_confirmation: bool
    suggest_ticket: bool
    escalate: bool
    retry_count: int
