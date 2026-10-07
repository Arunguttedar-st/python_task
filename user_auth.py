from datetime import datetime
from enum import Enum
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Enum as SQLEnum
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# --- DATABASE SETUP (SQLite) ---
DATABASE_URL = "sqlite:///./users.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- PASSWORD HASHING SETUP ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- ENUMS ---
class UserRole(str, Enum):
    Admin = "Admin"
    User = "User"

# --- SQLALCHEMY USER MODEL ---
class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.User, nullable=False)
    created_date = Column(DateTime, default=datetime.utcnow, nullable=False)

Base.metadata.create_all(bind=engine)

# --- PYDANTIC SCHEMAS ---
class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=1, description="Full name is mandatory")
    email: EmailStr = Field(..., description="Valid email address is mandatory")
    phone_number: Optional[str] = None
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    role: UserRole = UserRole.User

    @field_validator('password')
    def validate_password_strength(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[UserRole] = None

class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    phone_number: Optional[str] = None
    role: UserRole
    created_date: datetime

    model_config = ConfigDict(from_attributes=True)

# --- DEPENDENCY: DATABASE SESSION ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- FASTAPI APP ---
app = FastAPI(
    title="User Authentication & Management API",
    description="REST API built with FastAPI, SQLite, and Pydantic (Day 8 Task)",
    version="1.0.0"
)

# --- HELPER FUNCTIONS ---
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# --- API ENDPOINTS ---

@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered."
        )
    
    hashed_pwd = hash_password(user.password)

    db_user = UserModel(
        full_name=user.full_name,
        email=user.email,
        phone_number=user.phone_number,
        hashed_password=hashed_pwd,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/login", status_code=status.HTTP_200_OK)
def login_user(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == credentials.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials: Email not found."
        )
    
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials: Incorrect password."
        )
    
    return {
        "message": "Login successful",
        "user_id": user.id,
        "email": user.email,
        "role": user.role
    }

@app.get("/users", response_model=List[UserResponse], status_code=status.HTTP_200_OK)
def get_users(
    role: Optional[UserRole] = Query(None, description="Filter users by role (Admin/User)"),
    name: Optional[str] = Query(None, description="Search users by full name"),
    db: Session = Depends(get_db)
):
    query = db.query(UserModel)
    
    if role:
        query = query.filter(UserModel.role == role)
    if name:
        query = query.filter(UserModel.full_name.ilike(f"%{name}%"))
        
    users = query.all()
    return users

@app.get("/users/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )
    return user

@app.put("/users/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )
    
    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
        
    db.commit()
    db.refresh(user)
    return user

@app.put("/users/{user_id}/password", status_code=status.HTTP_200_OK)
def change_password(user_id: int, body: PasswordChange, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )
    
    if not verify_password(body.old_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password."
        )
        
    user.hashed_password = hash_password(body.new_password)
    db.commit()
    return {"message": "Password updated successfully."}

@app.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )
    
    db.delete(user)
    db.commit()
    return {"message": f"User with ID {user_id} deleted successfully."}