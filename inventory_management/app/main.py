from fastapi import FastAPI
from app.core.config import settings
from app.routers import product

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(product.router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
  return {"message": "Inventory API is running"}