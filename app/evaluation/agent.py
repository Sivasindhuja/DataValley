def eval_agent_trajectory(trace: dict):
    steps=trace.get("steps",[])
    has_input=any("Input Guardrail" in s["name"] for s in steps)
    has_rag=any("RAG" in s["name"] for s in steps)
    has_output=any("Output Guardrail" in s["name"] for s in steps)
    tool_calls=len([s for s in steps if "Tool" in s["name"]])
    policy_ok=not any("Policy Engine" in s["name"] and not s["safe"] for s in steps if "safe" in s)
    return {"has_tool_calls": tool_calls>0, "has_guardrails": has_input and has_output, "has_rag": has_rag, "tool_calls": tool_calls, "policy_compliant": policy_ok, "task_success": policy_ok and has_output}
