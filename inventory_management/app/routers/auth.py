from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User, RefreshToken, UserRole
from schemas import UserRegister, UserLogin, TokenResponse, RefreshRequest, UserResponse
from security import get_password_hash, verify_password, create_access_token, create_refresh_token, SECRET_KEY, ALGORITHM
from deps import get_current_user
from jose import jwt, JWTError

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    if user_data.role == UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Cannot assign Admin role during registration.")
    
    existing = db.query(User).filter((User.username == user_data.username) | (User.email == user_data.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already registered.")

    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=TokenResponse)
def login(form_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive.")

    access_token = create_access_token({"sub": user.id, "role": user.role})
    refresh_token_str, token_id, expires_at = create_refresh_token({"sub": user.id})

    db_token = RefreshToken(token_id=token_id, user_id=user.id, expires_at=expires_at)
    db.add(db_token)
    db.commit()

    return {"access_token": access_token, "refresh_token": refresh_token_str, "token_type": "bearer"}

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=401, detail="Invalid refresh token.")
    try:
        payload = jwt.decode(body.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise credentials_exception
        user_id = payload.get("sub")
        token_id = payload.get("jti")
    except JWTError:
        raise credentials_exception

    db_token = db.query(RefreshToken).filter(RefreshToken.token_id == token_id, RefreshToken.is_revoked == False).first()
    if not db_token or db_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked.")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive.")

    access_token = create_access_token({"sub": user.id, "role": user.role})
    return {"access_token": access_token, "refresh_token": body.refresh_token, "token_type": "bearer"}

@router.post("/logout")
def logout(body: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(body.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        token_id = payload.get("jti")
        db_token = db.query(RefreshToken).filter(RefreshToken.token_id == token_id).first()
        if db_token:
            db_token.is_revoked = True
            db.commit()
    except JWTError:
        pass
    return {"message": "Successfully logged out."}