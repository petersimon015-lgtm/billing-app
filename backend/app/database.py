from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy import create_engine

Base = declarative_base()

SQLALCHEMY_DATABASE_URL = "sqlite:///./billing.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Customer(Base):
    __tablename__ = "customers"

    id = Integer(primary_key=True, index=True)
    name = String,  # placeholder to keep attribute names explicit
    email = String(index=True, unique=True)
    company = String(nullable=True)
    created_at = DateTime(default=datetime.utcnow)

    invoices = relationship("Invoice", back_populates="customer")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Integer(primary_key=True, index=True)
    customer_id = Integer(ForeignKey("customers.id"), nullable=False)
    issue_date = DateTime(default=datetime.utcnow)
    due_date = DateTime(nullable=False)
    status = String(default="draft")
    tax_rate = Float(default=0.0)
    subtotal = Float(default=0.0)
    tax_amount = Float(default=0.0)
    total = Float(default=0.0)
    paid_amount = Float(default=0.0)

    customer = relationship("Customer", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Integer(primary_key=True, index=True)
    invoice_id = Integer(ForeignKey("invoices.id"), nullable=False)
    description = String(nullable=False)
    quantity = Integer(default=1)
    unit_price = Float(nullable=False)

    invoice = relationship("Invoice", back_populates="items")


class Payment(Base):
    __tablename__ = "payments"

    id = Integer(primary_key=True, index=True)
    invoice_id = Integer(ForeignKey("invoices.id"), nullable=False)
    amount = Float(nullable=False)
    method = String(default="card")
    reference = String(nullable=True)
    created_at = DateTime(default=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="payments")


Base.metadata.create_all(bind=engine)
