"""MCP client - explicit execution mode, no silent fallback."""
from app.config import settings

# Direct map - always available for explicit direct mode
from app.tools.customer import get_customer, get_customer_orders, get_customer_tickets, verify_customer
from app.tools.orders import get_order, get_order_status, cancel_order, update_delivery_address
from app.tools.support import create_support_ticket, update_support_ticket, escalate_to_human, get_ticket
from app.tools.communication import send_email, send_notification
from app.rag.retrieval import chroma_retrieve, search_policy
from app.tools.product import get_product, get_warranty, get_product_status
from app.tools.account import get_account, update_account
from app.tools.refunds import get_refund_status, check_refund_eligibility, create_refund_request

DIRECT_MAP={
    "get_customer": get_customer,
    "get_customer_orders": get_customer_orders,
    "get_customer_tickets": get_customer_tickets,
    "verify_customer": verify_customer,
    "get_order": get_order,
    "get_order_status": get_order_status,
    "cancel_order": cancel_order,
    "update_delivery_address": update_delivery_address,
    "create_support_ticket": create_support_ticket,
    "update_support_ticket": update_support_ticket,
    "escalate_to_human": escalate_to_human,
    "get_ticket": get_ticket,
    "send_email": send_email,
    "send_notification": send_notification,
    "chroma_retrieve": chroma_retrieve,
    "hybrid_retrieve": chroma_retrieve,
    "search_policy": search_policy,
    "get_product": get_product,
    "get_warranty": get_warranty,
    "get_product_status": get_product_status,
    "get_account": get_account,
    "update_account": update_account,
    "get_refund_status": get_refund_status,
    "check_refund_eligibility": check_refund_eligibility,
    "create_refund_request": create_refund_request,
}

MCP_SERVERS={
    "customer-mcp": {"module":"app.mcp.customer_server","tools":["get_customer","get_customer_orders","get_customer_tickets","verify_customer","get_account","update_account"]},
    "order-mcp": {"module":"app.mcp.order_server","tools":["get_order","get_order_status","cancel_order","update_delivery_address"]},
    "support-mcp": {"module":"app.mcp.support_server","tools":["create_support_ticket","update_support_ticket","escalate_to_human","get_ticket","send_email","send_notification"]},
    "knowledge-mcp": {"module":"app.mcp.knowledge_server","tools":["chroma_retrieve","hybrid_retrieve","search_policy","get_product","get_warranty","get_product_status"]},
}

def get_execution_mode() -> str:
    # Explicit mode via settings: "mcp" or "direct"
    if settings.enable_mcp or settings.mcp_execution_mode == "mcp":
        return "mcp"
    return "direct"

async def call_mcp(tool: str, args: dict):
    """Async MCP call via stdio - requires mcp>=1.1.2"""
    from mcp.client.stdio import stdio_client
    from mcp import ClientSession, StdioServerParameters
    server="customer-mcp"
    for name, info in MCP_SERVERS.items():
        if tool in info["tools"]:
            server=name
            break
    mod=MCP_SERVERS[server]["module"]
    params=StdioServerParameters(command="python", args=["-m", mod], env=None)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result=await session.call_tool(tool, arguments=args)
            if result.content:
                import json
                text=result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
                try:
                    return json.loads(text)
                except:
                    return {"result": text}
            return {"error":"empty MCP response"}

def call(tool: str, args: dict):
    """Sync wrapper - explicit mode, no silent fallback."""
    mode = get_execution_mode()
    if mode == "direct":
        fn=DIRECT_MAP.get(tool)
        if not fn:
            return {"error": f"Unknown tool {tool}"}
        return fn(**args)
    # MCP mode - explicit, do not silently hide failure
    if tool not in DIRECT_MAP and tool not in [t for v in MCP_SERVERS.values() for t in v["tools"]]:
        return {"error": f"Unknown tool {tool}"}
    import asyncio
    try:
        return asyncio.run(call_mcp(tool, args))
    except Exception as e:
        # Explicit failure - don't fallback to direct silently
        return {"error": f"MCP failed: {e}", "execution_mode": "mcp", "fallback": "none"}
