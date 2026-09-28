from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field
import sqlite3
from typing import Optional, List

app = FastAPI(title="Product Management API", version="1.0.0")

DB_FILE = "products.db"

# Initialize SQLite Database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()

@app.on_event("startup")
def startup_event():
    init_db()

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Allows dictionary-like access to rows
    return conn

# --- Pydantic Models for Validation ---
class ProductCreate(BaseModel):
    product_id: str = Field(..., min_length=1, description="Unique identifier for the product")
    name: str = Field(..., min_length=1, description="Name of the product")
    category: str = Field(..., min_length=1, description="Category name (e.g., Electronics)")
    price: float = Field(..., gt=0, description="Price must be greater than 0")
    quantity: int = Field(..., gt=0, description="Quantity must be greater than 0")

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, min_length=1)
    price: Optional[float] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, gt=0)


# --- API Endpoints ---

@app.post("/products", status_code=status.HTTP_201_CREATED, summary="Create a new product")
def create_product(product: ProductCreate):
    conn = get_db()
    cursor = conn.cursor()
    
    # Check for duplicate Product ID
    cursor.execute("SELECT * FROM products WHERE product_id = ?", (product.product_id,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product ID '{product.product_id}' already exists."
        )
    
    cursor.execute(
        "INSERT INTO products (product_id, name, category, price, quantity) VALUES (?, ?, ?, ?, ?)",
        (product.product_id, product.name, product.category, product.price, product.quantity)
    )
    conn.commit()
    conn.close()
    
    return {"message": "Product created successfully", "product": product}


@app.get("/products", summary="Get all products or filter by category (Bonus)")
def get_products(category: Optional[str] = Query(None, description="Filter products by category")):
    conn = get_db()
    cursor = conn.cursor()
    
    if category:
        cursor.execute("SELECT * FROM products WHERE category = ?", (category,))
    else:
        cursor.execute("SELECT * FROM products")
        
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


@app.get("/products/{product_id}", summary="Get a single product by ID")
def get_product(product_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product ID '{product_id}' not found."
        )
        
    return dict(row)


@app.put("/products/{product_id}", summary="Update an existing product")
def update_product(product_id: str, product_update: ProductUpdate):
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if product exists
    cursor.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product ID '{product_id}' not found."
        )
        
    current = dict(row)
    
    # Update fields if provided, otherwise keep existing values
    new_name = product_update.name if product_update.name is not None else current["name"]
    new_category = product_update.category if product_update.category is not None else current["category"]
    new_price = product_update.price if product_update.price is not None else current["price"]
    new_quantity = product_update.quantity if product_update.quantity is not None else current["quantity"]
    
    cursor.execute(
        "UPDATE products SET name = ?, category = ?, price = ?, quantity = ? WHERE product_id = ?",
        (new_name, new_category, new_price, new_quantity, product_id)
    )
    conn.commit()
    conn.close()
    
    return {
        "message": "Product updated successfully",
        "product": {
            "product_id": product_id,
            "name": new_name,
            "category": new_category,
            "price": new_price,
            "quantity": new_quantity
        }
    }


@app.delete("/products/{product_id}", summary="Delete a product")
def delete_product(product_id: str):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product ID '{product_id}' not found."
        )
        
    cursor.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
    conn.commit()
    conn.close()
    
    return {"message": f"Product ID '{product_id}' deleted successfully."}