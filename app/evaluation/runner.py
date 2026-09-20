import json, pathlib, time
from app.agent.graph import run_graph
from app.evaluation.retrieval import eval_retrieval
from app.evaluation.tools import eval_tool_selection
from app.evaluation.safety import eval_safety
from app.tools.seed import seed

def evaluate_dataset(path: str, reset_db_each_case=False):
    cases=json.loads(pathlib.Path(path).read_text())
    results=[]
    for c in cases:
        if reset_db_each_case:
            try: seed()
            except: pass
        inp=c.get("input") or c.get("query") or ""
        cid=c.get("customer_id","C102")
        confirm=c.get("confirm",False)
        out=run_graph(inp, customer_id=cid, confirm=confirm)
        exp_tools=c.get("expected_tools",[])
        tools_used=out.get("tools_used",[])
        tool_ok=all(t in tools_used for t in exp_tools) if exp_tools else True
        expected=c.get("expected_behavior") or c.get("expected",{})
        blocked_ok=True
        if isinstance(expected, dict) and "action" in expected:
            if expected.get("action")=="BLOCK":
                blocked_ok=out.get("blocked",False)==True
            elif expected.get("action")=="ALLOW":
                blocked_ok=out.get("blocked",False)==False
        # retrieval check - soft, not fail overall unless strict
        retrieval_ok=True
        strict=c.get("strict_retrieval", False)
        if strict and c.get("expected_policy"):
            docs=out.get("docs",[])
            retrieval_ok=c["expected_policy"] in docs or any(c["expected_policy"] in d for d in docs)
        passed=tool_ok and blocked_ok
        if strict:
            passed=passed and retrieval_ok
        results.append({"id":c.get("id"), "passed": passed, "tool_ok": tool_ok, "retrieval_ok": retrieval_ok, "blocked_ok": blocked_ok, "response": out["response"][:300], "tools_used": tools_used, "docs": out["docs"]})
        time.sleep(0.02)
    return results

def evaluate_all(reset_each=False):
    import glob
    all_results={}
    for fp in glob.glob("evals/**/*.json", recursive=True):
        try:
            all_results[fp]=evaluate_dataset(fp, reset_db_each_case=reset_each)
        except Exception as e:
            import traceback
            all_results[fp]={"error": str(e), "trace": traceback.format_exc()}
    return all_results

if __name__=="__main__":
    import json as j
    print(j.dumps(evaluate_all(reset_each=True), indent=2))
