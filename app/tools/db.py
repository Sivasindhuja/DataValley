from sqlalchemy import Column, String, Integer, Float, DateTime, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os
from app.config import settings

# Centralized config: single source of truth
DATABASE_URL = settings.database_url
sync_url = settings.sync_database_url

Base = declarative_base()

class Customer(Base):
    __tablename__ = "customers"
    id = Column(String, primary_key=True)  # C102
    name = Column(String)
    email = Column(String)
    status = Column(String, default="ACTIVE") # ACTIVE, LOCKED
    communication_preference = Column(String, default="email")
    password_hash = Column(String, nullable=True)  # bcrypt hash
    created_at = Column(DateTime, default=datetime.utcnow)

class Order(Base):
    __tablename__ = "orders"
    id = Column(String, primary_key=True) # 123
    customer_id = Column(String)
    product = Column(String)
    status = Column(String) # PENDING, PROCESSING, SHIPPED, DELIVERED, CANCELLED
    amount = Column(Float)
    shipping_address = Column(Text)
    carrier_status = Column(String)
    shipped_date = Column(String, nullable=True)
    delivered_date = Column(String, nullable=True)
    created_at = Column(String)

class Refund(Base):
    __tablename__ = "refunds"
    id = Column(String, primary_key=True) # R421
    order_id = Column(String)
    customer_id = Column(String)
    status = Column(String) # PROCESSING, APPROVED, REJECTED, COMPLETED
    amount = Column(Float)
    created_at = Column(String)

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(String, primary_key=True) # T42
    customer_id = Column(String)
    order_id = Column(String, nullable=True)
    issue = Column(Text)
    status = Column(String, default="OPEN") # OPEN, IN_PROGRESS, CLOSED, ESCALATED
    priority = Column(String, default="MEDIUM")
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class MemoryStore(Base):
    __tablename__ = "memories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String)
    content = Column(Text)
    type = Column(String) # episodic, customer
    created_at = Column(DateTime, default=datetime.utcnow)

def get_engine():
    # only create data dir for sqlite
    if sync_url.startswith("sqlite"):
        os.makedirs("data", exist_ok=True)
        os.makedirs(os.path.dirname(sync_url.replace("sqlite:///","")) or "data", exist_ok=True)
    return create_engine(sync_url, echo=False, pool_pre_ping=True)

def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine

def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()

