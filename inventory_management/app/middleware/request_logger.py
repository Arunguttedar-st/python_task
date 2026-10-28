import time
import uuid
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract correlation ID from headers or generate a new one
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"FAILED | Method: {request.method} | Path: {request.url.path} | "
                f"Duration: {process_time:.2f}ms | Correlation-ID: {correlation_id} | Error: {str(e)}"
            )
            raise e
            
        process_time = (time.time() - start_time) * 1000
        
        # Attach correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        logger.info(
            f"SUCCESS | Method: {request.method} | Path: {request.url.path} | "
            f"Status: {response.status_code} | Duration: {process_time:.2f}ms | "
            f"Correlation-ID: {correlation_id}"
        )
        
        return response