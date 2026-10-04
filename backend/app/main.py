from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .database import SessionLocal, Base, engine
from .models import Customer, Invoice, InvoiceItem, Payment

app = FastAPI(title="Billing App", version="1.0.0")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=2)
    email: str
    company: Optional[str] = None


class CustomerSchema(CustomerCreate):
    id: int
    created_at: datetime


class InvoiceItemCreate(BaseModel):
    description: str
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)


class InvoiceCreate(BaseModel):
    customer_id: int
    due_days: int = 14
    tax_rate: float = 0.0
    items: List[InvoiceItemCreate]


class PaymentCreate(BaseModel):
    amount: float = Field(..., gt=0)
    method: str = "card"
    reference: Optional[str] = None


class InvoiceItemSchema(InvoiceItemCreate):
    id: int


class InvoiceSchema(BaseModel):
    id: int
    customer_id: int
    issue_date: datetime
    due_date: datetime
    status: str
    tax_rate: float
    subtotal: float
    tax_amount: float
    total: float
    paid_amount: float
    items: List[InvoiceItemSchema]


class PaymentSchema(BaseModel):
    id: int
    invoice_id: int
    amount: float
    method: str
    reference: Optional[str]
    created_at: datetime


def calculate_invoice_values(items: List[InvoiceItemCreate], tax_rate: float):
    subtotal = sum(item.quantity * item.unit_price for item in items)
    tax_amount = subtotal * (tax_rate / 100)
    total = subtotal + tax_amount
    return round(subtotal, 2), round(tax_amount, 2), round(total, 2)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/customers", response_model=list[CustomerSchema])
def get_customers(db: Session = Depends(get_db)):
    return db.query(Customer).order_by(Customer.id.desc()).all()


@app.post("/api/customers", response_model=CustomerSchema, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)):
    exists = db.query(Customer).filter(Customer.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Customer with this email already exists")

    customer = Customer(
        name=payload.name,
        email=payload.email,
        company=payload.company,
        created_at=datetime.utcnow(),
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@app.get("/api/invoices", response_model=list[InvoiceSchema])
def list_invoices(db: Session = Depends(get_db)):
    invoices = db.query(Invoice).order_by(Invoice.id.desc()).all()
    return [
        InvoiceSchema(
            id=invoice.id,
            customer_id=invoice.customer_id,
            issue_date=invoice.issue_date,
            due_date=invoice.due_date,
            status=invoice.status,
            tax_rate=invoice.tax_rate,
            subtotal=invoice.subtotal,
            tax_amount=invoice.tax_amount,
            total=invoice.total,
            paid_amount=invoice.paid_amount,
            items=[
                InvoiceItemSchema(
                    id=item.id,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                )
                for item in invoice.items
            ],
        )
        for invoice in invoices
    ]


@app.post("/api/invoices", response_model=InvoiceSchema, status_code=status.HTTP_201_CREATED)
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == payload.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if not payload.items:
        raise HTTPException(status_code=400, detail="Invoice must include at least one item")

    subtotal, tax_amount, total = calculate_invoice_values(payload.items, payload.tax_rate)
    issue_date = datetime.utcnow()
    due_date = issue_date + timedelta(days=payload.due_days)

    invoice = Invoice(
        customer_id=payload.customer_id,
        issue_date=issue_date,
        due_date=due_date,
        status="sent",
        tax_rate=payload.tax_rate,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total=total,
        paid_amount=0.0,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    for item in payload.items:
        db.add(
            InvoiceItem(
                invoice_id=invoice.id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
        )

    db.commit()
    db.refresh(invoice)
    return InvoiceSchema(
        id=invoice.id,
        customer_id=invoice.customer_id,
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        status=invoice.status,
        tax_rate=invoice.tax_rate,
        subtotal=invoice.subtotal,
        tax_amount=invoice.tax_amount,
        total=invoice.total,
        paid_amount=invoice.paid_amount,
        items=[
            InvoiceItemSchema(
                id=item.id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
            for item in invoice.items
        ],
    )


@app.get("/api/invoices/{invoice_id}", response_model=InvoiceSchema)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return InvoiceSchema(
        id=invoice.id,
        customer_id=invoice.customer_id,
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        status=invoice.status,
        tax_rate=invoice.tax_rate,
        subtotal=invoice.subtotal,
        tax_amount=invoice.tax_amount,
        total=invoice.total,
        paid_amount=invoice.paid_amount,
        items=[
            InvoiceItemSchema(
                id=item.id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
            for item in invoice.items
        ],
    )


@app.post("/api/invoices/{invoice_id}/pay", response_model=PaymentSchema)
def pay_invoice(invoice_id: int, payload: PaymentCreate, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    remaining = invoice.total - invoice.paid_amount
    if payload.amount > remaining:
        raise HTTPException(status_code=400, detail=f"Payment exceeds remaining balance of {remaining}")

    payment = Payment(
        invoice_id=invoice.id,
        amount=payload.amount,
        method=payload.method,
        reference=payload.reference,
        created_at=datetime.utcnow(),
    )
    db.add(payment)
    invoice.paid_amount = round(invoice.paid_amount + payload.amount, 2)
    invoice.status = "paid" if invoice.paid_amount >= invoice.total else "partially_paid"
    db.commit()
    db.refresh(payment)
    return payment


@app.get("/api/payments", response_model=list[PaymentSchema])
def list_payments(db: Session = Depends(get_db)):
    return db.query(Payment).order_by(Payment.id.desc()).all()


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    customers_count = db.query(Customer.id).count()
    invoices = db.query(Invoice).all()
    total_revenue = round(sum(invoice.paid_amount for invoice in invoices), 2)
    outstanding = round(sum(invoice.total - invoice.paid_amount for invoice in invoices if invoice.total > invoice.paid_amount), 2)
    overdue_count = sum(
        1 for invoice in invoices if invoice.status in {"sent", "partially_paid"} and invoice.due_date < datetime.utcnow()
    )
    return {
        "customers_count": customers_count,
        "invoices_count": len(invoices),
        "total_revenue": total_revenue,
        "outstanding": outstanding,
        "overdue_count": overdue_count,
    }


Base.metadata.create_all(bind=engine)
