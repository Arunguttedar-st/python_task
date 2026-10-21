from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.models.user import UserRole


class UserCreate(BaseModel):
  username: str
  email: EmailStr
  password: str


class UserResponse(BaseModel):
  id: int
  username: str
  email: EmailStr
  role: UserRole
  is_active: bool
  created_at: datetime

  class Config:
    from_attributes = True


class TokenResponse(BaseModel):
  access_token: str
  refresh_token: str
  token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
  refresh_token: str