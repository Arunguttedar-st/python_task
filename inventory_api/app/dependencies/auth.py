from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
  credentials_exception = HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Could not validate credentials",
      headers={"WWW-Authenticate": "Bearer"},
  )
  try:
    payload = jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    user_id: str = payload.get("sub")
    token_type: str = payload.get("type")
    if user_id is None or token_type != "access":
      raise credentials_exception
  except JWTError:
    raise credentials_exception

  user = UserRepository.get_by_id(db, user_id=int(user_id))
  if user is None or not user.is_active:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Inactive or non-existent user",
    )
  return user


def require_role(required_roles: list[UserRole]):
  def role_checker(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in required_roles:
      raise HTTPException(
          status_code=status.HTTP_403_FORBIDDEN,
          detail="You do not have permission to perform this action",
      )
    return current_user

  return role_checker