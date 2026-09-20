from mcp.server.fastmcp import FastMCP
from app.tools.customer import get_customer, get_customer_orders, get_customer_tickets, verify_customer
mcp = FastMCP("customer-mcp")
mcp.tool()(get_customer)
mcp.tool()(get_customer_orders)
mcp.tool()(get_customer_tickets)
mcp.tool()(verify_customer)
if __name__ == "__main__":
    mcp.run()
