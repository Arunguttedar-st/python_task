from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, PaginatedResponse
from app.services.product_service import ProductService
from app.repositories.product_repository import ProductRepository
from app.services.notification_service import notify_low_stock

router = APIRouter(prefix="/products", tags=["Products"])

# --- 1. EXISTING CREATION ENDPOINT (WITH BACKGROUND TASK) ---
@router.post("/", status_code=201)
def create_product(
    product_in: ProductCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a new product and trigger low-stock background check if needed."""
    repo = ProductRepository(db)
    product = repo.create(product_in)  # Or your existing CRUD call

    # Trigger background check for low stock (Fixed product.stock to product.quantity)
    background_tasks.add_task(
        notify_low_stock,
        product_name=product.name,
        stock=product.quantity,  # Updated to match your model's field name
        reorder_level=product.reorder_level
    )

    return {"message": "Product created successfully", "product_id": product.id}


# --- 2. NEW PAGINATED, FILTERED & SORTED LISTING ENDPOINT ---
@router.get("", response_model=PaginatedResponse[ProductResponse])
def get_products(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    category_id: Optional[int] = Query(None, description="Filter by Category ID"),
    supplier_id: Optional[int] = Query(None, description="Filter by Supplier ID"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    min_quantity: Optional[int] = Query(None, ge=0, description="Minimum quantity"),
    max_quantity: Optional[int] = Query(None, ge=0, description="Maximum quantity"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name, SKU, or description"),
    sort_by: str = Query("id", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    db: Session = Depends(get_db),
):
    """Retrieve paginated, filtered, sorted, and searched products."""
    return ProductService.list_products(
        db=db,
        page=page,
        page_size=page_size,
        category_id=category_id,
        supplier_id=supplier_id,
        min_price=min_price,
        max_price=max_price,
        min_quantity=min_quantity,
        max_quantity=max_quantity,
        is_active=is_active,
        low_stock_only=False,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


# --- 3. NEW DEDICATED SEARCH ENDPOINT ---
@router.get("/search", response_model=PaginatedResponse[ProductResponse])
def search_products(
    q: str = Query(..., min_length=1, description="Search query string"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Dedicated search endpoint for products by name, SKU, or description."""
    return ProductService.list_products(
        db=db,
        page=page,
        page_size=page_size,
        category_id=None,
        supplier_id=None,
        min_price=None,
        max_price=None,
        min_quantity=None,
        max_quantity=None,
        is_active=None,
        low_stock_only=False,
        search=q,
        sort_by="name",
        sort_order="asc",
    )


# --- 4. NEW LOW STOCK RESTOCKING ENDPOINT ---
@router.get("/low-stock", response_model=PaginatedResponse[ProductResponse])
def get_low_stock_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Retrieve products where quantity is at or below their reorder level."""
    return ProductService.list_products(
        db=db,
        page=page,
        page_size=page_size,
        category_id=None,
        supplier_id=None,
        min_price=None,
        max_price=None,
        min_quantity=None,
        max_quantity=None,
        is_active=None,
        low_stock_only=True,
        search=None,
        sort_by="quantity",
        sort_order="asc",
    )