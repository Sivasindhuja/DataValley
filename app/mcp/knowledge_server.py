from mcp.server.fastmcp import FastMCP
from app.rag.retrieval import hybrid_retrieve, search_policy
from app.tools.product import get_product, get_warranty
mcp = FastMCP("knowledge-mcp")
mcp.tool()(hybrid_retrieve)
mcp.tool()(search_policy)
mcp.tool()(get_product)
mcp.tool()(get_warranty)
if __name__ == "__main__":
    mcp.run()
