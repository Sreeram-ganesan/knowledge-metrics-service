"""Knowledge & Metrics Service - FastAPI Application.

A backend service for evaluating alternative data vendors with:
- Vendor metrics and analytics
- Natural language query processing
- Statistical computations
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import API routers
from app.api.v1 import metrics_router, queries_router

# Import models
from app.models import HealthResponse

# Import middleware
from app.middleware import RequestIDMiddleware, LoggingMiddleware

# Import core of the application
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.exceptions import setup_exception_handlers

settings = get_settings()

# Configure logging based on settings
setup_logging(settings)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Internal Knowledge & Metrics Service for evaluating alternative data vendors. "
        "Provides vendor metrics, statistical analysis, and natural language query capabilities."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# =============================================================================
# Middleware Registration (IMPORTANT: Order is LIFO - Last added runs FIRST!)
# =============================================================================
# Execution order will be: RequestID → Logging → CORS → Your Endpoint
#
# We want:
# 1. RequestIDMiddleware FIRST (so ID is available for logging)
# 2. LoggingMiddleware SECOND (uses request ID from step 1)
# 3. CORSMiddleware THIRD (handles CORS headers)
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Logging middleware (logs requests/responses with timing)
app.add_middleware(LoggingMiddleware)

# 1. Requ pest ID middleware (adds X-Request-ID header for tracing) - RUNS FIRST!
app.add_middleware(RequestIDMiddleware)

# Setup global exception handlers
setup_exception_handlers(app)

# Register routers - when the no of routers increases, consider splitting into separate file like routes.py
app.include_router(metrics_router, prefix="/api/v1")
app.include_router(queries_router, prefix="/api/v1")


# Root and Health Endpoints
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with welcome message."""
    return {
        "message": "Knowledge & Metrics Service",
        "version": settings.app_version,
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint for container orchestration."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment,
    )
