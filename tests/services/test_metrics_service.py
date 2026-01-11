"""Unit tests for MetricsService."""

from datetime import date
from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.core.exceptions import InvalidDateRangeError, VendorNotFoundError
from app.services.metrics_service import MetricsService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_dataframe():
    """Create a sample DataFrame for testing."""
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"]
            ),
            "vendor": ["Vendor_A", "Vendor_A", "Vendor_B", "Vendor_B"],
            "universe": ["Equities", "Equities", "FX", "FX"],
            "feature_x": [1.0, 2.0, 1.5, 2.5],
            "feature_y": [2.0, 4.0, 3.0, 5.0],
            "signal_strength": [0.5, 0.6, 0.4, 0.8],
            "drawdown_flag": [0, 1, 0, 0],
        }
    )


@pytest.fixture
def mock_data_loader(sample_dataframe):
    """Create a mock DataLoaderService."""
    mock = MagicMock()
    mock.get_vendors.return_value = ["Vendor_A", "Vendor_B"]

    def get_vendor_data(vendor, start_date=None, end_date=None):
        df = sample_dataframe[sample_dataframe["vendor"] == vendor].copy()
        if df.empty:
            raise VendorNotFoundError(vendor, available=["Vendor_A", "Vendor_B"])
        return df

    mock.get_vendor_data.side_effect = get_vendor_data
    mock.get_data_by_date_range.return_value = sample_dataframe
    mock.get_drawdown_periods.return_value = sample_dataframe[
        sample_dataframe["drawdown_flag"] == 1
    ]
    return mock


@pytest.fixture
def metrics_service(mock_data_loader):
    """Create a MetricsService with mocked data loader."""
    return MetricsService(data_loader=mock_data_loader)


# =============================================================================
# Tests
# =============================================================================


class TestGetVendorMetrics:
    """Test get_vendor_metrics method."""

    def test_returns_vendor_metrics(self, metrics_service: MetricsService):
        """Compute metrics for a valid vendor."""
        result = metrics_service.get_vendor_metrics("Vendor_A")

        assert result.vendor == "Vendor_A"
        assert result.record_count == 2
        assert result.universes == ["Equities"]
        assert result.drawdown_count == 1
        assert result.drawdown_rate == 0.5

    def test_computes_feature_statistics(self, metrics_service: MetricsService):
        """Verify feature mean and std calculations."""
        result = metrics_service.get_vendor_metrics("Vendor_A")

        assert result.feature_x_mean == 1.5  # (1.0 + 2.0) / 2
        assert result.feature_y_mean == 3.0  # (2.0 + 4.0) / 2

    def test_computes_signal_statistics(self, metrics_service: MetricsService):
        """Verify signal strength calculations."""
        result = metrics_service.get_vendor_metrics("Vendor_A")

        assert result.signal_strength_mean == 0.55  # (0.5 + 0.6) / 2
        assert result.signal_strength_min == 0.5
        assert result.signal_strength_max == 0.6

    def test_computes_correlation(self, metrics_service: MetricsService):
        """Correlation between feature_x and feature_y."""
        result = metrics_service.get_vendor_metrics("Vendor_A")

        # Perfect positive correlation (x doubles, y doubles)
        assert result.feature_xy_correlation == 1.0

    def test_invalid_date_range_raises_error(self, metrics_service: MetricsService):
        """Raise error when start_date >= end_date."""
        with pytest.raises(InvalidDateRangeError):
            metrics_service.get_vendor_metrics(
                "Vendor_A",
                start_date=date(2023, 1, 10),
                end_date=date(2023, 1, 1),
            )

    def test_vendor_not_found_raises_error(self, metrics_service: MetricsService):
        """Raise error for unknown vendor."""
        with pytest.raises(VendorNotFoundError):
            metrics_service.get_vendor_metrics("Unknown_Vendor")


class TestGetPeriodMetrics:
    """Test get_period_metrics method."""

    def test_returns_period_metrics(self, metrics_service: MetricsService):
        """Compute aggregated period metrics."""
        result = metrics_service.get_period_metrics()

        assert result.record_count == 4
        assert result.vendor_count == 2
        assert result.total_drawdown_events == 1

    def test_computes_vendor_breakdowns(self, metrics_service: MetricsService):
        """Per-vendor signal averages and drawdown rates."""
        result = metrics_service.get_period_metrics()

        assert "Vendor_A" in result.vendor_avg_signals
        assert "Vendor_B" in result.vendor_avg_signals
        assert result.vendor_drawdown_rates["Vendor_A"] == 0.5  # 1/2
        assert result.vendor_drawdown_rates["Vendor_B"] == 0.0  # 0/2


class TestGetComparativeMetrics:
    """Test get_comparative_metrics method."""

    def test_returns_comparative_metrics(self, metrics_service: MetricsService):
        """Generate vendor comparison."""
        result = metrics_service.get_comparative_metrics()

        assert set(result.vendors) == {"Vendor_A", "Vendor_B"}
        assert result.best_avg_signal in ["Vendor_A", "Vendor_B"]
        assert result.lowest_drawdown_rate in ["Vendor_A", "Vendor_B"]

    def test_rankings_are_computed(self, metrics_service: MetricsService):
        """Vendors are ranked by signal and stability."""
        result = metrics_service.get_comparative_metrics()

        assert len(result.ranking_by_avg_signal) == 2
        assert 1 in result.ranking_by_avg_signal.values()
        assert 2 in result.ranking_by_avg_signal.values()


class TestGetDrawdownAnalysis:
    """Test get_drawdown_analysis method."""

    def test_returns_drawdown_analysis(self, metrics_service: MetricsService):
        """Analyze drawdown periods."""
        result = metrics_service.get_drawdown_analysis()

        assert result["total_drawdown_events"] == 1
        assert "Vendor_A" in result["vendors_affected"]
        assert result["avg_signal_during_drawdown"] is not None

    def test_empty_drawdowns(self, metrics_service: MetricsService, mock_data_loader):
        """Handle case with no drawdowns."""
        mock_data_loader.get_drawdown_periods.return_value = pd.DataFrame()

        result = metrics_service.get_drawdown_analysis()

        assert result["total_drawdown_events"] == 0
        assert result["vendors_affected"] == []
        assert result["avg_signal_during_drawdown"] is None
