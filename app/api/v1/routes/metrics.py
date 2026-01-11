"""Metrics API v1 routes.

Endpoints for vendor metrics, period aggregations, and comparisons.
"""

from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.models import (
    ComparativeMetricsResponse,
    DataInfoResponse,
    DrawdownAnalysisResponse,
    PeriodMetricsResponse,
    VendorMetricsResponse,
)
from app.services import (
    DataLoaderService,
    MetricsService,
    get_data_loader,
    get_metrics_service,
)

router = APIRouter(prefix="/metrics", tags=["Metrics v1"])


# Type aliases for dependency injection
DataLoaderDep = Annotated[DataLoaderService, Depends(get_data_loader)]
MetricsServiceDep = Annotated[MetricsService, Depends(get_metrics_service)]


@router.get(
    "/info",
    response_model=DataInfoResponse,
    summary="Get dataset information",
    description="Returns metadata about the available data: vendors, universes, date range.",
)
async def get_data_info(data_loader: DataLoaderDep) -> DataInfoResponse:
    """Get information about the available dataset."""
    df = data_loader.dataframe
    min_date, max_date = data_loader.get_date_range()

    return DataInfoResponse(
        vendors=data_loader.get_vendors(),
        universes=data_loader.get_universes(),
        date_range=(min_date, max_date),
        total_records=len(df),
    )


@router.post(
    "/upload",
    response_model=dict,
    summary="Upload new dataset",
    description="Upload a CSV file to replace the current dataset. Includes validation and size limits.",
)
async def upload_data_file(
    file: Annotated[UploadFile, File(description="CSV file to upload")],
    data_loader: DataLoaderDep,
) -> dict:
    """Upload a new dataset with validation.

    Features:
    - File size limit (10MB)
    - Content-type validation
    - Streaming read for memory efficiency
    """
    result = await data_loader.load_data_from_upload(
        read_chunk=file.read,
        content_type=file.content_type,
        filename=file.filename,
    )
    return {"message": "Data uploaded successfully", **result}


@router.get(
    "/vendors/{vendor}",
    response_model=VendorMetricsResponse,
    summary="Get vendor metrics",
    description="Returns comprehensive metrics for a specific vendor with optional date filtering.",
    responses={
        400: {"description": "Invalid date range (start_date must be before end_date)"},
        404: {"description": "Vendor not found"},
    },
)
async def get_vendor_metrics(
    vendor: str,
    metrics_service: MetricsServiceDep,
    start_date: Annotated[
        Optional[date],
        Query(description="Filter data from this date (YYYY-MM-DD)"),
    ] = None,
    end_date: Annotated[
        Optional[date],
        Query(description="Filter data until this date (YYYY-MM-DD)"),
    ] = None,
) -> VendorMetricsResponse:
    """Get comprehensive metrics for a single vendor.

    Note: ValueError from service layer is caught by global exception handler.
    """
    # No try/except needed - global handler catches ValueError
    metrics = metrics_service.get_vendor_metrics(vendor, start_date, end_date)
    return VendorMetricsResponse(
        vendor=metrics.vendor,
        universes=metrics.universes,
        record_count=metrics.record_count,
        date_range=metrics.date_range,
        feature_x_mean=metrics.feature_x_mean,
        feature_x_std=metrics.feature_x_std,
        feature_y_mean=metrics.feature_y_mean,
        feature_y_std=metrics.feature_y_std,
        signal_strength_mean=metrics.signal_strength_mean,
        signal_strength_std=metrics.signal_strength_std,
        signal_strength_min=metrics.signal_strength_min,
        signal_strength_max=metrics.signal_strength_max,
        drawdown_count=metrics.drawdown_count,
        drawdown_rate=metrics.drawdown_rate,
        feature_xy_correlation=metrics.feature_xy_correlation,
        signal_volatility=metrics.signal_volatility,
        avg_signal_during_drawdown=metrics.avg_signal_during_drawdown,
        avg_signal_outside_drawdown=metrics.avg_signal_outside_drawdown,
    )


@router.get(
    "/period",
    response_model=PeriodMetricsResponse,
    summary="Get period metrics",
    description="Returns aggregated metrics for a time period across all vendors.",
)
async def get_period_metrics(
    metrics_service: MetricsServiceDep,
    start_date: Annotated[
        Optional[date],
        Query(description="Period start date (YYYY-MM-DD)"),
    ] = None,
    end_date: Annotated[
        Optional[date],
        Query(description="Period end date (YYYY-MM-DD)"),
    ] = None,
) -> PeriodMetricsResponse:
    """Get aggregated metrics for a time period."""
    period = metrics_service.get_period_metrics(start_date, end_date)
    return PeriodMetricsResponse(
        start_date=period.start_date,
        end_date=period.end_date,
        record_count=period.record_count,
        vendor_count=period.vendor_count,
        avg_signal_strength=period.avg_signal_strength,
        signal_strength_std=period.signal_strength_std,
        total_drawdown_events=period.total_drawdown_events,
        vendor_avg_signals=period.vendor_avg_signals,
        vendor_drawdown_rates=period.vendor_drawdown_rates,
    )


@router.get(
    "/compare",
    response_model=ComparativeMetricsResponse,
    summary="Compare all vendors",
    description="Returns comparative analysis and rankings across all vendors.",
)
async def compare_vendors(
    metrics_service: MetricsServiceDep,
) -> ComparativeMetricsResponse:
    """Compare metrics across all vendors."""
    comparison = metrics_service.get_comparative_metrics()
    return ComparativeMetricsResponse(
        vendors=comparison.vendors,
        best_avg_signal=comparison.best_avg_signal,
        lowest_drawdown_rate=comparison.lowest_drawdown_rate,
        highest_signal_volatility=comparison.highest_signal_volatility,
        ranking_by_avg_signal=comparison.ranking_by_avg_signal,
        ranking_by_stability=comparison.ranking_by_stability,
    )


@router.get(
    "/drawdowns",
    response_model=DrawdownAnalysisResponse,
    summary="Analyze drawdowns",
    description="Returns analysis of drawdown/stress periods.",
)
async def get_drawdown_analysis(
    metrics_service: MetricsServiceDep,
    vendor: Annotated[
        Optional[str],
        Query(description="Filter by vendor name"),
    ] = None,
) -> DrawdownAnalysisResponse:
    """Get detailed drawdown analysis."""
    analysis = metrics_service.get_drawdown_analysis(vendor)
    return DrawdownAnalysisResponse(
        total_drawdown_events=analysis["total_drawdown_events"],
        vendors_affected=analysis["vendors_affected"],
        avg_signal_during_drawdown=analysis.get("avg_signal_during_drawdown"),
        drawdown_dates=analysis.get("drawdown_dates", []),
        by_vendor=analysis.get("by_vendor"),
    )
