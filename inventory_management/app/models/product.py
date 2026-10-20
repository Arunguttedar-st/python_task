from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database.base import Base


class Product(Base):
  __tablename__ = "products"

  id = Column(Integer, primary_key=True, index=True, autoincrement=True)
  name = Column(String(255), nullable=False, index=True)
  sku = Column(String(100), unique=True, nullable=False, index=True)
  description = Column(String(500), nullable=True)
  price = Column(Float, nullable=False)
  quantity = Column(Integer, nullable=False, default=0)
  reorder_level = Column(Integer, nullable=False, default=10)

  category_id = Column(
      Integer, ForeignKey("categories.id"), nullable=False, index=True
  )
  supplier_id = Column(
      Integer, ForeignKey("suppliers.id"), nullable=False, index=True
  )