"""Customer MCP server - exposes customer tools via MCP protocol (stub for LangGraph integration)"""
from app.tools.customer import get_customer, get_customer_orders, get_customer_tickets, verify_customer
TOOLS = {
    "get_customer": get_customer,
    "get_customer_orders": get_customer_orders,
    "get_customer_tickets": get_customer_tickets,
    "verify_customer": verify_customer,
}
def handle(tool: str, args: dict):
    fn = TOOLS.get(tool)
    if not fn: return {"error": f"Unknown tool {tool}"}
    return fn(**args)
