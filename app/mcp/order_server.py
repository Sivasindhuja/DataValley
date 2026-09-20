from app.tools.orders import get_order, get_order_status, cancel_order, update_delivery_address
TOOLS = {
    "get_order": get_order,
    "get_order_status": get_order_status,
    "cancel_order": cancel_order,
    "update_delivery_address": update_delivery_address,
}
def handle(tool: str, args: dict):
    fn = TOOLS.get(tool)
    if not fn: return {"error": f"Unknown tool {tool}"}
    return fn(**args)
