from app.guardrails.actions import check_action
def eval_tool_selection(tool: str, args: dict, should_allow: bool):
    res=check_action(tool, args, customer_id="C102")
    return {"correct": res.get("allow")==should_allow, "result": res}
