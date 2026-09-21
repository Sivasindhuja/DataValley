from mcp.server.fastmcp import FastMCP
from app.tools.customer import get_customer, get_customer_orders, get_customer_tickets, verify_customer
from app.tools.account import get_account, update_account
mcp = FastMCP("customer-mcp")
mcp.tool()(get_customer)
mcp.tool()(get_customer_orders)
mcp.tool()(get_customer_tickets)
mcp.tool()(verify_customer)
mcp.tool()(get_account)
mcp.tool()(update_account)
if __name__ == "__main__":
    mcp.run()
