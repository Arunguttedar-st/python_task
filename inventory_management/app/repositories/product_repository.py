from typing import List, Optional, Tuple
from sqlalchemy import or_, desc, asc, func
from sqlalchemy.orm import Session
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


class ProductRepository:
    ALLOWED_SORT_FIELDS = {
        "name": Product.name,
        "price": Product.price,
        "quantity": Product.quantity,
        "reorder_level": Product.reorder_level,
        "created_at": Product.created_at,
        "updated_at": Product.updated_at,
        "id": Product.id,
    }

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, product_id: int) -> Product | None:
        return self.db.query(Product).filter(Product.id == product_id).first()

    def get_by_sku(self, sku: str) -> Product | None:
        return self.db.query(Product).filter(Product.sku == sku).first()

    def get_all(
        self, skip: int = 0, limit: int = 10, category_id: int | None = None
    ) -> list[Product]:
        query = self.db.query(Product)
        if category_id:
            query = query.filter(Product.category_id == category_id)
        return query.offset(skip).limit(limit).all()

    def get_filtered_products(
        self,
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
        search_query: Optional[str] = None,
        sort_by: str = "id",
        sort_order: str = "desc",
    ) -> Tuple[List[Product], int]:
        
        query = self.db.query(Product)
        count_query = self.db.query(func.count(Product.id))

        filters = []
        if category_id is not None:
            filters.append(Product.category_id == category_id)
        if supplier_id is not None:
            filters.append(Product.supplier_id == supplier_id)
        if min_price is not None:
            filters.append(Product.price >= min_price)
        if max_price is not None:
            filters.append(Product.price <= max_price)
        if min_quantity is not None:
            filters.append(Product.quantity >= min_quantity)
        if max_quantity is not None:
            filters.append(Product.quantity <= max_quantity)
        if is_active is not None:
            filters.append(Product.is_active == is_active)
        if low_stock_only:
            filters.append(Product.quantity <= Product.reorder_level)

        if search_query:
            pattern = f"%{search_query}%"
            filters.append(
                or_(
                    Product.name.ilike(pattern),
                    Product.sku.ilike(pattern),
                    Product.description.ilike(pattern),
                )
            )

        if filters:
            query = query.filter(*filters)
            count_query = count_query.filter(*filters)

        total_records = count_query.scalar() or 0

        # Whitelisted dynamic sorting
        sort_col = self.ALLOWED_SORT_FIELDS.get(sort_by, Product.id)
        if sort_order.lower() == "asc":
            query = query.order_by(asc(sort_col))
        else:
            query = query.order_by(desc(sort_col))

        # Pagination offset and limit
        offset = (page - 1) * page_size
        products = query.offset(offset).limit(page_size).all()

        return products, total_records

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