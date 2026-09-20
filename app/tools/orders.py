from app.tools.db import get_session, Order

def get_order(order_id: str):
    s = get_session()
    o = s.query(Order).filter_by(id=order_id).first()
    s.close()
    if not o: return {"error": "Order not found"}
    return {"id": o.id, "customer_id": o.customer_id, "status": o.status, "product": o.product, "amount": o.amount, "shipping_address": o.shipping_address, "carrier_status": o.carrier_status, "shipped_date": o.shipped_date, "delivered_date": o.delivered_date}

def get_order_status(order_id: str):
    # Simulate API timeout handling - real would call carrier
    o = get_order(order_id)
    if "error" in o: return o
    return {"order_id": o["id"], "status": o["status"], "carrier_status": o["carrier_status"], "estimated_delivery": "2026-09-22" if o["status"]=="SHIPPED" else None}

def cancel_order(order_id: str):
    s = get_session()
    o = s.query(Order).filter_by(id=order_id).first()
    if not o:
        s.close()
        return {"success": False, "error": "Order not found"}
    # policy check delegated to policy engine, but tool also validates
    if o.status in ["SHIPPED", "DELIVERED", "CANCELLED"]:
        s.close()
        return {"success": False, "error": f"Cannot cancel order with status {o.status}"}
    o.status = "CANCELLED"
    s.commit()
    s.close()
    return {"success": True, "order_id": order_id, "new_status": "CANCELLED"}

def update_delivery_address(order_id: str, new_address: str):
    s = get_session()
    o = s.query(Order).filter_by(id=order_id).first()
    if not o:
        s.close()
        return {"success": False, "error": "Order not found"}
    if o.status == "SHIPPED":
        s.close()
        return {"success": False, "error": "Cannot update address after shipment per cancellation-policy v3"}
    o.shipping_address = new_address
    s.commit()
    s.close()
    return {"success": True, "order_id": order_id, "new_address": new_address}
