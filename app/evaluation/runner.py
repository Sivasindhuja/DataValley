import json, pathlib, time
from app.agent.graph import run_graph
from app.evaluation.retrieval import eval_retrieval
from app.evaluation.tools import eval_tool_selection
from app.evaluation.safety import eval_safety
from app.tools.seed import seed
from app.guardrails.output import validate_output

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
        # detect unnecessary tools
        extra_tools=len([t for t in tools_used if t not in exp_tools]) if exp_tools else 0
        expected=c.get("expected_behavior") or c.get("expected",{})
        blocked_ok=True
        if isinstance(expected, dict) and "action" in expected:
            if expected.get("action")=="BLOCK":
                blocked_ok=out.get("blocked",False)==True
            elif expected.get("action")=="ALLOW":
                blocked_ok=out.get("blocked",False)==False
        # retrieval check - soft, not fail overall unless strict (spec §17)
        retrieval_ok=True
        strict=c.get("strict_retrieval", False)
        # also check expected_policy always (not strict) for metrics
        retr_metrics=None
        if c.get("expected_policy"):
            docs=out.get("docs",[])
            hit=c["expected_policy"] in docs or any(c["expected_policy"] in d for d in docs)
            retr_metrics=eval_retrieval(inp, c["expected_policy"], top_k=3)
            retrieval_ok=hit if strict else True  # only enforce if strict
        # output guardrail / groundedness (spec §17)
        grounded_ok=True
        if out.get("response"):
            # if expected policy, response should be grounded + cite version
            if c.get("expected_policy") and "policy" in out["response"].lower():
                grounded_ok="v" in out["response"]
        # policy compliance: check that high-risk denied correctly
        policy_ok=True
        if c.get("id","").startswith("cancel") and "123" in inp and "SHIPPED" in str(out.get("tool_results")):
            # should not have cancel_order success
            policy_ok="cancel_order" not in tools_used or "create_support_ticket" in tools_used

        passed=tool_ok and blocked_ok and grounded_ok and policy_ok
        if strict:
            passed=passed and retrieval_ok
        results.append({"id":c.get("id"), "passed": passed, "tool_ok": tool_ok, "extra_tools": extra_tools, "retrieval_ok": retrieval_ok, "retrieval_metrics": retr_metrics, "blocked_ok": blocked_ok, "grounded_ok": grounded_ok, "policy_ok": policy_ok, "response": out["response"][:400], "tools_used": tools_used, "docs": out["docs"]})
        time.sleep(0.02)
    return results

def evaluate_all(reset_each=False):
    import glob
    all_results={}
    totals={"passed":0,"total":0}
    retr_scores=[]
    tool_scores=[]
    for fp in glob.glob("evals/**/*.json", recursive=True):
        try:
            res=evaluate_dataset(fp, reset_db_each_case=reset_each)
            all_results[fp]=res
            for r in res:
                if isinstance(r, dict) and "passed" in r:
                    totals["total"]+=1
                    if r["passed"]: totals["passed"]+=1
                    if r.get("retrieval_metrics"): retr_scores.append(r["retrieval_metrics"])
                    tool_scores.append(1 if r.get("tool_ok") else 0)
        except Exception as e:
            import traceback
            all_results[fp]={"error": str(e), "trace": traceback.format_exc()}
    # aggregate metrics per spec §17-20 (RAG, tool, safety)
    all_results["_summary"]={
        "task_success": round(totals["passed"]/totals["total"]*100,1) if totals["total"] else 0,
        "total_cases": totals["total"],
        "passed": totals["passed"],
        "tool_accuracy": round(sum(tool_scores)/len(tool_scores)*100,1) if tool_scores else 0,
        "retrieval": {
            "avg_recall@3": round(sum(r["recall@k"] for r in retr_scores)/len(retr_scores),3) if retr_scores else 0,
            "avg_mrr": round(sum(r["mrr"] for r in retr_scores)/len(retr_scores),3) if retr_scores else 0,
            "avg_ndcg": round(sum(r["ndcg"] for r in retr_scores)/len(retr_scores),3) if retr_scores else 0,
        },
        "guardrail_accuracy": "see safety eval",
        "safety": eval_safety()
    }
    return all_results

if __name__=="__main__":
    import json as j
    print(j.dumps(evaluate_all(reset_each=True), indent=2))
