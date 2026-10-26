from pydantic import BaseModel, Field
from typing import Optional, Generic, List, TypeVar  # <-- Ensure Generic, List, TypeVar are imported here
from schemas.file_metadata import FileMetadataResponse


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sku: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    price: float = Field(..., ge=0)
    quantity: int = Field(..., ge=0)
    reorder_level: int = Field(..., ge=0)
    category_id: int
    supplier_id: int
    image_id: int | None = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    price: float | None = Field(None, ge=0)
    quantity: int | None = Field(None, ge=0)
    reorder_level: int | None = Field(None, ge=0)
    category_id: int | None = None
    supplier_id: int | None = None
    image_id: int | None = None


class ProductResponse(ProductBase):
    id: int
    image: FileMetadataResponse | None = None

    class Config:
        from_attributes = True



T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[T]

    class Config:
        from_attributes = True