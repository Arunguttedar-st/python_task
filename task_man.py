from datetime import datetime, date
from enum import Enum
from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, Enum as SQLEnum, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# ==========================================
# 1. DATABASE CONFIGURATION (SQLite)
# ==========================================
SQLALCHEMY_DATABASE_URL = "sqlite:///./tasks.sqlite"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# SQLAlchemy 2.0 Modern Declarative Base
class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================================
# 2. ENUMS & PYDANTIC SCHEMAS
# ==========================================
class PriorityEnum(str, Enum):
    low = "Low"
    medium = "Medium"
    high = "High"


class StatusEnum(str, Enum):
    pending = "Pending"
    in_progress = "In Progress"
    completed = "Completed"


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, description="Task Title (Mandatory)")
    description: str = Field(..., min_length=1, description="Description (Mandatory)")
    priority: PriorityEnum = Field(..., description="Priority: Low, Medium, High")
    status: Optional[StatusEnum] = Field(
        default=StatusEnum.pending,
        description="Status: Pending, In Progress, Completed",
    )
    due_date: date = Field(..., description="Valid due date (YYYY-MM-DD)")
    assigned_to: str = Field(
        ..., min_length=1, description="Assigned person (Mandatory)"
    )


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = Field(None, min_length=1)
    priority: Optional[PriorityEnum] = None
    status: Optional[StatusEnum] = None
    due_date: Optional[date] = None
    assigned_to: Optional[str] = Field(None, min_length=1)


class TaskResponse(TaskBase):
    id: int
    created_date: datetime

    # Pydantic v2 modern configuration style
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 3. SQLALCHEMY DATABASE MODEL
# ==========================================
class TaskDB(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    priority = Column(SQLEnum(PriorityEnum), nullable=False)
    status = Column(SQLEnum(StatusEnum), default=StatusEnum.pending, nullable=False)
    due_date = Column(String, nullable=False)  # stored as YYYY-MM-DD string
    assigned_to = Column(String, nullable=False)
    created_date = Column(DateTime, default=datetime.utcnow, nullable=False)


# Create tables on startup
Base.metadata.create_all(bind=engine)


# ==========================================
# 4. CRUD OPERATIONS & FILTERS
# ==========================================
def get_task(db: Session, task_id: int):
    return db.query(TaskDB).filter(TaskDB.id == task_id).first()


def get_tasks(
    db: Session,
    status: Optional[StatusEnum] = None,
    priority: Optional[PriorityEnum] = None,
    assigned_to: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    query = db.query(TaskDB)
    if status:
        query = query.filter(TaskDB.status == status)
    if priority:
        query = query.filter(TaskDB.priority == priority)
    if assigned_to:
        query = query.filter(TaskDB.assigned_to.ilike(f"%{assigned_to}%"))
    return query.offset(skip).limit(limit).all()


def create_task(db: Session, task: TaskCreate):
    db_task = TaskDB(
        title=task.title,
        description=task.description,
        priority=task.priority,
        status=task.status,
        due_date=str(task.due_date),
        assigned_to=task.assigned_to,
        created_date=datetime.utcnow(),
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def update_task(db: Session, task_id: int, task_update: TaskUpdate):
    db_task = get_task(db, task_id)
    if not db_task:
        return None

    update_data = task_update.model_dump(exclude_unset=True)
    if "due_date" in update_data and update_data["due_date"]:
        update_data["due_date"] = str(update_data["due_date"])

    for key, value in update_data.items():
        setattr(db_task, key, value)

    db.commit()
    db.refresh(db_task)
    return db_task


def delete_task(db: Session, task_id: int):
    db_task = get_task(db, task_id)
    if not db_task:
        return None
    db.delete(db_task)
    db.commit()
    return db_task


# ==========================================
# 5. FASTAPI APPLICATION & ENDPOINTS
# ==========================================
app = FastAPI(
    title="Task Management API",
    description="Single-file REST API for managing tasks using FastAPI, Pydantic, and SQLite.",
    version="1.0.0",
)


@app.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
)
def create_new_task(task: TaskCreate, db: Session = Depends(get_db)):
    """Create a task with unique ID, title, description, priority, status, due date, and assignee."""
    return create_task(db=db, task=task)


@app.get(
    "/tasks",
    response_model=List[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all tasks with optional filters",
)
def read_tasks(
    status: Optional[StatusEnum] = Query(
        None, description="Filter by status (Pending, In Progress, Completed)"
    ),
    priority: Optional[PriorityEnum] = Query(
        None, description="Filter by priority (Low, Medium, High)"
    ),
    assigned_to: Optional[str] = Query(
        None, description="Filter/search by assigned person"
    ),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Retrieve all tasks or filter by status, priority, or assigned person."""
    return get_tasks(
        db,
        status=status,
        priority=priority,
        assigned_to=assigned_to,
        skip=skip,
        limit=limit,
    )


@app.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get task by ID",
)
def read_task(task_id: int, db: Session = Depends(get_db)):
    """Get a specific task by its unique ID. Returns 404 if not found."""
    db_task = get_task(db, task_id=task_id)
    if db_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )
    return db_task


@app.put(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing task",
)
def update_existing_task(
    task_id: int, task_update: TaskUpdate, db: Session = Depends(get_db)
):
    """Update task details by ID. Returns 404 if not found."""
    db_task = update_task(db, task_id=task_id, task_update=task_update)
    if db_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )
    return db_task


@app.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
)
def delete_existing_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task by ID. Returns 404 if not found."""
    db_task = delete_task(db, task_id=task_id)
    if db_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )
    return None