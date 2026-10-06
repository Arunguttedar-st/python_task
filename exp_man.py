from datetime import datetime, date
from enum import Enum
from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException, status, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker, relationship


# 1. DATABASE CONFIGURATION (SQLite)

SQLALCHEMY_DATABASE_URL = "sqlite:///./expenses.db"
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

class PaymentMethod(str, Enum):
    cash = "Cash"
    card = "Card"
    upi = "UPI"
    bank_transfer = "Bank Transfer"

class ExpenseStatus(str, Enum):
    pending = "Pending"
    approved = "Approved"
    rejected = "Rejected"

class CategoryModel(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=False)
    
    expenses = relationship("ExpenseModel", back_populates="category", cascade="all, delete-orphan")

class ExpenseModel(Base):
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_name = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    expense_date = Column(String, nullable=False)
    payment_method = Column(SQLEnum(PaymentMethod), nullable=False)
    status = Column(SQLEnum(ExpenseStatus), default=ExpenseStatus.pending, nullable=False)
    created_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    category = relationship("CategoryModel", back_populates="expenses")

Base.metadata.create_all(bind=engine)


# 3. PYDANTIC SCHEMAS

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = Field(None, min_length=1)

class CategoryResponse(CategoryCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

class ExpenseCreate(BaseModel):
    employee_name: str = Field(..., min_length=1)
    category_id: int = Field(..., gt=0)
    amount: float = Field(..., gt=0)
    description: str = Field(..., min_length=1)
    expense_date: date
    payment_method: PaymentMethod
    status: Optional[ExpenseStatus] = ExpenseStatus.pending

class ExpenseUpdate(BaseModel):
    employee_name: Optional[str] = Field(None, min_length=1)
    category_id: Optional[int] = Field(None, gt=0)
    amount: Optional[float] = Field(None, gt=0)
    description: Optional[str] = Field(None, min_length=1)
    expense_date: Optional[date] = None
    payment_method: Optional[PaymentMethod] = None
    status: Optional[ExpenseStatus] = None

class ExpenseResponse(BaseModel):
    id: int
    employee_name: str
    category_id: int
    amount: float
    description: str
    expense_date: str
    payment_method: PaymentMethod
    status: ExpenseStatus
    created_date: datetime
    model_config = ConfigDict(from_attributes=True)


# 4. FASTAPI APPLICATION

app = FastAPI(title="Expense Management API", version="1.0")


# --- CATEGORY ENDPOINTS ---

@app.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    existing = db.query(CategoryModel).filter(CategoryModel.name == category.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category name already exists.")
    
    db_cat = CategoryModel(name=category.name, description=category.description)
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat

@app.get("/categories", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    return db.query(CategoryModel).all()

@app.get("/categories/{category_id}", response_model=CategoryResponse)
def get_category(category_id: int, db: Session = Depends(get_db)):
    cat = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found.")
    return cat

@app.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, update_data: CategoryUpdate, db: Session = Depends(get_db)):
    cat = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found.")
    
    dump = update_data.model_dump(exclude_unset=True)
    if "name" in dump:
        existing = db.query(CategoryModel).filter(CategoryModel.name == dump["name"], CategoryModel.id != category_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Category name already exists.")

    for key, val in dump.items():
        setattr(cat, key, val)
    
    db.commit()
    db.refresh(cat)
    return cat

@app.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    cat = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found.")
    db.delete(cat)
    db.commit()
    return None


# --- EXPENSE ENDPOINTS ---

@app.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(expense: ExpenseCreate, db: Session = Depends(get_db)):
    cat = db.query(CategoryModel).filter(CategoryModel.id == expense.category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category does not exist. Cannot create expense.")
    
    db_exp = ExpenseModel(
        employee_name=expense.employee_name,
        category_id=expense.category_id,
        amount=expense.amount,
        description=expense.description,
        expense_date=str(expense.expense_date),
        payment_method=expense.payment_method,
        status=expense.status
    )
    db.add(db_exp)
    db.commit()
    db.refresh(db_exp)
    return db_exp

@app.get("/expenses", response_model=List[ExpenseResponse])
def get_expenses(
    category_id: Optional[int] = Query(None),
    status: Optional[ExpenseStatus] = Query(None),
    payment_method: Optional[PaymentMethod] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(ExpenseModel)
    
    if category_id is not None:
        query = query.filter(ExpenseModel.category_id == category_id)
    if status is not None:
        query = query.filter(ExpenseModel.status == status)
    if payment_method is not None:
        query = query.filter(ExpenseModel.payment_method == payment_method)
    if start_date is not None:
        query = query.filter(ExpenseModel.expense_date >= str(start_date))
    if end_date is not None:
        query = query.filter(ExpenseModel.expense_date <= str(end_date))
        
    return query.all()

@app.get("/expenses/total")
def get_total_expenses(
    category_id: Optional[int] = Query(None),
    status: Optional[ExpenseStatus] = Query(None),
    payment_method: Optional[PaymentMethod] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(ExpenseModel)
    
    if category_id is not None:
        query = query.filter(ExpenseModel.category_id == category_id)
    if status is not None:
        query = query.filter(ExpenseModel.status == status)
    if payment_method is not None:
        query = query.filter(ExpenseModel.payment_method == payment_method)
    if start_date is not None:
        query = query.filter(ExpenseModel.expense_date >= str(start_date))
    if end_date is not None:
        query = query.filter(ExpenseModel.expense_date <= str(end_date))
        
    expenses = query.all()
    total = sum(exp.amount for exp in expenses)
    return {
        "total_expenses": total,
        "count": len(expenses)
    }

@app.get("/expenses/{expense_id}", response_model=ExpenseResponse)
def get_expense(expense_id: int, db: Session = Depends(get_db)):
    exp = db.query(ExpenseModel).filter(ExpenseModel.id == expense_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expense not found.")
    return exp

@app.put("/expenses/{expense_id}", response_model=ExpenseResponse)
def update_expense(expense_id: int, update_data: ExpenseUpdate, db: Session = Depends(get_db)):
    exp = db.query(ExpenseModel).filter(ExpenseModel.id == expense_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expense not found.")
    
    dump = update_data.model_dump(exclude_unset=True)
    if "category_id" in dump:
        cat = db.query(CategoryModel).filter(CategoryModel.id == dump["category_id"]).first()
        if not cat:
            raise HTTPException(status_code=404, detail="Category does not exist.")

    for key, val in dump.items():
        if key == "expense_date":
            setattr(exp, key, str(val))
        else:
            setattr(exp, key, val)
    
    db.commit()
    db.refresh(exp)
    return exp

@app.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    exp = db.query(ExpenseModel).filter(ExpenseModel.id == expense_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Expense not found.")
    db.delete(exp)
    db.commit()
    return None