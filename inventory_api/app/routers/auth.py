from fastapi import AP, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import TokenResponse, UserCreate, UserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
  if UserRepository.get_by_username(db, user_in.username):
    raise HTTPException(
        status_code=400, detail="Username already registered"
    )
  if UserRepository.get_by_email(db, user_in.email):
    raise HTTPException(status_code=400, detail="Email already registered")

  hashed_pwd = hash_password(user_in.password)
  new_user = UserRepository.create(
      db,
      {
          "username": user_in.username,
          "email": user_in.email,
          "hashed_password": hashed_pwd,
          "role": UserRole.EMPLOYEE,
          "is_active": True,
      },
  )
  return new_user


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
  user = UserRepository.get_by_username(db, form_data.username)
  if not user or not verify_password(form_data.password, user.hashed_password):
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
    )
  if not user.is_active:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated"
    )

  access_token = create_access_token({"sub": str(user.id)})
  refresh_token = create_refresh_token({"sub": str(user.id)})

  return {
      "access_token": access_token,
      "refresh_token": refresh_token,
      "token_type": "bearer",
  }