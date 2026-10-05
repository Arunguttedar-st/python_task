from datetime import datetime, date
from enum import Enum
from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, EmailStr
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker, relationship


# 1. DATABASE CONFIGURATION (SQLite)

SQLALCHEMY_DATABASE_URL = "sqlite:///./shop.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 2. ENUMS & SQLALCHEMY MODELS

class OrderStatus(str, Enum):
    pending = "Pending"
    confirmed = "Confirmed"
    shipped = "Shipped"
    delivered = "Delivered"
    cancelled = "Cancelled"

class CustomerModel(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String)
    address = Column(String)
    city = Column(String)
    created_date = Column(DateTime, default=datetime.utcnow)
    orders = relationship("OrderModel", back_populates="customer", cascade="all, delete-orphan")

class OrderModel(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    order_status = Column(SQLEnum(OrderStatus), default=OrderStatus.pending)
    order_date = Column(String, nullable=False)
    customer = relationship("CustomerModel", back_populates="orders")

Base.metadata.create_all(bind=engine)

# 3. PYDANTIC SCHEMAS

class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    phone_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None

class CustomerResponse(CustomerCreate):
    id: int
    created_date: datetime
    model_config = ConfigDict(from_attributes=True)

class OrderCreate(BaseModel):
    customer_id: int
    product_name: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    order_status: Optional[OrderStatus] = OrderStatus.pending
    order_date: Optional[date] = Field(default_factory=date.today)

class OrderUpdate(BaseModel):
    product_name: Optional[str] = None
    quantity: Optional[int] = Field(None, gt=0)
    unit_price: Optional[float] = Field(None, gt=0)
    order_status: Optional[OrderStatus] = None

class OrderResponse(BaseModel):
    id: int
    customer_id: int
    product_name: str
    quantity: int
    unit_price: float
    total_amount: float
    order_status: OrderStatus
    order_date: str
    model_config = ConfigDict(from_attributes=True)

# 4. FASTAPI APPLICATION
app = FastAPI(title="Customer & Order Management API", version="1.0")

# --- CUSTOMER ENDPOINTS ---
@app.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    if db.query(CustomerModel).filter(CustomerModel.email == customer.email).first():
        raise HTTPException(status_code=400, detail="Customer email already registered.")
    
    db_cust = CustomerModel(**customer.model_dump())
    db.add(db_cust)
    db.commit()
    db.refresh(db_cust)
    return db_cust

@app.get("/customers", response_model=List[CustomerResponse])
def get_customers(db: Session = Depends(get_db)):
    return db.query(CustomerModel).all()

@app.get("/customers/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    cust = db.query(CustomerModel).filter(CustomerModel.id == customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found.")
    return cust

@app.put("/customers/{customer_id}", response_model=CustomerResponse)
def update_customer(customer_id: int, update_data: CustomerUpdate, db: Session = Depends(get_db)):
    cust = db.query(CustomerModel).filter(CustomerModel.id == customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found.")
    
    for key, val in update_data.model_dump(exclude_unset=True).items():
        setattr(cust, key, val)
    
    db.commit()
    db.refresh(cust)
    return cust

@app.delete("/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    cust = db.query(CustomerModel).filter(CustomerModel.id == customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found.")
    db.delete(cust)
    db.commit()
    return None

# --- ORDER ENDPOINTS ---
@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    # Verify customer exists
    cust = db.query(CustomerModel).filter(CustomerModel.id == order.customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer does not exist. Cannot create order.")
    
    # Calculate Total Amount automatically
    total = order.quantity * order.unit_price

    db_order = OrderModel(
        customer_id=order.customer_id,
        product_name=order.product_name,
        quantity=order.quantity,
        unit_price=order.unit_price,
        total_amount=total,
        order_status=order.order_status,
        order_date=str(order.order_date)
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

@app.get("/orders", response_model=List[OrderResponse])
def get_orders(db: Session = Depends(get_db)):
    return db.query(OrderModel).all()

@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    ord_obj = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not ord_obj:
        raise HTTPException(status_code=404, detail="Order not found.")
    return ord_obj

@app.put("/orders/{order_id}", response_model=OrderResponse)
def update_order(order_id: int, update_data: OrderUpdate, db: Session = Depends(get_db)):
    ord_obj = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not ord_obj:
        raise HTTPException(status_code=404, detail="Order not found.")
    
    for key, val in update_data.model_dump(exclude_unset=True).items():
        setattr(ord_obj, key, val)
    
    # Recalculate total if quantity or price changes
    if "quantity" in update_data.model_dump(exclude_unset=True) or "unit_price" in update_data.model_dump(exclude_unset=True):
        ord_obj.total_amount = ord_obj.quantity * ord_obj.unit_price

    db.commit()
    db.refresh(ord_obj)
    return ord_obj

@app.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    ord_obj = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not ord_obj:
        raise HTTPException(status_code=404, detail="Order not found.")
    db.delete(ord_obj)
    db.commit()
    return None