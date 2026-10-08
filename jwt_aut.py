from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, ConfigDict
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship

SECRET_KEY, ALGORITHM = "secret-key", "HS256"
engine = create_engine("sqlite:///./task.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# DB Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="User")
    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    status = Column(String, default="Pending")
    priority = Column(String, default="Medium")
    assigned_to = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="tasks")

Base.metadata.create_all(bind=engine)

# Pydantic Schemas
class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: Optional[str] = "User"

class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "Pending"
    priority: Optional[str] = "Medium"

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None

class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    assigned_to: int
    model_config = ConfigDict(from_attributes=True)

# Helper dependency
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email: raise HTTPException(401)
    except JWTError: raise HTTPException(401)
    user = db.query(User).filter(User.email == email).first()
    if not user: raise HTTPException(401)
    return user

app = FastAPI()

# Auth APIs
@app.post("/register", response_model=UserOut, status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(400, "Email already registered")
    u = User(full_name=user.full_name, email=user.email, hashed_password=pwd_context.hash(user.password), role=user.role)
    db.add(u); db.commit(); db.refresh(u)
    return u

@app.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not pwd_context.verify(form.password, user.hashed_password):
        raise HTTPException(401, "Incorrect email or password")
    token = jwt.encode({"sub": user.email, "exp": datetime.utcnow() + timedelta(minutes=30)}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}

@app.get("/users/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)):
    return user

# Task APIs
@app.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(task: TaskCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = Task(**task.model_dump(), assigned_to=user.id)
    db.add(t); db.commit(); db.refresh(t)
    return t

@app.get("/tasks", response_model=List[TaskOut])
def get_tasks(status: Optional[str] = None, priority: Optional[str] = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Task)
    if user.role != "Admin": q = q.filter(Task.assigned_to == user.id)
    if status: q = q.filter(Task.status == status)
    if priority: q = q.filter(Task.priority == priority)
    return q.all()

@app.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.query(Task).filter(Task.id == task_id).first()
    if not t: raise HTTPException(404, "Task not found")
    if user.role != "Admin" and t.assigned_to != user.id: raise HTTPException(403, "Not authorized")
    return t

@app.put("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, update: TaskUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.query(Task).filter(Task.id == task_id).first()
    if not t: raise HTTPException(404, "Task not found")
    if user.role != "Admin" and t.assigned_to != user.id: raise HTTPException(403, "Not authorized")
    for k, v in update.model_dump(exclude_unset=True).items(): setattr(t, k, v)
    db.commit(); db.refresh(t)
    return t

@app.patch("/tasks/{task_id}/complete", response_model=TaskOut)
def complete_task(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.query(Task).filter(Task.id == task_id).first()
    if not t: raise HTTPException(404, "Task not found")
    if user.role != "Admin" and t.assigned_to != user.id: raise HTTPException(403, "Not authorized")
    t.status = "Completed"
    db.commit(); db.refresh(t)
    return t

@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.query(Task).filter(Task.id == task_id).first()
    if not t: raise HTTPException(404, "Task not found")
    if user.role != "Admin" and t.assigned_to != user.id: raise HTTPException(403, "Not authorized")
    db.delete(t); db.commit()
    return None