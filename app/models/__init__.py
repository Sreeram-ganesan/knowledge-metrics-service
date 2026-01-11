"""Models package - Pydantic schemas for API contracts.

Schemas are organized by domain:
- base.py: Common response models (ErrorResponse, HealthResponse)
- vendor.py: Vendor-related schemas
- metrics.py: Analytics and metrics schemas
- query.py: Natural language query schemas

Import directly from this package:
    from app.models import VendorMetricsResponse, QueryRequest
"""

# Base/Common
from app.models.base import (
    ErrorResponse,
    HealthResponse,
)

# Vendor
from app.models.vendor import (
    DataInfoResponse,
    VendorInfo,
    VendorListResponse,
    VendorMetricsResponse,
)

# Metrics
from app.models.metrics import (
    ComparativeMetricsResponse,
    DrawdownAnalysisResponse,
    PeriodMetricsResponse,
)

# Query
from app.models.query import (
    QueryEntities,
    QueryRequest,
    QueryResponse,
    SupportedQueryResponse,
)

__all__ = [
    # Base
    "ErrorResponse",
    "HealthResponse",
    # Vendor
    "DataInfoResponse",
    "VendorInfo",
    "VendorListResponse",
    "VendorMetricsResponse",
    # Metrics
    "ComparativeMetricsResponse",
    "DrawdownAnalysisResponse",
    "PeriodMetricsResponse",
    # Query
    "QueryEntities",
    "QueryRequest",
    "QueryResponse",
    "SupportedQueryResponse",
]
