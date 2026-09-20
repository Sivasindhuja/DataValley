from mcp.server.fastmcp import FastMCP
from app.tools.orders import get_order, get_order_status, cancel_order, update_delivery_address
mcp = FastMCP("order-mcp")
mcp.tool()(get_order)
mcp.tool()(get_order_status)
mcp.tool()(cancel_order)
mcp.tool()(update_delivery_address)
if __name__ == "__main__":
    mcp.run()
