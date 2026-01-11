"""Request ID Middleware - Adds correlation IDs for distributed tracing.

Every request gets a unique ID that:
- Is returned in response headers (X-Request-ID)
- Can be passed in by clients (for end-to-end tracing)
- Is available throughout the request lifecycle via contextvars

Go equivalent: You'd use context.Context with a request ID value.
"""

import uuid
from contextvars import ContextVar
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# ContextVar allows us to store request-scoped data (like Go's context.Context)
# This is thread-safe and works with async code
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_request_id() -> Optional[str]:
    """Get the current request ID from context.

    Use this anywhere in your code to get the current request's ID:

        from app.middleware.request_id import get_request_id

        def some_function():
            rid = get_request_id()
            logger.info(f"[{rid}] Processing...")
    """
    return request_id_var.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that assigns a unique request ID to each request.

    Features:
    - Generates UUID4 if client doesn't provide X-Request-ID header
    - Stores ID in ContextVar for access anywhere in the request
    - Adds X-Request-ID to response headers for client correlation

    Usage in app/__init__.py:
        from app.middleware import RequestIDMiddleware
        app.add_middleware(RequestIDMiddleware)
    """

    HEADER_NAME = "X-Request-ID"

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Check if client provided a request ID (for end-to-end tracing)
        request_id = request.headers.get(self.HEADER_NAME)

        # Generate new ID if not provided
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in context for this request's lifecycle
        token = request_id_var.set(request_id)

        try:
            # Process the request
            response = await call_next(request)

            # Add request ID to response headers
            response.headers[self.HEADER_NAME] = request_id

            return response
        finally:
            # Reset context (cleanup)
            request_id_var.reset(token)
