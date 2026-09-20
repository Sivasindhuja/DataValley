from app.tools.support import create_support_ticket, update_support_ticket, escalate_to_human, get_ticket
TOOLS = {
    "create_support_ticket": create_support_ticket,
    "update_support_ticket": update_support_ticket,
    "escalate_to_human": escalate_to_human,
    "get_ticket": get_ticket,
}
def handle(tool: str, args: dict):
    fn = TOOLS.get(tool)
    if not fn: return {"error": f"Unknown tool {tool}"}
    return fn(**args)
