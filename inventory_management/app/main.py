from fastapi import FastAPI
from app.core.config import settings
from app.routers import product, auth, users, file

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["Authentication"])
app.include_router(users.router, prefix=settings.API_V1_STR, tags=["User Management"])
app.include_router(product.router, prefix=settings.API_V1_STR, tags=["Products"])
app.include_router(file.router, prefix=settings.API_V1_STR, tags=["Files"])


@app.get("/")
def root():
    return {"message": "Inventory API is running"}