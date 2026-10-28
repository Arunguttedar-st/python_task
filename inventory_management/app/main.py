from fastapi import FastAPI
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import register_exception_handlers
from app.middleware.request_logger import RequestLoggingMiddleware
from app.routers import product, auth, users, file

# 1. Initialize logging on startup
setup_logging()

app = FastAPI(title=settings.PROJECT_NAME)

# 2. Add Request Logging Middleware (wraps requests for tracking & correlation IDs)
app.add_middleware(RequestLoggingMiddleware)

# 3. Register Centralized Exception Handlers (catches custom & global errors safely)
register_exception_handlers(app)

# 4. Include your API Routers
app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["Authentication"])
app.include_router(users.router, prefix=settings.API_V1_STR, tags=["User Management"])
app.include_router(product.router, prefix=settings.API_V1_STR, tags=["Products"])
app.include_router(file.router, prefix=settings.API_V1_STR, tags=["Files"])


@app.get("/")
def root():
    return {"message": "Inventory API is running"}