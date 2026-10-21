from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserResponse

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
  return current_user


@router.get("", response_model=list[UserResponse])
def get_all_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role([UserRole.ADMIN])),
):
  return UserRepository.get_all(db)


@router.patch("/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    new_role: UserRole,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role([UserRole.ADMIN])),
):
  user = UserRepository.get_by_id(db, user_id)
  if not user:
    raise HTTPException(status_code=404, detail="User not found")
  return UserRepository.update_role(db, user, new_role)


@router.patch("/{user_id}/status", response_model=UserResponse)
def update_user_status(
    user_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role([UserRole.ADMIN])),
):
  user = UserRepository.get_by_id(db, user_id)
  if not user:
    raise HTTPException(status_code=404, detail="User not found")
  return UserRepository.update_status(db, user, is_active)