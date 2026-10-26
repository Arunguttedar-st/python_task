import datetime  # <-- 1. Add this import at the very top
from sqlalchemy import Column, Float, ForeignKey, Integer, String, DateTime, Boolean  # <-- 2. Add DateTime and Boolean here
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

  # --- 3. ADD THE NEW COLUMNS RIGHT HERE INSIDE THE CLASS ---
  is_active = Column(Boolean, default=True, index=True)
  created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
  updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
  # -----------------------------------------------------------

  category_id = Column(
      Integer, ForeignKey("categories.id"), nullable=False, index=True
  )
  supplier_id = Column(
      Integer, ForeignKey("suppliers.id"), nullable=False, index=True
  )

  # Added image relationship fields
  image_id = Column(Integer, ForeignKey("file_metadata.id"), nullable=True, index=True)
  image = relationship("FileMetadata", back_populates="products")