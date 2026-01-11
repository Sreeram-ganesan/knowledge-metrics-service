"""Metrics and analytics schemas.

This module contains schemas for:
- Period-based metrics aggregation
- Comparative analysis across vendors
- Drawdown analysis
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class PeriodMetricsResponse(BaseModel):
    """Aggregated metrics for a time period."""

    start_date: date = Field(description="Period start date")
    end_date: date = Field(description="Period end date")
    record_count: int = Field(description="Total records in period")
    vendor_count: int = Field(description="Number of vendors with data")

    # Aggregate statistics
    avg_signal_strength: float = Field(
        description="Average signal strength across all vendors"
    )
    signal_strength_std: float = Field(description="Signal strength standard deviation")
    total_drawdown_events: int = Field(description="Total drawdown events")

    # Per-vendor breakdown
    vendor_avg_signals: dict[str, float] = Field(
        description="Average signal per vendor"
    )
    vendor_drawdown_rates: dict[str, float] = Field(
        description="Drawdown rate per vendor"
    )


class ComparativeMetricsResponse(BaseModel):
    """Comparative analysis across vendors."""

    vendors: list[str] = Field(description="List of analyzed vendors")
    best_avg_signal: str = Field(description="Vendor with highest avg signal")
    lowest_drawdown_rate: str = Field(description="Vendor with lowest drawdown rate")
    highest_signal_volatility: str = Field(
        description="Vendor with highest signal volatility"
    )

    # Rankings (1 = best)
    ranking_by_avg_signal: dict[str, int] = Field(
        description="Ranking by average signal strength (1 = highest)"
    )
    ranking_by_stability: dict[str, int] = Field(
        description="Ranking by stability, i.e. lower volatility (1 = most stable)"
    )


class DrawdownAnalysisResponse(BaseModel):
    """Drawdown period analysis."""

    total_drawdown_events: int = Field(description="Total drawdown events")
    vendors_affected: list[str] = Field(description="Vendors with drawdowns")
    avg_signal_during_drawdown: Optional[float] = Field(
        default=None, description="Average signal during drawdowns"
    )
    drawdown_dates: list[str] = Field(description="Dates of drawdown events")
    by_vendor: Optional[dict[str, int]] = Field(
        default=None, description="Drawdown count per vendor"
    )
