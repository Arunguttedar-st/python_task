from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, create_engine, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

# 1. DATABASE CONFIGURATION

SQLALCHEMY_DATABASE_URL = "sqlite:///./inventory.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency that yields a database session, ensuring it closes after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 2. SQLALCHEMY MODELS

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    created_date = Column(DateTime, default=datetime.utcnow, nullable=False)

    products = relationship(
        "Product", back_populates="category", cascade="all, delete-orphan"
    )


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    created_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_date = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    category = relationship("Category", back_populates="products")


# 3. PYDANTIC SCHEMAS

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None


class CategoryResponse(CategoryBase):
    id: int
    created_date: datetime
    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    category_id: int
    price: float = Field(..., gt=0, description="Price must be greater than 0")
    quantity: int = Field(
        ..., ge=0, description="Quantity must be greater than or equal to 0"
    )


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    category_id: Optional[int] = None
    price: Optional[float] = Field(
        None, gt=0, description="Price must be greater than 0"
    )
    quantity: Optional[int] = Field(
        None, ge=0, description="Quantity must be greater than or equal to 0"
    )


class ProductResponse(ProductBase):
    id: int
    created_date: datetime
    updated_date: datetime
    model_config = ConfigDict(from_attributes=True)


class InventoryValueResponse(BaseModel):
    total_inventory_value: float


# 4. FASTAPI APP & ROUTERS SETUP
app = FastAPI(
    title="Product Inventory Management API",
    description="REST API built with FastAPI and SQLAlchemy ORM in a single file.",
    version="1.0.0",
)

category_router = APIRouter(prefix="/categories", tags=["Categories"])
product_router = APIRouter(prefix="/products", tags=["Products"])


# --- Category Endpoints ---
@category_router.post(
    "/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED
)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    db_category = Category(
        name=category.name, description=category.description
    )
    db.add(db_category)
    try:
        db.commit()
        db.refresh(db_category)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists.",
        )
    return db_category


@category_router.get("/", response_model=List[CategoryResponse])
def get_categories(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    return db.query(Category).offset(skip).limit(limit).all()


@category_router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    return category


@category_router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    db: Session = Depends(get_db),
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    update_data = category_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)

    try:
        db.commit()
        db.refresh(category)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category name already exists.",
        )
    return category


@category_router.delete(
    "/{category_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    db.delete(category)
    db.commit()
    return None


@category_router.get(
    "/{category_id}/products", response_model=List[ProductResponse]
)
def get_products_by_category_path(
    category_id: int, db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    return (
        db.query(Product).filter(Product.category_id == category_id).all()
    )


# --- Product Endpoints ---
@product_router.post(
    "/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED
)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    category = (
        db.query(Category).filter(Category.id == product.category_id).first()
    )
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with ID {product.category_id} does not exist.",
        )

    db_product = Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@product_router.get(
    "/inventory-value", response_model=InventoryValueResponse
)
def get_inventory_value(db: Session = Depends(get_db)):
    total_value = db.query(
        func.sum(Product.price * Product.quantity)
    ).scalar()
    return {"total_inventory_value": total_value if total_value else 0.0}


@product_router.get("/", response_model=List[ProductResponse])
def get_products(
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(Product)

    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if search is not None:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    return query.offset(skip).limit(limit).all()


@product_router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return product


@product_router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    update_data = product_update.model_dump(exclude_unset=True)

    if "category_id" in update_data:
        category = (
            db.query(Category)
            .filter(Category.id == update_data["category_id"])
            .first()
        )
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with ID {update_data['category_id']} does not exist.",
            )

    for key, value in update_data.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product


@product_router.delete(
    "/{product_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    db.delete(product)
    db.commit()
    return None

# 5. REGISTER ROUTERS & APP STARTUP

app.include_router(category_router)
app.include_router(product_router)

# Create database tables automatically upon startup
Base.metadata.create_all(bind=engine)


@app.get("/", tags=["Root"])
def read_root():
    return {
        "message": "Welcome to the Product Inventory Management API! Go to /docs for interactive Swagger UI."
    }