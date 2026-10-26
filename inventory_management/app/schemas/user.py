from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from models import UserRole

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    # Prevent users from assigning Admin role during registration
    role: UserRole = Field(default=UserRole.EMPLOYEE)

    def validate_role(self):
        if self.role == UserRole.ADMIN:
            raise ValueError("Cannot register as Admin directly.")

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class RoleUpdate(BaseModel):
    role: UserRole

class StatusUpdate(BaseModel):
    is_active: bool