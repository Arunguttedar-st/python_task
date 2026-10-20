from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:

  def __init__(self, db: Session):
    self.product_repo = ProductRepository(db)

  def get_product(self, product_id: int):
    product = self.product_repo.get_by_id(product_id)
    if not product:
      raise HTTPException(
          status_code=status.HTTP_404_NOT_FOUND,
          detail=f"Product with ID {product_id} not found",
      )
    return product

  def create_product(self, product_in: ProductCreate):
    # Rule: SKU must be unique
    if self.product_repo.get_by_sku(product_in.sku):
      raise HTTPException(
          status_code=status.HTTP_409_CONFLICT,
          detail=f"Product with SKU '{product_in.sku}' already exists.",
      )
    return self.product_repo.create(product_in)