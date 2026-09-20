from mcp.server.fastmcp import FastMCP
from app.tools.support import create_support_ticket, update_support_ticket, escalate_to_human, get_ticket
from app.tools.communication import send_email, send_notification
mcp = FastMCP("support-mcp")
mcp.tool()(create_support_ticket)
mcp.tool()(update_support_ticket)
mcp.tool()(escalate_to_human)
mcp.tool()(get_ticket)
mcp.tool()(send_email)
mcp.tool()(send_notification)
if __name__ == "__main__":
    mcp.run()
