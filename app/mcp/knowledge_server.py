from app.rag.retrieval import search_policy, hybrid_retrieve
from app.tools.product import get_product, get_warranty
TOOLS = {
    "search_policy": search_policy,
    "search_product_docs": get_product,
    "hybrid_retrieve": hybrid_retrieve,
    "get_warranty": get_warranty,
}
def handle(tool: str, args: dict):
    fn = TOOLS.get(tool)
    if not fn: return {"error": f"Unknown tool {tool}"}
    return fn(**args)
