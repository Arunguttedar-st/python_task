from typing import List, Optional, Tuple
from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from app.models.category import Category

class CategoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[Category], int]:
        query = self.db.query(Category)
        count_query = self.db.query(func.count(Category.id))

        filters = []
        if search:
            filters.append(Category.name.ilike(f"%{search}%"))
        if is_active is not None:
            filters.append(Category.is_active == is_active)

        if filters:
            query = query.filter(*filters)
            count_query = count_query.filter(*filters)

        total = count_query.scalar() or 0
        offset = (page - 1) * page_size
        items = query.order_by(desc(Category.id)).offset(offset).limit(page_size).all()

        return items, total