from pydantic import BaseModel, Field


class ProductBase(BaseModel):
  name: str = Field(..., min_length=1, max_length=255)
  sku: str = Field(..., min_length=1, max_length=100)
  description: str | None = None
  price: float = Field(..., ge=0)
  quantity: int = Field(..., ge=0)
  reorder_level: int = Field(..., ge=0)
  category_id: int
  supplier_id: int


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


class ProductResponse(ProductBase):
  id: int

  class Config:
    from_attributes = True