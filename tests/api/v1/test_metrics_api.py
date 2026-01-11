"""Unit tests for Metrics API v1 endpoints.

Following the same dependency injection pattern as test_queries_api.py,
we override dependencies to test the route layer in isolation.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import get_data_loader, get_metrics_service


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_data_loader():
    """Create a mock DataLoaderService."""
    mock = MagicMock()
    mock.dataframe = MagicMock()
    mock.get_vendors.return_value = ["Vendor_A", "Vendor_B"]
    mock.get_universes.return_value = ["Universe_1", "Universe_2"]
    mock.get_date_range.return_value = (date(2023, 1, 1), date(2023, 12, 31))
    mock.dataframe.__len__.return_value = 1000
    mock.load_data_from_upload = AsyncMock(return_value={"records": 1000, "vendors": 2})
    return mock


@pytest.fixture
def mock_metrics_service():
    """Create a mock MetricsService."""
    mock = MagicMock()

    # Mock vendor metrics
    vendor_metrics = MagicMock()
    vendor_metrics.vendor = "Vendor_A"
    vendor_metrics.universes = ["Universe_1"]
    vendor_metrics.record_count = 500
    vendor_metrics.date_range = (date(2023, 1, 1), date(2023, 12, 31))
    vendor_metrics.feature_x_mean = 1.5
    vendor_metrics.feature_x_std = 0.5
    vendor_metrics.feature_y_mean = 2.0
    vendor_metrics.feature_y_std = 0.6
    vendor_metrics.signal_strength_mean = 0.75
    vendor_metrics.signal_strength_std = 0.15
    vendor_metrics.signal_strength_min = 0.2
    vendor_metrics.signal_strength_max = 0.95
    vendor_metrics.drawdown_count = 10
    vendor_metrics.drawdown_rate = 0.02
    vendor_metrics.feature_xy_correlation = 0.8
    vendor_metrics.signal_volatility = 0.12
    vendor_metrics.avg_signal_during_drawdown = 0.65
    vendor_metrics.avg_signal_outside_drawdown = 0.78
    mock.get_vendor_metrics.return_value = vendor_metrics

    # Mock period metrics
    period_metrics = MagicMock()
    period_metrics.start_date = date(2023, 1, 1)
    period_metrics.end_date = date(2023, 12, 31)
    period_metrics.record_count = 1000
    period_metrics.vendor_count = 2
    period_metrics.avg_signal_strength = 0.72
    period_metrics.signal_strength_std = 0.18
    period_metrics.total_drawdown_events = 25
    period_metrics.vendor_avg_signals = {"Vendor_A": 0.75, "Vendor_B": 0.69}
    period_metrics.vendor_drawdown_rates = {"Vendor_A": 0.02, "Vendor_B": 0.03}
    mock.get_period_metrics.return_value = period_metrics

    # Mock comparative metrics
    comparative_metrics = MagicMock()
    comparative_metrics.vendors = ["Vendor_A", "Vendor_B"]
    comparative_metrics.best_avg_signal = "Vendor_A"
    comparative_metrics.lowest_drawdown_rate = "Vendor_A"
    comparative_metrics.highest_signal_volatility = "Vendor_B"
    comparative_metrics.ranking_by_avg_signal = {"Vendor_A": 1, "Vendor_B": 2}
    comparative_metrics.ranking_by_stability = {"Vendor_A": 1, "Vendor_B": 2}
    mock.get_comparative_metrics.return_value = comparative_metrics

    # Mock drawdown analysis
    mock.get_drawdown_analysis.return_value = {
        "total_drawdown_events": 25,
        "vendors_affected": ["Vendor_A", "Vendor_B"],
        "avg_signal_during_drawdown": 0.65,
        "drawdown_dates": ["2023-03-15", "2023-07-22"],
        "by_vendor": {"Vendor_A": 10, "Vendor_B": 15},
    }

    return mock


@pytest.fixture
def override_dependencies(mock_data_loader, mock_metrics_service):
    """Override both DataLoader and MetricsService dependencies."""
    app.dependency_overrides[get_data_loader] = lambda: mock_data_loader
    app.dependency_overrides[get_metrics_service] = lambda: mock_metrics_service
    yield mock_data_loader, mock_metrics_service
    app.dependency_overrides.clear()


# =============================================================================
# Tests
# =============================================================================


def test_get_data_info(client: TestClient, override_dependencies):
    """Test GET /api/v1/metrics/info endpoint."""
    response = client.get("/api/v1/metrics/info")

    assert response.status_code == 200
    data = response.json()
    assert data["vendors"] == ["Vendor_A", "Vendor_B"]
    assert data["universes"] == ["Universe_1", "Universe_2"]
    assert data["total_records"] == 1000
    assert data["date_range"] == ["2023-01-01", "2023-12-31"]


def test_upload_data_file(client: TestClient, override_dependencies):
    """Test POST /api/v1/metrics/upload endpoint."""
    file_content = (
        b"date,vendor,universe,feature_x,feature_y,signal_strength,drawdown_flag\n"
    )

    response = client.post(
        "/api/v1/metrics/upload",
        files={"file": ("test.csv", file_content, "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Data uploaded successfully"
    assert data["records"] == 1000
    assert data["vendors"] == 2


def test_get_vendor_metrics(client: TestClient, override_dependencies):
    """Test GET /api/v1/metrics/vendors/{vendor} endpoint."""
    response = client.get("/api/v1/metrics/vendors/Vendor_A")

    assert response.status_code == 200
    data = response.json()
    assert data["vendor"] == "Vendor_A"
    assert data["record_count"] == 500
    assert data["feature_x_mean"] == 1.5
    assert data["signal_strength_mean"] == 0.75
    assert data["drawdown_count"] == 10
    assert data["date_range"] == ["2023-01-01", "2023-12-31"]


def test_get_vendor_metrics_with_date_filters(
    client: TestClient, override_dependencies
):
    """Test GET /api/v1/metrics/vendors/{vendor} with date filters."""
    response = client.get(
        "/api/v1/metrics/vendors/Vendor_A",
        params={"start_date": "2023-06-01", "end_date": "2023-12-31"},
    )

    assert response.status_code == 200
    mock_data_loader, mock_metrics_service = override_dependencies
    mock_metrics_service.get_vendor_metrics.assert_called_once()


def test_get_period_metrics(client: TestClient, override_dependencies):
    """Test GET /api/v1/metrics/period endpoint."""
    response = client.get("/api/v1/metrics/period")

    assert response.status_code == 200
    data = response.json()
    assert data["record_count"] == 1000
    assert data["vendor_count"] == 2
    assert data["avg_signal_strength"] == 0.72
    assert data["total_drawdown_events"] == 25
    assert "Vendor_A" in data["vendor_avg_signals"]


def test_compare_vendors(client: TestClient, override_dependencies):
    """Test GET /api/v1/metrics/compare endpoint."""
    response = client.get("/api/v1/metrics/compare")

    assert response.status_code == 200
    data = response.json()
    assert data["vendors"] == ["Vendor_A", "Vendor_B"]
    assert data["best_avg_signal"] == "Vendor_A"
    assert data["lowest_drawdown_rate"] == "Vendor_A"
    assert data["ranking_by_avg_signal"] == {"Vendor_A": 1, "Vendor_B": 2}


def test_get_drawdown_analysis(client: TestClient, override_dependencies):
    """Test GET /api/v1/metrics/drawdowns endpoint."""
    response = client.get("/api/v1/metrics/drawdowns")

    assert response.status_code == 200
    data = response.json()
    assert data["total_drawdown_events"] == 25
    assert "Vendor_A" in data["vendors_affected"]
    assert data["avg_signal_during_drawdown"] == 0.65
    assert "by_vendor" in data
    assert "Vendor_A" in data["by_vendor"]


def test_get_drawdown_analysis_with_vendor_filter(
    client: TestClient, override_dependencies
):
    """Test GET /api/v1/metrics/drawdowns with vendor filter."""
    response = client.get("/api/v1/metrics/drawdowns?vendor=Vendor_A")

    assert response.status_code == 200
    mock_data_loader, mock_metrics_service = override_dependencies
    mock_metrics_service.get_drawdown_analysis.assert_called_once_with("Vendor_A")
