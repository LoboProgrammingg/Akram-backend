"""
Middleware configuration for the application.
Includes Correlation ID setup and request logging middleware.
"""

import time
import structlog
from typing import Callable
from fastapi import Request, Response
from asgi_correlation_id import CorrelationIdMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log requests and responses with timing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Log request start
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        )

        try:
            response = await call_next(request)
            
            process_time = time.time() - start_time
            
            # Log request completion
            logger.info(
                "Request completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
            )
            
            return response
            
        except Exception:
            process_time = time.time() - start_time
            logger.exception(
                "Request failed",
                method=request.method,
                path=request.url.path,
                process_time_ms=round(process_time * 1000, 2),
            )
            raise


def setup_middleware(app):
    """Setup all middleware for the application."""
    
    # 1. Correlation ID (Must be first to ensure ID is available for subsequent middleware)
    app.add_middleware(
        CorrelationIdMiddleware,
        header_name="X-Request-ID",
        update_request_header=True,
    )
    
    # 2. Request Logging
    app.add_middleware(RequestLoggingMiddleware)
