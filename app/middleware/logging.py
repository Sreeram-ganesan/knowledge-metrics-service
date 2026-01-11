"""Request Logging Middleware - HTTP request/response logging.

Provides:
- Request logging (method, path, client IP)
- Response logging (status code, duration)
- Automatic correlation with request ID

For logging configuration (formatters, setup), see app.core.logging.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.middleware.request_id import get_request_id

# Logger for request/response events
logger = logging.getLogger("app.request")


# These logs are - application level logs, not access logs - example:
# INFO  [abc-123] → GET /api/v1/metrics/vendors
# INFO  [abc-123] ← 200 OK (45.23ms)
# For handling access logs, separate it into core folder where app-wide concerns are handled., ex: access logging, db connection pooling, etc.
class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured request/response logging.

    Logs:
    - Incoming requests: method, path, client IP, request ID
    - Outgoing responses: status code, duration in ms

    Example log output:
        INFO  [abc-123] → GET /api/v1/metrics/vendors
        INFO  [abc-123] ← 200 OK (45.23ms)

    Usage:
        app.add_middleware(LoggingMiddleware)
    """

    # Paths to skip logging (health checks, etc.)
    SKIP_PATHS = {"/health", "/", "/docs", "/redoc", "/openapi.json"}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip logging for noisy endpoints
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        request_id = get_request_id() or "no-id"
        method = request.method
        path = request.url.path
        query = str(request.query_params) if request.query_params else ""
        client_ip = self._get_client_ip(request)

        # Log incoming request
        logger.info(
            f"[{request_id}] → {method} {path}"
            + (f"?{query}" if query else "")
            + f" (client: {client_ip})"
        )

        # Time the request
        start_time = time.perf_counter()

        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log response
            status = response.status_code
            log_level = logging.WARNING if status >= 400 else logging.INFO
            logger.log(log_level, f"[{request_id}] ← {status} ({duration_ms:.2f}ms)")

            return response

        except Exception as e:
            # Log exception (will be re-raised)
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[{request_id}] ✗ Exception: {type(e).__name__}: {e} ({duration_ms:.2f}ms)"
            )
            raise

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, considering proxy headers."""
        # Check X-Forwarded-For header (when behind load balancer/proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP (original client)
            return forwarded.split(",")[0].strip()

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"
