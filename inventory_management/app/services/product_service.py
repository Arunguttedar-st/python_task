from math import ceil
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.product_repository import ProductRepository
from app.schemas.product import PaginatedResponse

class ProductService:
    MAX_PAGE_SIZE = 100

    @staticmethod
    def list_products(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        category_id: Optional[int] = None,
        supplier_id: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_quantity: Optional[int] = None,
        max_quantity: Optional[int] = None,
        is_active: Optional[bool] = None,
        low_stock_only: bool = False,
        search: Optional[str] = None,
        sort_by: str = "id",
        sort_order: str = "desc",
    ) -> PaginatedResponse:
        
        # Validation checks
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page number must be greater than or equal to 1."
            )
        if page_size < 1 or page_size > ProductService.MAX_PAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Page size must be between 1 and {ProductService.MAX_PAGE_SIZE}."
            )
        if sort_by not in ProductRepository.ALLOWED_SORT_FIELDS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort field. Allowed fields: {list(ProductRepository.ALLOWED_SORT_FIELDS.keys())}"
            )
        if sort_order.lower() not in ["asc", "desc"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sort order must be either 'asc' or 'desc'."
            )

        # Instantiate repository with the synchronous session
        repo = ProductRepository(db)
        products, total = repo.get_filtered_products(
            page=page,
            page_size=page_size,
            category_id=category_id,
            supplier_id=supplier_id,
            min_price=min_price,
            max_price=max_price,
            min_quantity=min_quantity,
            max_quantity=max_quantity,
            is_active=is_active,
            low_stock_only=low_stock_only,
            search_query=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        total_pages = ceil(total / page_size) if total > 0 else 0

        return PaginatedResponse(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            items=products,
        )