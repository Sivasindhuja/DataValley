import json, pathlib
from app.agent.agent import run_agent

def evaluate(dataset_path: str):
    cases=json.loads(pathlib.Path(dataset_path).read_text())
    results=[]
    for c in cases:
        out=run_agent(c["input"], customer_id=c.get("customer_id","C102"))
        passed = all(tool in str(out.get("tools_used",[])) for tool in c.get("expected_tools",[]))
        results.append({"id": c["id"], "passed": passed, "output": out})
    return results
