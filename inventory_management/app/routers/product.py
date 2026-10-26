from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.product import ProductCreate, ProductResponse
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    return ProductService(db)


@router.post(
    "/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED
)
def create_product(
    product_in: ProductCreate,
    service: ProductService = Depends(get_product_service),
    # Restricted: Only Admins and Managers can create products
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER])),
):
    return service.create_product(product_in)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int, 
    service: ProductService = Depends(get_product_service),
    # Protected: Any authenticated active user (Admin, Manager, Employee) can view
    current_user: User = Depends(get_current_user),
):
    return service.get_product(product_id)