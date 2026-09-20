"""Agent trajectory evaluation placeholder"""
def eval_agent_trajectory(trace: dict):
    return {"has_tool_calls": len([s for s in trace.get("steps",[]) if "Tool" in s["name"]])>0, "policy_compliant": True}
