from sqlalchemy.orm import Session
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


class ProductRepository:

  def __init__(self, db: Session):
    self.db = db

  def get_by_id(self, product_id: int) -> Product | None:
    return (
        self.db.query(Product).filter(Product.id == product_id).first()
    )

  def get_by_sku(self, sku: str) -> Product | None:
    return self.db.query(Product).filter(Product.sku == sku).first()

  def get_all(
      self, skip: int = 0, limit: int = 10, category_id: int | None = None
  ) -> list[Product]:
    query = self.db.query(Product)
    if category_id:
      query = query.filter(Product.category_id == category_id)
    return query.offset(skip).limit(limit).all()

  def create(self, product_in: ProductCreate) -> Product:
    db_product = Product(**product_in.model_dump())
    self.db.add(db_product)
    self.db.commit()
    self.db.refresh(db_product)
    return db_product

  def update(self, db_product: Product, product_in: ProductUpdate) -> Product:
    update_data = product_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
      setattr(db_product, key, value)
    self.db.commit()
    self.db.refresh(db_product)
    return db_product

  def delete(self, db_product: Product) -> None:
    self.db.delete(db_product)
    self.db.commit()