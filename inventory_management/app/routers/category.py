from pydantic import BaseModel, Field
from typing import Optional, List, Generic, TypeVar

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = True

class CategoryResponse(CategoryBase):
    id: int

    class Config:
        from_attributes = True

T = TypeVar("T")
class PaginatedCategoryResponse(BaseModel, Generic[T]):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[T]

    class Config:
        from_attributes = True