from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy import Column, Integer, String, Float, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# ==========================================
# CONFIGURATION & SECURITY CONSTANTS
# ==========================================
SECRET_KEY = "YOUR_SUPER_SECRET_KEY_CHANGE_IN_PRODUCTION"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Database setup (SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite:///./employee_management.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 Scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ==========================================
# DATABASE MODELS
# ==========================================
class UserModel(Base):
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="Employee")  # Admin, Manager, Employee
    created_date = Column(DateTime, default=datetime.utcnow)

class EmployeeModel(Base):
    __tablename__ = "employees"
    
    employee_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String, nullable=False)
    department = Column(String, nullable=False)
    designation = Column(String, nullable=False)
    salary = Column(Float, nullable=False)
    joining_date = Column(DateTime, nullable=False)
    created_date = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ==========================================
# PYDANTIC SCHEMAS (Pydantic V2 Modern Config)
# ==========================================
class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=2)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: Optional[str] = "Employee"

class UserResponse(BaseModel):
    user_id: int
    full_name: str
    email: EmailStr
    role: str
    created_date: datetime

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class EmployeeCreate(BaseModel):
    employee_name: str = Field(..., min_length=2)
    email: EmailStr
    phone_number: str
    department: str
    designation: str
    salary: float = Field(..., gt=0)
    joining_date: datetime

class EmployeeUpdate(BaseModel):
    employee_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    salary: Optional[float] = Field(None, gt=0)
    joining_date: Optional[datetime] = None

class PhoneUpdate(BaseModel):
    phone_number: str

class EmployeeResponse(BaseModel):
    employee_id: int
    employee_name: str
    email: EmailStr
    phone_number: str
    department: str
    designation: str
    salary: float
    joining_date: datetime
    created_date: datetime

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# UTILS & DEPENDENCIES
# ==========================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UserModel:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if user is None:
        raise credentials_exception
    return user

def require_roles(allowed_roles: List[str]):
    def role_dependency(current_user: UserModel = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role: {current_user.role}"
            )
        return current_user
    return role_dependency

# ==========================================
# FASTAPI APP INSTANCE
# ==========================================
app = FastAPI(
    title="Employee Management RBAC API",
    description="REST API with FastAPI, JWT Authentication, and Role-Based Access Control",
    version="1.0.0"
)

# ==========================================
# AUTHENTICATION APIs
# ==========================================
@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserCreate, db: Session = Depends(get_db), current_user: Optional[UserModel] = Depends(get_current_user, use_cache=False)):
    existing_user = db.query(UserModel).filter(UserModel.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    role_to_assign = "Employee"
    if user_data.role and user_data.role != "Employee":
        if not current_user or current_user.role != "Admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Admins can assign elevated roles (Manager or Admin)"
            )
        role_to_assign = user_data.role

    hashed_pw = hash_password(user_data.password)
    new_user = UserModel(
        full_name=user_data.full_name,
        email=user_data.email,
        hashed_password=hashed_pw,
        role=role_to_assign
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=UserResponse)
def read_users_me(current_user: UserModel = Depends(get_current_user)):
    return current_user

# ==========================================
# EMPLOYEE APIs
# ==========================================
@app.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    employee_data: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles(["Admin"]))
):
    existing_emp = db.query(EmployeeModel).filter(EmployeeModel.email == employee_data.email).first()
    if existing_emp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee with this email already exists")
    
    new_employee = EmployeeModel(**employee_data.model_dump())
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)
    return new_employee

@app.get("/employees", response_model=List[EmployeeResponse])
def get_employees(
    department: Optional[str] = Query(None, description="Filter by department"),
    designation: Optional[str] = Query(None, description="Filter by designation"),
    min_salary: Optional[float] = Query(None, description="Minimum salary filter"),
    max_salary: Optional[float] = Query(None, description="Maximum salary filter"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles(["Admin", "Manager"]))
):
    query = db.query(EmployeeModel)
    
    if department:
        query = query.filter(EmployeeModel.department.ilike(f"%{department}%"))
    if designation:
        query = query.filter(EmployeeModel.designation.ilike(f"%{designation}%"))
    if min_salary is not None:
        query = query.filter(EmployeeModel.salary >= min_salary)
    if max_salary is not None:
        query = query.filter(EmployeeModel.salary <= max_salary)
        
    return query.all()

@app.get("/employees/me", response_model=EmployeeResponse)
def get_logged_in_employee_profile(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    employee = db.query(EmployeeModel).filter(EmployeeModel.email == current_user.email).first()
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee profile not found for this user account")
    return employee

@app.patch("/employees/me/phone", response_model=EmployeeResponse)
def update_my_phone_number(
    phone_data: PhoneUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    employee = db.query(EmployeeModel).filter(EmployeeModel.email == current_user.email).first()
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee profile not found for this user account")
    
    employee.phone_number = phone_data.phone_number
    db.commit()
    db.refresh(employee)
    return employee

@app.get("/employees/{employee_id}", response_model=EmployeeResponse)
def get_employee_by_id(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    employee = db.query(EmployeeModel).filter(EmployeeModel.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    
    if current_user.role == "Employee":
        if employee.email != current_user.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employees are only authorized to view their own profile details"
            )
            
    return employee

@app.put("/employees/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int,
    employee_data: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles(["Admin", "Manager"]))
):
    employee = db.query(EmployeeModel).filter(EmployeeModel.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    
    update_data = employee_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(employee, key, value)
        
    db.commit()
    db.refresh(employee)
    return employee

@app.delete("/employees/{employee_id}", status_code=status.HTTP_200_OK)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_roles(["Admin"]))
):
    employee = db.query(EmployeeModel).filter(EmployeeModel.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    
    db.delete(employee)
    db.commit()
    return {"detail": f"Employee with ID {employee_id} successfully deleted"}