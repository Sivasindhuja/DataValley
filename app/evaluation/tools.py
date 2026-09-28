from app.policies.engine import evaluate_policy
from app.auth.models import AuthContext
def eval_tool_selection(tool: str, args: dict, should_allow: bool):
    auth = AuthContext(authenticated=True, user_id="C102", customer_id="C102", roles=["customer"])
    dec = evaluate_policy(tool, args, auth)
    d = dec.to_dict()
    # map to legacy shape for compatibility
    res = {"allow": d["allowed"], "allowed": d["allowed"], **d}
    return {"correct": res.get("allow")==should_allow, "result": res}
