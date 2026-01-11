"""Base schemas and common response models.

This module contains:
- Common response models used across the API
- Base classes and mixins for schema inheritance
"""

from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(default="healthy", description="Service health status")
    version: str = Field(description="API version")
    environment: str = Field(description="Deployment environment")


class ErrorResponse(BaseModel):
    """Standard error response.

    Used for consistent error formatting across all endpoints.
    """

    error: str = Field(description="Error type or code")
    message: str = Field(description="Human-readable error message")
    detail: Optional[str] = Field(default=None, description="Additional error details")
