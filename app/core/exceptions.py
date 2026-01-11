"""Exception Handling - Custom exceptions and global handlers.

Provides:
- Custom exception hierarchy for domain errors
- Global exception handlers that return consistent JSON responses
- Automatic logging of exceptions with request ID

This is core infrastructure, not middleware.
"""

import logging
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.middleware.request_id import get_request_id
from app.models import ErrorResponse

logger = logging.getLogger("app.exceptions")


# =============================================================================
# Custom Exception Hierarchy
# =============================================================================


class AppException(Exception):
    """Base exception for all application errors.

    Subclass this for domain-specific errors:

        class VendorNotFoundError(AppException):
            def __init__(self, vendor: str):
                super().__init__(
                    message=f"Vendor '{vendor}' not found",
                    error_code="VENDOR_NOT_FOUND",
                    status_code=404,
                )
    """

    def __init__(
        self,
        message: str,
        error_code: str = "APP_ERROR",
        status_code: int = 500,
        detail: Optional[str] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class NotFoundError(AppException):
    """Resource not found (404)."""

    def __init__(self, resource: str, identifier: str, detail: Optional[str] = None):
        super().__init__(
            message=f"{resource} '{identifier}' not found",
            error_code=f"{resource.upper()}_NOT_FOUND",
            status_code=404,
            detail=detail,
        )


class ValidationError(AppException):
    """Invalid input data (400)."""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            detail=detail,
        )


class ServiceError(AppException):
    """Service layer error (500)."""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="SERVICE_ERROR",
            status_code=500,
            detail=detail,
        )


# =============================================================================
# Specific Domain Exceptions
# =============================================================================


class VendorNotFoundError(NotFoundError):
    """Specific error for vendor not found."""

    def __init__(self, vendor: str, available: Optional[list[str]] = None):
        detail = f"Available vendors: {', '.join(available)}" if available else None
        super().__init__(resource="Vendor", identifier=vendor, detail=detail)


class NoDataInRangeError(ValidationError):
    """No data available in the specified date range."""

    def __init__(self, start_date: str, end_date: str):
        super().__init__(
            message="No data available in the specified date range",
            detail=f"No data found between {start_date} and {end_date}",
        )


class InvalidDateRangeError(ValidationError):
    """Invalid date range provided."""

    def __init__(self, start_date: str, end_date: str):
        super().__init__(
            message="Invalid date range",
            detail=f"start_date ({start_date}) must be before end_date ({end_date})",
        )


class FileTooLargeError(AppException):
    """Uploaded file exceeds size limit (413)."""

    def __init__(self, max_size_mb: int):
        super().__init__(
            message=f"File too large. Maximum size: {max_size_mb}MB",
            error_code="FILE_TOO_LARGE",
            status_code=413,
        )


# =============================================================================
# Global Exception Handlers
# =============================================================================


def setup_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app.

    Call this in main.py:
        from app.core.exceptions import setup_exception_handlers
        setup_exception_handlers(app)
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request, exc: AppException
    ) -> JSONResponse:
        """Handle all AppException subclasses."""
        request_id = get_request_id()

        # Log the error
        logger.warning(
            f"[{request_id}] {exc.error_code}: {exc.message}"
            + (f" | {exc.detail}" if exc.detail else "")
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.error_code,
                message=exc.message,
                detail=exc.detail,
            ).model_dump(),
            headers={"X-Request-ID": request_id} if request_id else {},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """Handle ValueError (often from service layer validation)."""
        request_id = get_request_id()

        logger.warning(f"[{request_id}] ValueError: {exc}")

        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error="VALIDATION_ERROR",
                message=str(exc),
                detail=None,
            ).model_dump(),
            headers={"X-Request-ID": request_id} if request_id else {},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Catch-all handler for unexpected exceptions.

        IMPORTANT: Never expose internal error details to clients in production!
        """
        request_id = get_request_id()

        # Log full exception for debugging
        logger.exception(f"[{request_id}] Unhandled exception: {type(exc).__name__}")

        # Return generic message to client (security: don't leak internals)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="INTERNAL_ERROR",
                message="An unexpected error occurred",
                detail=f"Request ID: {request_id}" if request_id else None,
            ).model_dump(),
            headers={"X-Request-ID": request_id} if request_id else {},
        )
