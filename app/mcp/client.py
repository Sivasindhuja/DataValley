"""MCP client wrapper - routes tool calls through MCP servers when available, else direct import"""
from app.mcp.customer_server import mcp as customer_mcp
from app.mcp.order_server import mcp as order_mcp
from app.mcp.support_server import mcp as support_mcp
from app.mcp.knowledge_server import mcp as knowledge_mcp

# For now direct fallback; in production use MCP ClientSession over stdio
def call(tool: str, args: dict):
    # map to server
    try:
        if tool in ["get_customer","get_customer_orders","get_customer_tickets","verify_customer"]:
            from app.tools.customer import get_customer, get_customer_orders, get_customer_tickets, verify_customer
            return {"get_customer":get_customer,"get_customer_orders":get_customer_orders,"get_customer_tickets":get_customer_tickets,"verify_customer":verify_customer}[tool](**args)
        if tool in ["get_order","get_order_status","cancel_order","update_delivery_address"]:
            from app.tools.orders import get_order, get_order_status, cancel_order, update_delivery_address
            return {"get_order":get_order,"get_order_status":get_order_status,"cancel_order":cancel_order,"update_delivery_address":update_delivery_address}[tool](**args)
    except Exception as e:
        return {"error": str(e)}
