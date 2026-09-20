from app.tools.db import init_db, get_session, Customer, Order, Refund, Ticket, MemoryStore
from datetime import datetime

def seed():
    engine = init_db()
    session = get_session()
    # clear
    session.query(Customer).delete()
    session.query(Order).delete()
    session.query(Refund).delete()
    session.query(Ticket).delete()
    session.query(MemoryStore).delete()

    customers = [
        Customer(id="C102", name="Alex Johnson", email="alex@example.com", status="ACTIVE", communication_preference="email"),
        Customer(id="C103", name="Priya Singh", email="priya@example.com", status="ACTIVE"),
        Customer(id="C104", name="John Locked", email="john@example.com", status="LOCKED"),
    ]
    orders = [
        Order(id="123", customer_id="C102", product="product-a", status="SHIPPED", amount=149, shipping_address="123 Main St, NY", carrier_status="In transit", shipped_date="2026-09-17", created_at="2026-09-10"),
        Order(id="124", customer_id="C102", product="product-b", status="PENDING", amount=79, shipping_address="123 Main St, NY", carrier_status="Not shipped", created_at="2026-09-19"),
        Order(id="125", customer_id="C103", product="product-c", status="DELIVERED", amount=49, shipping_address="456 Park Ave", carrier_status="Delivered", shipped_date="2026-09-05", delivered_date="2026-09-10", created_at="2026-09-01"),
        Order(id="126", customer_id="C103", product="product-a", status="PROCESSING", amount=149, shipping_address="456 Park Ave", carrier_status="Processing", created_at="2026-09-18"),
    ]
    refunds = [
        Refund(id="R421", order_id="125", customer_id="C103", status="PROCESSING", amount=49, created_at="2026-09-15"),
        Refund(id="R422", order_id="123", customer_id="C102", status="COMPLETED", amount=149, created_at="2026-09-12"),
    ]
    tickets = [
        Ticket(id="T42", customer_id="C102", order_id="123", issue="Order #123 delivery delayed", status="OPEN", priority="MEDIUM", summary="Customer reported delivery issue, contacted twice"),
    ]
    memories = [
        MemoryStore(customer_id="C102", content="Order #123 delivery issue - contacted support twice", type="episodic"),
        MemoryStore(customer_id="C102", content="Active orders: 123, 124 | Open tickets: T42", type="customer"),
    ]
    for c in customers: session.add(c)
    for o in orders: session.add(o)
    for r in refunds: session.add(r)
    for t in tickets: session.add(t)
    for m in memories: session.add(m)
    session.commit()
    print("Seeded DB with", session.query(Customer).count(), "customers,", session.query(Order).count(), "orders")
    session.close()

if __name__ == "__main__":
    seed()
