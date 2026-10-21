from fastapi import FastAPI
from app.routers import auth, users

app = FastAPI(title="Secure Inventory Management API", version="2.0.0")

# Include routers
app.include_router(auth.router)
app.include_router(users.router)


@app.get("/")
def read_root():
  return {
      "message": "Welcome to the Secure Inventory Management API. Visit /docs"
      " for Swagger UI."
  }