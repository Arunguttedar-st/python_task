from math import ceil
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import PaginatedCategoryResponse, CategoryResponse

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.get("", response_model=PaginatedCategoryResponse[CategoryResponse])
def list_categories(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search category by name"),
    is_active: Optional[bool] = Query(None, description="Filter active categories"),
    db: Session = Depends(get_db),
):
    """Retrieve paginated and filtered categories."""
    repo = CategoryRepository(db)
    items, total = repo.get_paginated(page=page, page_size=page_size, search=search, is_active=is_active)
    total_pages = ceil(total / page_size) if total > 0 else 0

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "items": items,
    }