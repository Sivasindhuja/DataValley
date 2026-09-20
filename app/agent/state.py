from typing import TypedDict, List, Dict, Annotated, Optional
from langgraph.graph import add_messages

class AgentState(TypedDict):
    messages: Annotated[List[Dict], add_messages]
    customer_id: Optional[str]
    order_id: Optional[str]
    intent: Optional[str]
    tools_used: List[str]
    retrieved_docs: List[Dict]
    guardrail_decisions: List[Dict]
    trace: Dict
