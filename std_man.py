import sqlite3
import re
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status, Query
from pydantic import BaseModel, EmailStr, Field, field_validator

# Initialize FastAPI App
app = FastAPI(
    title="Student Management API (Raw SQLite)",
    version="2.0.0"
)

DB_FILE = "students.db"

# Database Initialization Helper
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone_number TEXT,
            age INTEGER NOT NULL,
            course TEXT NOT NULL,
            address TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Pydantic Schemas
class StudentBase(BaseModel):
    student_name: str = Field(..., min_length=1)
    email: EmailStr
    phone_number: str
    age: int = Field(..., ge=18, le=60)
    course: str = Field(..., min_length=1)
    address: Optional[str] = None

    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.fullmatch(r'^\d{10,15}$', v):
            raise ValueError('Phone number must contain between 10 and 15 digits.')
        return v

class StudentCreate(StudentBase):
    pass

class StudentUpdate(BaseModel):
    student_name: Optional[str] = Field(None, min_length=1)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    age: Optional[int] = Field(None, ge=18, le=60)
    course: Optional[str] = Field(None, min_length=1)
    address: Optional[str] = None

class StudentResponse(StudentBase):
    id: int


# 1. CREATE Student
@app.post("/students", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(student: StudentCreate):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO students (student_name, email, phone_number, age, course, address) VALUES (?, ?, ?, ?, ?, ?)",
            (student.student_name, student.email, student.phone_number, student.age, student.course, student.address)
        )
        conn.commit()
        student_id = cursor.lastrowid
        conn.close()
        
        return {**student.model_dump(), "id": student_id}
    
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Student with email '{student.email}' already exists."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2. GET ALL Students (with Course search & Age filters)
@app.get("/students", response_model=List[StudentResponse])
def get_students(
    course: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None, ge=18, le=60),
    max_age: Optional[int] = Query(None, ge=18, le=60)
):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    cursor = conn.cursor()
    
    query = "SELECT * FROM students WHERE 1=1"
    params = []
    
    if course:
        query += " AND course LIKE ?"
        params.append(f"%{course}%")
    if min_age is not None:
        query += " AND age >= ?"
        params.append(min_age)
    if max_age is not None:
        query += " AND age <= ?"
        params.append(max_age)
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

# 3. GET Student by ID
@app.get("/students/{student_id}", response_model=StudentResponse)
def get_student(student_id: int):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} not found."
        )
    return dict(row)

# 4. UPDATE Student
@app.put("/students/{student_id}", response_model=StudentResponse)
def update_student(student_id: int, student_update: StudentUpdate):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Student with ID {student_id} not found.")
        
    update_data = student_update.model_dump(exclude_unset=True)
    if not update_data:
        conn.close()
        return dict(existing)
        
    # Build dynamic SQL update query
    set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
    values = list(update_data.values()) + [student_id]
    
    try:
        cursor.execute(f"UPDATE students SET {set_clause} WHERE id = ?", values)
        conn.commit()
        
        cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
        updated_row = cursor.fetchone()
        conn.close()
        return dict(updated_row)
        
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered by another student.")

# 5. DELETE Student
@app.delete("/students/{student_id}")
def delete_student(student_id: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"Student with ID {student_id} not found.")
        
    cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
    
    return {"message": f"Student with ID {student_id} successfully deleted."}