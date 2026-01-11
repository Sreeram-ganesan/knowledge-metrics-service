"""Vendor-related schemas.

This module contains schemas for:
- Vendor information
- Vendor metrics responses
- Vendor listings
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class VendorInfo(BaseModel):
    """Basic vendor information."""

    name: str = Field(description="Vendor name")
    universes: list[str] = Field(description="Asset classes/universes")
    record_count: int = Field(description="Number of data points")
    date_range: tuple[date, date] = Field(description="Data coverage period")


class VendorMetricsResponse(BaseModel):
    """Comprehensive metrics for a single vendor."""

    vendor: str = Field(description="Vendor name")
    universes: list[str] = Field(description="Asset classes/universes")
    record_count: int = Field(description="Number of data points analyzed")
    date_range: tuple[date, date] = Field(description="Analysis period")

    # Feature statistics
    feature_x_mean: float = Field(description="Mean of feature_x")
    feature_x_std: float = Field(description="Standard deviation of feature_x")
    feature_y_mean: float = Field(description="Mean of feature_y")
    feature_y_std: float = Field(description="Standard deviation of feature_y")

    # Signal strength analysis
    signal_strength_mean: float = Field(description="Average signal strength")
    signal_strength_std: float = Field(description="Signal strength volatility")
    signal_strength_min: float = Field(description="Minimum signal strength")
    signal_strength_max: float = Field(description="Maximum signal strength")

    # Drawdown analysis
    drawdown_count: int = Field(description="Number of drawdown periods")
    drawdown_rate: float = Field(description="Percentage of periods in drawdown (0-1)")

    # Derived metrics
    feature_xy_correlation: Optional[float] = Field(
        default=None,
        description="Pearson correlation between feature_x and feature_y. None if undefined (single data point or constant values).",
    )
    signal_volatility: Optional[float] = Field(
        default=None,
        description="Coefficient of variation (std/|mean|). None if mean ≈ 0.",
    )
    avg_signal_during_drawdown: Optional[float] = Field(
        default=None, description="Average signal during drawdown periods"
    )
    avg_signal_outside_drawdown: Optional[float] = Field(
        default=None, description="Average signal outside drawdown periods"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "vendor": "AlphaSignals",
                "universes": ["Equities"],
                "record_count": 10,
                "date_range": ["2020-01-03", "2020-03-06"],
                "feature_x_mean": 0.07,
                "feature_x_std": 0.0986,
                "feature_y_mean": 0.011,
                "feature_y_std": 0.0567,
                "signal_strength_mean": 0.266,
                "signal_strength_std": 0.1189,
                "signal_strength_min": 0.05,
                "signal_strength_max": 0.42,
                "drawdown_count": 3,
                "drawdown_rate": 0.3,
                "feature_xy_correlation": -0.8234,  # None if undefined
                "signal_volatility": 0.447,  # None if mean ≈ 0
                "avg_signal_during_drawdown": 0.1967,
                "avg_signal_outside_drawdown": 0.2957,
            }
        }
    )


class VendorListResponse(BaseModel):
    """List of vendors."""

    vendors: list[str] = Field(description="Available vendor names")
    count: int = Field(description="Number of vendors")


class DataInfoResponse(BaseModel):
    """Dataset information."""

    vendors: list[str] = Field(description="Available vendors")
    universes: list[str] = Field(description="Available universes")
    date_range: tuple[date, date] = Field(description="Data coverage")
    total_records: int = Field(description="Total data points")
