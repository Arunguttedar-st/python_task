from sqlalchemy.orm import Session
from app.models.user import User, UserRole


class UserRepository:

  @staticmethod
  def get_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()

  @staticmethod
  def get_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()

  @staticmethod
  def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()

  @staticmethod
  def get_all(db: Session) -> list[User]:
    return db.query(User).all()

  @staticmethod
  def create(db: Session, user_data: dict) -> User:
    user = User(**user_data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

  @staticmethod
  def update_role(db: Session, user: User, new_role: UserRole) -> User:
    user.role = new_role
    db.commit()
    db.refresh(user)
    return user

  @staticmethod
  def update_status(db: Session, user: User, is_active: bool) -> User:
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user