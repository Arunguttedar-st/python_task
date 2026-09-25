from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = "sqlite:///./employees.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class EmployeeModel(Base):
  __tablename__ = "employees"
  id = Column(Integer, primary_key=True, index=True, autoincrement=True)
  name = Column(String, nullable=False)
  email = Column(String, unique=True, index=True, nullable=False)
  phone = Column(String, nullable=True)
  department = Column(String, nullable=False)
  designation = Column(String, nullable=False)
  created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Employee Directory API",
    description="CRUD operations for employee management",
)


def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()


class EmployeeCreate(BaseModel):
  name: str = Field(..., min_length=1)
  email: EmailStr
  phone: str | None = None
  department: str = Field(..., min_length=1)
  designation: str = Field(..., min_length=1)


class EmployeeResponse(EmployeeCreate):
  id: int
  created_at: datetime

  class Config:
    from_attributes = True


@app.post(
    "/employees/",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_employee(employee: EmployeeCreate, db: Session = Depends(get_db)):
  existing = (
      db.query(EmployeeModel)
      .filter(EmployeeModel.email == employee.email)
      .first()
  )
  if existing:
    raise HTTPException(
        status_code=400, detail="Email already registered in the directory."
    )
  db_employee = EmployeeModel(**employee.dict())
  db.add(db_employee)
  db.commit()
  db.refresh(db_employee)
  return db_employee


@app.get("/employees/", response_model=list[EmployeeResponse])
def get_employees(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
  return db.query(EmployeeModel).offset(skip).limit(limit).all()


@app.get("/employees/{emp_id}", response_model=EmployeeResponse)
def get_employee(emp_id: int, db: Session = Depends(get_db)):
  emp = (
      db.query(EmployeeModel).filter(EmployeeModel.id == emp_id).first()
  )
  if not emp:
    raise HTTPException(status_code=404, detail="Employee not found.")
  return emp


@app.put("/employees/{emp_id}", response_model=EmployeeResponse)
def update_employee(
    emp_id: int, employee: EmployeeCreate, db: Session = Depends(get_db)
):
  emp = (
      db.query(EmployeeModel).filter(EmployeeModel.id == emp_id).first()
  )
  if not emp:
    raise HTTPException(status_code=404, detail="Employee not found.")
  email_check = (
      db.query(EmployeeModel)
      .filter(
          EmployeeModel.email == employee.email, EmployeeModel.id != emp_id
      )
      .first()
  )
  if email_check:
    raise HTTPException(
        status_code=400, detail="Email is already used by another employee."
    )
  for key, value in employee.dict().items():
    setattr(emp, key, value)
  db.commit()
  db.refresh(emp)
  return emp


@app.delete("/employees/{emp_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(emp_id: int, db: Session = Depends(get_db)):
  emp = (
      db.query(EmployeeModel).filter(EmployeeModel.id == emp_id).first()
  )
  if not emp:
    raise HTTPException(status_code=404, detail="Employee not found.")
  db.delete(emp)
  db.commit()
  return None