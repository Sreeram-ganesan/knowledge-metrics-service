"""Metrics Service - Statistical computations for vendor analysis."""

from dataclasses import dataclass
from datetime import date
from typing import Optional

import numpy as np

from app.services.data_loader import DataLoaderService, get_data_loader
from app.core.exceptions import (
    VendorNotFoundError,
    InvalidDateRangeError,
    NotFoundError,
)


@dataclass
class VendorMetrics:
    """Computed metrics for a single vendor."""

    vendor: str
    universes: list[str]
    record_count: int
    date_range: tuple[date, date]

    # Feature statistics
    feature_x_mean: float
    feature_x_std: float
    feature_y_mean: float
    feature_y_std: float

    # Signal strength analysis
    signal_strength_mean: float
    signal_strength_std: float
    signal_strength_min: float
    signal_strength_max: float

    # Drawdown analysis
    drawdown_count: int
    drawdown_rate: float  # % of periods in drawdown

    # Derived metrics
    # Correlation is None when undefined (e.g., single data point)
    feature_xy_correlation: Optional[float]
    # CV = std / |mean|; None when mean ≈ 0
    signal_volatility: Optional[float]
    avg_signal_during_drawdown: Optional[float]
    avg_signal_outside_drawdown: Optional[float]


@dataclass
class PeriodMetrics:
    """Aggregated metrics for a time period across vendors."""

    start_date: date
    end_date: date
    record_count: int
    vendor_count: int

    # Cross-vendor statistics
    avg_signal_strength: float
    signal_strength_std: float
    total_drawdown_events: int

    # Per-vendor breakdown
    vendor_avg_signals: dict[str, float]
    vendor_drawdown_rates: dict[str, float]


@dataclass
class ComparativeMetrics:
    """Comparative analysis across all vendors."""

    vendors: list[str]
    best_avg_signal: str
    lowest_drawdown_rate: str
    highest_signal_volatility: str

    # Rankings (1 = best)
    ranking_by_avg_signal: dict[str, int]  # higher signal = better
    ranking_by_stability: dict[str, int]  # lower volatility = better


