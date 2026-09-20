catalog = {
    "product-a": {"name": "Smart Hub", "price": 149, "warranty": "2 years", "description": "Voice control hub"},
    "product-b": {"name": "Wireless Earbuds", "price": 79, "warranty": "1 year", "description": "Noise cancelling"},
    "product-c": {"name": "Fitness Band", "price": 49, "warranty": "6 months", "description": "Heart rate + steps"},
}
def get_product(product_id: str):
    return catalog.get(product_id, {"error": "Product not found"})
def get_warranty(product_id: str):
    p = get_product(product_id)
    if "error" in p: return p
    return {"product": product_id, "warranty": p["warranty"], "policy": "warranty-policy v2"}
def get_product_status(product_id: str):
    return {"product": product_id, "available": product_id in catalog, "stock": "In Stock" if product_id in catalog else "Unknown"}
