"""
Custom Exception Handlers for SecureHall-RAG API
Phase 5B, Task 5B.2.5 - Centralized error handling with structured responses.
"""

import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("securehall-rag.errors")


def register_exception_handlers(app: FastAPI):
    """Register all custom exception handlers on the FastAPI app."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """Handle Pydantic validation errors with user-friendly messages."""
        request_id = getattr(request.state, "request_id", "unknown")
        errors = exc.errors()
        details = []
        for err in errors:
            field = " → ".join(str(loc) for loc in err.get("loc", []))
            msg = err.get("msg", "Invalid value")
            details.append(f"{field}: {msg}")

        logger.warning(
            f"[{request_id}] Validation error on {request.method} {request.url.path}: "
            f"{details}"
        )

        return JSONResponse(
            status_code=422,
            content={
                "detail": "Request validation failed.",
                "errors": details,
                "error_code": "VALIDATION_ERROR",
                "request_id": request_id,
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with consistent response format."""
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(
            f"[{request_id}] HTTP {exc.status_code} on "
            f"{request.method} {request.url.path}: {exc.detail}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error_code": f"HTTP_{exc.status_code}",
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Catch-all for any unhandled exceptions."""
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(
            f"[{request_id}] Unhandled error on "
            f"{request.method} {request.url.path}: {type(exc).__name__}: {exc}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An unexpected internal error occurred. Please try again later.",
                "error_code": "INTERNAL_SERVER_ERROR",
                "request_id": request_id,
            },
        )