class MetricsService:
    """
    Service for computing statistical metrics on vendor data.

    Responsibilities:
    - Calculate per-vendor statistics (mean, std, volatility)
    - Compute drawdown analysis
    - Generate comparative metrics across vendors
    - Support period-based aggregations

    Uses: pandas for aggregations, numpy for numerical ops
    """

    def __init__(self, data_loader: Optional[DataLoaderService] = None):
        """
        Initialize metrics service.

        Args:
            data_loader: DataLoaderService instance. Uses singleton if not provided.
        """
        self._data_loader = data_loader or get_data_loader()

    def get_vendor_metrics(
        self,
        vendor: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> VendorMetrics:
        """
        Compute comprehensive metrics for a single vendor.

        Args:
            vendor: Vendor name.
            start_date: Optional start date filter.
            end_date: Optional end date filter.

        Returns:
            VendorMetrics: Computed statistics for the vendor.

        Raises:
            InvalidDateRangeError: If start_date is after or equal to end_date.
            VendorNotFoundError: If no data found for the vendor.
        """
        # Validate date range
        if start_date and end_date and start_date >= end_date:
            raise InvalidDateRangeError(
                start_date=str(start_date),
                end_date=str(end_date),
            )

        df = self._data_loader.get_vendor_data(vendor, start_date, end_date)

        # Handle empty DataFrame (vendor not found or no data in date range)
        if df is None or df.empty:
            available_vendors = self._data_loader.get_vendors()
            raise VendorNotFoundError(vendor, available=available_vendors)

        # Get all unique universes for this vendor
        universes = df["universe"].unique().tolist() if "universe" in df.columns else []

        # Ensure required columns exist - defensive check
        if (
            "feature_x" not in df.columns
            or "feature_y" not in df.columns
            or "signal_strength" not in df.columns
            or "drawdown_flag" not in df.columns
        ):
            raise NotFoundError(
                resource="Required data columns",
                identifier=f"vendor={vendor}",
                detail="One or more required columns (feature_x, feature_y, signal_strength, drawdown_flag) are missing.",
            )

        # Basic stats
        feature_x_mean = float(df["feature_x"].mean())
        feature_x_std = (
            float(df["feature_x"].std()) if len(df) > 1 else 0.0
        )  # If only one record, std deviation is 0
        feature_y_mean = float(df["feature_y"].mean())
        feature_y_std = (
            float(df["feature_y"].std()) if len(df) > 1 else 0.0
        )  # If only one record, std deviation is 0

        # Signal strength analysis
        signal_mean = float(df["signal_strength"].mean())
        signal_std = (
            float(df["signal_strength"].std()) if len(df) > 1 else 0.0
        )  # If only one record, std deviation is 0
        signal_min = float(df["signal_strength"].min())
        signal_max = float(df["signal_strength"].max())

        # Drawdown analysis
        drawdown_count = int(df["drawdown_flag"].sum())
        drawdown_rate = (
            drawdown_count / len(df) if len(df) > 0 else 0.0
        )  # Avoid division by zero

        # Correlation between features (Pearson)
        # Returns None when undefined (n=1 or constant values)
        if len(df) > 1:
            corr = df["feature_x"].corr(df["feature_y"])
            feature_xy_correlation = (
                round(float(corr), 4) if not np.isnan(corr) else None
            )
        else:
            feature_xy_correlation = None  # Undefined for single data point

        # Coefficient of Variation: CV = σ / |μ|
        # Only valid for ratio-scale data; uses abs(mean) to handle negative signals
        # Returns None when mean ≈ 0 (CV would be infinite/meaningless)
        if abs(signal_mean) > 1e-10:
            signal_volatility = round(signal_std / abs(signal_mean), 4)
        else:
            signal_volatility = None  # Undefined when mean is near zero

        # Signal during vs outside drawdown
        drawdown_df = df[df["drawdown_flag"] == 1]
        non_drawdown_df = df[df["drawdown_flag"] == 0]

        avg_signal_during_drawdown = (
            float(drawdown_df["signal_strength"].mean())
            if len(drawdown_df) > 0
            else None
        )
        avg_signal_outside_drawdown = (
            float(non_drawdown_df["signal_strength"].mean())
            if len(non_drawdown_df) > 0
            else None
        )

        return VendorMetrics(
            vendor=vendor,
            universes=universes,
            record_count=len(df),
            date_range=(
                df["date"].min().date(),
                df["date"].max().date(),
            ),
            feature_x_mean=round(feature_x_mean, 4),
            feature_x_std=round(feature_x_std, 4),
            feature_y_mean=round(feature_y_mean, 4),
            feature_y_std=round(feature_y_std, 4),
            signal_strength_mean=round(signal_mean, 4),
            signal_strength_std=round(signal_std, 4),
            signal_strength_min=round(signal_min, 4),
            signal_strength_max=round(signal_max, 4),
            drawdown_count=drawdown_count,
            drawdown_rate=round(drawdown_rate, 4),
            feature_xy_correlation=feature_xy_correlation,
            signal_volatility=signal_volatility,
            avg_signal_during_drawdown=(
                round(avg_signal_during_drawdown, 4)
                if avg_signal_during_drawdown is not None
                else None
            ),
            avg_signal_outside_drawdown=(
                round(avg_signal_outside_drawdown, 4)
                if avg_signal_outside_drawdown is not None
                else None
            ),
        )

    def get_period_metrics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> PeriodMetrics:
        """
        Compute aggregated metrics for a time period across all vendors.

        Args:
            start_date: Period start date.
            end_date: Period end date.

        Returns:
            PeriodMetrics: Aggregated statistics for the period.
        """
        df = self._data_loader.get_data_by_date_range(start_date, end_date)

        if df.empty:
            # Return empty metrics
            return PeriodMetrics(
                start_date=start_date or date.min,
                end_date=end_date or date.max,
                record_count=0,
                vendor_count=0,
                avg_signal_strength=0.0,
                signal_strength_std=0.0,
                total_drawdown_events=0,
                vendor_avg_signals={},
                vendor_drawdown_rates={},
            )

        # Actual date range from data
        actual_start = df["date"].min().date()
        actual_end = df["date"].max().date()

        # Per-vendor aggregations
        vendor_stats = df.groupby("vendor").agg(
            {
                "signal_strength": "mean",
                "drawdown_flag": ["sum", "count"],
            }
        )

        vendor_avg_signals: dict[str, float] = (
            vendor_stats[("signal_strength", "mean")].round(4).to_dict()
        )

        drawdown_sums = vendor_stats[("drawdown_flag", "sum")]
        drawdown_counts = vendor_stats[("drawdown_flag", "count")]
        vendor_drawdown_rates: dict[str, float] = (
            (drawdown_sums / drawdown_counts).round(4).to_dict()
        )

        return PeriodMetrics(
            start_date=actual_start,
            end_date=actual_end,
            record_count=len(df),
            vendor_count=df["vendor"].nunique(),
            avg_signal_strength=round(float(df["signal_strength"].mean()), 4),
            signal_strength_std=round(float(df["signal_strength"].std()), 4),
            total_drawdown_events=int(df["drawdown_flag"].sum()),
            vendor_avg_signals=vendor_avg_signals,
            vendor_drawdown_rates=vendor_drawdown_rates,
        )

    def get_comparative_metrics(self) -> ComparativeMetrics:
        """
        Generate comparative analysis across all vendors.

        Returns:
            ComparativeMetrics: Rankings and comparisons.
        """
        vendors = self._data_loader.get_vendors()

        # Compute metrics for each vendor
        vendor_metrics = {v: self.get_vendor_metrics(v) for v in vendors}

        # Find best performers
        signal_scores = {v: m.signal_strength_mean for v, m in vendor_metrics.items()}
        drawdown_rates = {v: m.drawdown_rate for v, m in vendor_metrics.items()}
        # Filter out None volatilities for comparison
        volatilities = {
            v: m.signal_volatility
            for v, m in vendor_metrics.items()
            if m.signal_volatility is not None
        }

        best_avg_signal = max(signal_scores, key=lambda v: signal_scores[v])
        lowest_drawdown_rate = min(drawdown_rates, key=lambda v: drawdown_rates[v])
        # Fallback to first vendor if all volatilities are None
        highest_signal_volatility = (
            max(volatilities, key=lambda v: volatilities[v])
            if volatilities
            else vendors[0]
        )

        # Rankings (1 = best)
        ranking_by_avg_signal = {
            v: rank
            for rank, (v, _) in enumerate(
                sorted(signal_scores.items(), key=lambda x: -x[1]), 1
            )
        }

        # Lower volatility = more stable = better rank
        ranking_by_stability = {
            v: rank
            for rank, (v, _) in enumerate(
                sorted(volatilities.items(), key=lambda x: x[1]), 1
            )
        }

        return ComparativeMetrics(
            vendors=vendors,
            best_avg_signal=best_avg_signal,
            lowest_drawdown_rate=lowest_drawdown_rate,
            highest_signal_volatility=highest_signal_volatility,
            ranking_by_avg_signal=ranking_by_avg_signal,
            ranking_by_stability=ranking_by_stability,
        )

    def get_drawdown_analysis(
        self,
        vendor: Optional[str] = None,
    ) -> dict:
        """
        Detailed analysis of drawdown periods.

        Args:
            vendor: Optional vendor filter.

        Returns:
            dict: Drawdown statistics and patterns.
        """
        df = self._data_loader.get_drawdown_periods(vendor)

        if df.empty:
            return {
                "total_drawdown_events": 0,
                "vendors_affected": [],
                "avg_signal_during_drawdown": None,
                "drawdown_dates": [],
            }

        return {
            "total_drawdown_events": len(df),
            "vendors_affected": df["vendor"].unique().tolist(),
            "avg_signal_during_drawdown": round(float(df["signal_strength"].mean()), 4),
            "drawdown_dates": df["date"].dt.strftime("%Y-%m-%d").tolist(),  # type: ignore[union-attr]
            "by_vendor": df.groupby("vendor").size().to_dict(),
        }


def get_metrics_service() -> MetricsService:
    """Factory function for MetricsService (for FastAPI dependency injection)."""
    return MetricsService()
