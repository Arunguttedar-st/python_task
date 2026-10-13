import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# --- 1. CONFIGURATION & DATABASE SETUP ---
load_dotenv()

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "inventory_db")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
except Exception as e:
    raise RuntimeError(f"Failed to create database engine: {e}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- 2. SQLALCHEMY MODELS ---
class Category(Base):
    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category_name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    created_date = Column(DateTime, default=datetime.utcnow, nullable=False)

    products = relationship("Product", back_populates="category", cascade="all, delete-orphan")


class Supplier(Base):
    __tablename__ = "suppliers"

    supplier_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    supplier_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    phone_number = Column(String(20), nullable=False)
    address = Column(Text, nullable=False)
    company_name = Column(String(150), nullable=False)
    created_date = Column(DateTime, default=datetime.utcnow, nullable=False)

    products = relationship("Product", back_populates="supplier", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_name = Column(String(150), index=True, nullable=False)
    description = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.category_id", ondelete="RESTRICT"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.supplier_id", ondelete="RESTRICT"), nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    created_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    category = relationship("Category", back_populates="products")
    supplier = relationship("Supplier", back_populates="products")


# --- 3. PYDANTIC SCHEMAS ---
# Category Schemas
class CategoryBase(BaseModel):
    category_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    category_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None

class CategoryResponse(CategoryBase):
    category_id: int
    created_date: datetime

    class Config:
        from_attributes = True


# Supplier Schemas
class SupplierBase(BaseModel):
    supplier_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone_number: str = Field(..., min_length=5, max_length=20)
    address: str = Field(..., min_length=1)
    company_name: str = Field(..., min_length=1, max_length=150)

class SupplierCreate(SupplierBase):
    pass

class SupplierUpdate(BaseModel):
    supplier_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, min_length=5, max_length=20)
    address: Optional[str] = None
    company_name: Optional[str] = Field(None, min_length=1, max_length=150)

class SupplierResponse(SupplierBase):
    supplier_id: int
    created_date: datetime

    class Config:
        from_attributes = True


# Product Schemas
class ProductBase(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    category_id: int
    supplier_id: int
    price: float = Field(..., gt=0, description="Price must be greater than 0")
    quantity: int = Field(..., ge=0, description="Quantity must be greater than or equal to 0")

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    product_name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None
    price: Optional[float] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, ge=0)

class ProductResponse(ProductBase):
    product_id: int
    created_date: datetime
    updated_date: datetime
    category: Optional[CategoryResponse] = None
    supplier: Optional[SupplierResponse] = None

    class Config:
        from_attributes = True

class InventoryValueResponse(BaseModel):
    total_inventory_value: float


# --- 4. FASTAPI APP & ROUTERS ---
app = FastAPI(
    title="Inventory Management API",
    description="Single-file REST API built with FastAPI, SQLAlchemy, and MySQL.",
    version="1.0.0"
)

# Categories Router
categories_router = APIRouter(prefix="/categories", tags=["Categories"])

@categories_router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    existing = db.query(Category).filter(Category.category_name == category.category_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category name already exists.")
    db_category = Category(**category.dict())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@categories_router.get("/", response_model=list[CategoryResponse])
def get_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Category).offset(skip).limit(limit).all()

@categories_router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.category_id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found.")
    return category

@categories_router.put("/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.category_id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found.")
    if payload.category_name and payload.category_name != category.category_name:
        existing = db.query(Category).filter(Category.category_name == payload.category_name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Category name already exists.")
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(category, key, value)
    db.commit()
    db.refresh(category)
    return category

@categories_router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.category_id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found.")
    db.delete(category)
    db.commit()
    return None


# Suppliers Router
suppliers_router = APIRouter(prefix="/suppliers", tags=["Suppliers"])

@suppliers_router.post("/", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(supplier: SupplierCreate, db: Session = Depends(get_db)):
    existing = db.query(Supplier).filter(Supplier.email == supplier.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Supplier email already exists.")
    db_supplier = Supplier(**supplier.dict())
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier

@suppliers_router.get("/", response_model=list[SupplierResponse])
def get_suppliers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Supplier).offset(skip).limit(limit).all()

@suppliers_router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.supplier_id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found.")
    return supplier

@suppliers_router.get("/{supplier_id}/products", response_model=list[ProductResponse])
def get_supplier_products(supplier_id: int, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.supplier_id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found.")
    return supplier.products

@suppliers_router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(supplier_id: int, payload: SupplierUpdate, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.supplier_id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found.")
    if payload.email and payload.email != supplier.email:
        existing = db.query(Supplier).filter(Supplier.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Supplier email already exists.")
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(supplier, key, value)
    db.commit()
    db.refresh(supplier)
    return supplier

@suppliers_router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.supplier_id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found.")
    db.delete(supplier)
    db.commit()
    return None


# Products Router
products_router = APIRouter(prefix="/products", tags=["Products"])

@products_router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    if not db.query(Category).filter(Category.category_id == product.category_id).first():
        raise HTTPException(status_code=400, detail="Category ID does not exist.")
    if not db.query(Supplier).filter(Supplier.supplier_id == product.supplier_id).first():
        raise HTTPException(status_code=400, detail="Supplier ID does not exist.")
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@products_router.get("/inventory-value", response_model=InventoryValueResponse)
def get_inventory_value(db: Session = Depends(get_db)):
    total = db.query(func.sum(Product.price * Product.quantity)).scalar()
    return {"total_inventory_value": total or 0.0}

@products_router.get("/", response_model=list[ProductResponse])
def get_products(
    search: Optional[str] = Query(None, description="Search by product name"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    supplier_id: Optional[int] = Query(None, description="Filter by supplier ID"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(Product)
    if search:
        query = query.filter(Product.product_name.ilike(f"%{search}%"))
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    if supplier_id is not None:
        query = query.filter(Product.supplier_id == supplier_id)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    return query.offset(skip).limit(limit).all()

@products_router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product

@products_router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    if payload.category_id is not None and not db.query(Category).filter(Category.category_id == payload.category_id).first():
        raise HTTPException(status_code=400, detail="Category ID does not exist.")
    if payload.supplier_id is not None and not db.query(Supplier).filter(Supplier.supplier_id == payload.supplier_id).first():
        raise HTTPException(status_code=400, detail="Supplier ID does not exist.")
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product

@products_router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    db.delete(product)
    db.commit()
    return None


# Include Routers
app.include_router(categories_router)
app.include_router(suppliers_router)
app.include_router(products_router)

@app.get("/", tags=["Root"])
def root():
    return {"message": "Welcome to the Inventory Management API. Visit /docs for Swagger UI."}


# --- 5. AUTOMATIC TABLE CREATION ON STARTUP ---
Base.metadata.create_all(bind=engine)