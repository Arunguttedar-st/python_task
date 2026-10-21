import enum
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String
from app.core.database import Base


class UserRole(str, enum.Enum):
  ADMIN = "Admin"
  MANAGER = "Manager"
  EMPLOYEE = "Employee"


class User(Base):
  __tablename__ = "users"

  id = Column(Integer, primary_key=True, index=True)
  username = Column(String(50), unique=True, index=True, nullable=False)
  email = Column(String(100), unique=True, index=True, nullable=False)
  hashed_password = Column(String(255), nullable=False)
  role = Column(
      Enum(UserRole), default=UserRole.EMPLOYEE, nullable=False
  )
  is_active = Column(Boolean, default=True, nullable=False)
  created_at = Column(DateTime, default=datetime.utcnow, nullable=False)