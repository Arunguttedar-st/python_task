from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field, ConfigDict
import sqlite3
from typing import Optional, List

DB_FILE = "library.db"

def init_db():
    """Initialize SQLite database tables."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Books Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            author TEXT NOT NULL,
            category TEXT NOT NULL,
            isbn TEXT UNIQUE NOT NULL,
            price REAL NOT NULL,
            available_quantity INTEGER NOT NULL
        )
    """)
    
    # Members Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone_number TEXT,
            membership_type TEXT
        )
    """)
    
    # Borrowings Table (tracks which member borrowed which book)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS borrowings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            book_id INTEGER,
            FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE CASCADE,
            FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern lifespan event handler for startup and shutdown."""
    init_db()
    yield

app = FastAPI(
    title="Library Management API",
    description="REST API built with FastAPI, Pydantic, and SQLite for managing books and library members.",
    version="1.0.0",
    lifespan=lifespan
)

# ==================== Pydantic Schemas ====================

class BookCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Book Name")
    author: str = Field(..., min_length=1, description="Author Name")
    category: str = Field(..., min_length=1, description="Category")
    isbn: str = Field(..., min_length=1, description="Unique ISBN")
    price: float = Field(..., gt=0, description="Price must be greater than 0")
    available_quantity: int = Field(..., ge=0, description="Quantity must be >= 0")

class BookUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    author: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, min_length=1)
    isbn: Optional[str] = Field(None, min_length=1)
    price: Optional[float] = Field(None, gt=0)
    available_quantity: Optional[int] = Field(None, ge=0)

class BookResponse(BookCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

class MemberCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Member Name")
    email: EmailStr = Field(..., description="Unique Email Address")
    phone_number: Optional[str] = None
    membership_type: Optional[str] = None

class MemberUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    membership_type: Optional[str] = None

class MemberResponse(MemberCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

# ==================== Database Helper ====================

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# ==================== Book APIs ====================

@app.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
def create_book(book: BookCreate):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO books (name, author, category, isbn, price, available_quantity) VALUES (?, ?, ?, ?, ?, ?)",
            (book.name, book.author, book.category, book.isbn, book.price, book.available_quantity)
        )
        conn.commit()
        book_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A book with this ISBN already exists."
        )
    conn.close()
    return {**book.model_dump(), "id": book_id}

@app.get("/books", response_model=List[BookResponse])
def get_books(
    category: Optional[str] = Query(None, description="Filter books by category"),
    author: Optional[str] = Query(None, description="Filter books by author")
):
    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT * FROM books WHERE 1=1"
    params = []
    
    if category:
        query += " AND category LIKE ?"
        params.append(f"%{category}%")
    if author:
        query += " AND author LIKE ?"
        params.append(f"%{author}%")
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

@app.get("/books/{book_id}", response_model=BookResponse)
def get_book(book_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return dict(row)

@app.put("/books/{book_id}", response_model=BookResponse)
def update_book(book_id: int, book: BookUpdate):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
        
    update_data = book.model_dump(exclude_unset=True)
    if not update_data:
        conn.close()
        return dict(existing)
        
    set_clause = ", ".join([f"{k} = ?" for k in update_data.keys()])
    values = list(update_data.values()) + [book_id]
    
    try:
        cursor.execute(f"UPDATE books SET {set_clause} WHERE id = ?", values)
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ISBN already exists for another book.")
        
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    updated = cursor.fetchone()
    conn.close()
    return dict(updated)

@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
        
    cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    return None

# ==================== Member APIs ====================

@app.post("/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def create_member(member: MemberCreate):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO members (name, email, phone_number, membership_type) VALUES (?, ?, ?, ?)",
            (member.name, member.email, member.phone_number, member.membership_type)
        )
        conn.commit()
        member_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A member with this email already exists."
        )
    conn.close()
    return {**member.model_dump(), "id": member_id}

@app.get("/members", response_model=List[MemberResponse])
def get_members():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/members/{member_id}", response_model=MemberResponse)
def get_member(member_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return dict(row)

@app.put("/members/{member_id}", response_model=MemberResponse)
def update_member(member_id: int, member: MemberUpdate):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
        
    update_data = member.model_dump(exclude_unset=True)
    if not update_data:
        conn.close()
        return dict(existing)
        
    set_clause = ", ".join([f"{k} = ?" for k in update_data.keys()])
    values = list(update_data.values()) + [member_id]
    
    try:
        cursor.execute(f"UPDATE members SET {set_clause} WHERE id = ?", values)
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists for another member.")
        
    cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))
    updated = cursor.fetchone()
    conn.close()
    return dict(updated)

@app.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(member_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
        
    cursor.execute("DELETE FROM members WHERE id = ?", (member_id,))
    conn.commit()
    conn.close()
    return None

# ==================== Borrow & Return APIs (Bonus) ====================

@app.post("/members/{member_id}/books/{book_id}/borrow", status_code=status.HTTP_200_OK)
def borrow_book(member_id: int, book_id: int):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
        
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    book = cursor.fetchone()
    if not book:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
        
    if book["available_quantity"] <= 0:
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Book is out of stock (available quantity is 0)")
        
    cursor.execute("UPDATE books SET available_quantity = available_quantity - 1 WHERE id = ?", (book_id,))
    cursor.execute("INSERT INTO borrowings (member_id, book_id) VALUES (?, ?)", (member_id, book_id))
    conn.commit()
    conn.close()
    
    return {"message": "Book borrowed successfully", "book_id": book_id, "member_id": member_id}

@app.post("/members/{member_id}/books/{book_id}/return", status_code=status.HTTP_200_OK)
def return_book(member_id: int, book_id: int):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
        
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
        
    cursor.execute("SELECT * FROM borrowings WHERE member_id = ? AND book_id = ?", (member_id, book_id))
    borrowing = cursor.fetchone()
    if not borrowing:
        conn.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This book was not borrowed by this member")
        
    cursor.execute("DELETE FROM borrowings WHERE id = ?", (borrowing["id"],))
    cursor.execute("UPDATE books SET available_quantity = available_quantity + 1 WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    
    return {"message": "Book returned successfully", "book_id": book_id, "member_id": member_id}