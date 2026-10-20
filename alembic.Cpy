from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from sqlalchemy.exc import IntegrityError

# ==========================================
# 1. DATABASE CONFIGURATION
# ==========================================
DATABASE_URL = "sqlite:///./inventory.db"  # Change to MySQL URL if needed

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ==========================================
# 2. SQLALCHEMY MODELS
# ==========================================
class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    products = relationship("Product", back_populates="category")


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    contact_email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20), nullable=True)          
    address = Column(String(255), nullable=True)        
    is_active = Column(Boolean, default=True, nullable=False) 

    products = relationship("Product", back_populates="supplier")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    sku = Column(String(50), unique=True, nullable=False, index=True) 
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    stock_quantity = Column(Integer, nullable=False, default=0)
    reorder_level = Column(Integer, nullable=False, default=10)      
    
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False) 

    category = relationship("Category", back_populates="products")
    supplier = relationship("Supplier", back_populates="products")


Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================================
# 3. PYDANTIC SCHEMAS (Updated to Pydantic v2 ConfigDict)
# ==========================================
# Category Schemas
class CategoryCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None

class CategoryResponse(CategoryCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


# Supplier Schemas
class SupplierCreate(BaseModel):
    name: str = Field(..., max_length=100)
    contact_email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = True

class SupplierResponse(SupplierCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


# Product Schemas
class ProductCreate(BaseModel):
    name: str = Field(..., max_length=100)
    sku: str = Field(..., max_length=50)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    stock_quantity: int = Field(..., ge=0)
    reorder_level: int = Field(default=10, ge=0)
    category_id: int
    supplier_id: int

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    sku: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    reorder_level: Optional[int] = Field(None, ge=0)
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None

class ProductResponse(ProductCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 4. FASTAPI APPLICATION & ENDPOINTS
# ==========================================
app = FastAPI(
    title="Inventory Management API with Alembic Ready Schema",
    version="2.0.0"
)

@app.get("/")
def root():
    return {"message": "Welcome to the Inventory Management API. Visit /docs for Swagger UI."}

# --- Category Endpoints ---
@app.post("/categories/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    db_cat = Category(**category.model_dump())
    db.add(db_cat)
    try:
        db.commit()
        db.refresh(db_cat)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Category with this name already exists.")
    return db_cat

@app.get("/categories/", response_model=List[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()


# --- Supplier Endpoints ---
@app.post("/suppliers/", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(supplier: SupplierCreate, db: Session = Depends(get_db)):
    existing = db.query(Supplier).filter(Supplier.contact_email == supplier.contact_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Supplier with this email already exists.")
    
    db_supplier = Supplier(**supplier.model_dump())
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier

@app.get("/suppliers/", response_model=List[SupplierResponse])
def list_suppliers(active_only: bool = Query(False, description="Filter active suppliers only"), db: Session = Depends(get_db)):
    query = db.query(Supplier)
    if active_only:
        query = query.filter(Supplier.is_active == True)
    return query.all()


# --- Product Endpoints ---
@app.post("/products/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    existing_sku = db.query(Product).filter(Product.sku == product.sku).first()
    if existing_sku:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with SKU '{product.sku}' already exists."
        )
    
    db_product = Product(**product.model_dump())
    db.add(db_product)
    try:
        db.commit()
        db.refresh(db_product)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Foreign key error: Ensure category_id and supplier_id exist."
        )
    return db_product

@app.get("/products/", response_model=List[ProductResponse])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).all()

@app.get("/products/restock", response_model=List[ProductResponse])
def get_products_needing_restock(db: Session = Depends(get_db)):
    """Retrieve products where stock quantity is less than or equal to the reorder level."""
    return db.query(Product).filter(Product.stock_quantity <= Product.reorder_level).all()

@app.put("/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product_update: ProductUpdate, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found.")
    
    update_data = product_update.model_dump(exclude_unset=True)
    
    if "sku" in update_data and update_data["sku"] != db_product.sku:
        duplicate_sku = db.query(Product).filter(Product.sku == update_data["sku"]).first()
        if duplicate_sku:
            raise HTTPException(status_code=400, detail=f"SKU '{update_data['sku']}' is already in use.")

    for key, value in update_data.items():
        setattr(db_product, key, value)
    
    db_product.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_product)
    return db_product