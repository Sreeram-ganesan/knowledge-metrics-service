"""Unit tests for QueryService."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from app.services.query_service import (
    ParsedQuery,
    QueryExecutor,
    QueryIntent,
    QueryResult,
    QueryService,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_metrics_service():
    """Create a mock MetricsService."""
    mock = MagicMock()

    # Mock vendor metrics
    vendor_metrics = MagicMock()
    vendor_metrics.vendor = "Vendor_A"
    vendor_metrics.universes = ["Equities"]
    vendor_metrics.record_count = 100
    vendor_metrics.date_range = (date(2023, 1, 1), date(2023, 12, 31))
    vendor_metrics.signal_strength_mean = 0.75
    vendor_metrics.signal_strength_std = 0.15
    vendor_metrics.drawdown_rate = 0.02
    vendor_metrics.signal_volatility = 0.2
    vendor_metrics.avg_signal_during_drawdown = 0.65
    vendor_metrics.avg_signal_outside_drawdown = 0.78
    mock.get_vendor_metrics.return_value = vendor_metrics

    # Mock period metrics
    period_metrics = MagicMock()
    period_metrics.start_date = date(2023, 1, 1)
    period_metrics.end_date = date(2023, 12, 31)
    period_metrics.record_count = 500
    period_metrics.vendor_count = 3
    period_metrics.avg_signal_strength = 0.72
    period_metrics.total_drawdown_events = 25
    period_metrics.vendor_avg_signals = {"Vendor_A": 0.75, "Vendor_B": 0.70}
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
        "total_drawdown_events": 10,
        "vendors_affected": ["Vendor_A"],
        "avg_signal_during_drawdown": 0.65,
        "drawdown_dates": ["2023-03-15"],
        "by_vendor": {"Vendor_A": 10},
    }

    return mock


@pytest.fixture
def mock_data_loader():
    """Create a mock DataLoaderService."""
    mock = MagicMock()
    mock.get_vendors.return_value = ["Vendor_A", "Vendor_B", "Vendor_C"]
    return mock


@pytest.fixture
def query_executor(mock_metrics_service, mock_data_loader):
    """Create a QueryExecutor with mocked dependencies."""
    executor = QueryExecutor(metrics_service=mock_metrics_service)
    executor._data_loader = mock_data_loader
    return executor


# =============================================================================
# Tests - QueryExecutor
# =============================================================================


class TestQueryExecutorListVendors:
    """Test LIST_VENDORS intent execution."""

    def test_list_vendors(self, query_executor: QueryExecutor):
        """List all available vendors."""
        parsed = ParsedQuery(intent=QueryIntent.LIST_VENDORS, raw_query="list vendors")

        result = query_executor.execute(parsed)

        assert result.success is True
        assert result.intent == QueryIntent.LIST_VENDORS
        assert result.data["count"] == 3
        assert "Vendor_A" in result.data["vendors"]


class TestQueryExecutorVendorMetrics:
    """Test VENDOR_METRICS intent execution."""

    def test_vendor_metrics(self, query_executor: QueryExecutor):
        """Get metrics for a specific vendor."""
        parsed = ParsedQuery(
            intent=QueryIntent.VENDOR_METRICS,
            vendors=["Vendor_A"],
            raw_query="metrics for Vendor_A",
        )

        result = query_executor.execute(parsed)

        assert result.success is True
        assert result.intent == QueryIntent.VENDOR_METRICS
        assert "Vendor_A" in result.data
        assert result.data["Vendor_A"]["signal_strength_mean"] == 0.75

    def test_vendor_metrics_no_vendor_specified(self, query_executor: QueryExecutor):
        """Return error when no vendor specified."""
        parsed = ParsedQuery(
            intent=QueryIntent.VENDOR_METRICS,
            vendors=[],
            raw_query="show metrics",
        )

        result = query_executor.execute(parsed)

        assert result.success is False
        assert result.error is not None
        assert "No vendor specified" in result.error


class TestQueryExecutorPeriodMetrics:
    """Test PERIOD_METRICS intent execution."""

    def test_period_metrics(self, query_executor: QueryExecutor):
        """Get metrics for a time period."""
        parsed = ParsedQuery(
            intent=QueryIntent.PERIOD_METRICS,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 6, 30),
            raw_query="metrics from Jan to Jun 2023",
        )

        result = query_executor.execute(parsed)

        assert result.success is True
        assert result.intent == QueryIntent.PERIOD_METRICS
        assert result.data["vendor_count"] == 3
        assert result.data["record_count"] == 500


class TestQueryExecutorCompareVendors:
    """Test COMPARE_VENDORS intent execution."""

    def test_compare_vendors(self, query_executor: QueryExecutor):
        """Compare all vendors."""
        parsed = ParsedQuery(
            intent=QueryIntent.COMPARE_VENDORS,
            raw_query="compare vendors",
        )

        result = query_executor.execute(parsed)

        assert result.success is True
        assert result.intent == QueryIntent.COMPARE_VENDORS
        assert result.data["best_avg_signal"] == "Vendor_A"
        assert result.data["lowest_drawdown_rate"] == "Vendor_A"


class TestQueryExecutorDrawdownAnalysis:
    """Test DRAWDOWN_ANALYSIS intent execution."""

    def test_drawdown_analysis(self, query_executor: QueryExecutor):
        """Analyze drawdown periods."""
        parsed = ParsedQuery(
            intent=QueryIntent.DRAWDOWN_ANALYSIS,
            raw_query="show drawdowns",
        )

        result = query_executor.execute(parsed)

        assert result.success is True
        assert result.intent == QueryIntent.DRAWDOWN_ANALYSIS
        assert result.data["total_drawdown_events"] == 10

    def test_drawdown_analysis_with_vendor(self, query_executor: QueryExecutor):
        """Analyze drawdowns for specific vendor."""
        parsed = ParsedQuery(
            intent=QueryIntent.DRAWDOWN_ANALYSIS,
            vendors=["Vendor_A"],
            raw_query="drawdowns for Vendor_A",
        )

        result = query_executor.execute(parsed)

        assert result.success is True
        assert "Vendor_A" in result.data["vendors_affected"]


class TestQueryExecutorUnknown:
    """Test UNKNOWN intent execution."""

    def test_unknown_query(self, query_executor: QueryExecutor):
        """Handle unknown query gracefully."""
        parsed = ParsedQuery(
            intent=QueryIntent.UNKNOWN,
            raw_query="random gibberish",
        )

        result = query_executor.execute(parsed)

        assert result.success is False
        assert result.intent == QueryIntent.UNKNOWN
        assert "suggestions" in result.data


class TestQueryExecutorErrorHandling:
    """Test error handling in executor."""

    def test_handles_exception(
        self, query_executor: QueryExecutor, mock_metrics_service
    ):
        """Wrap exceptions in error response."""
        mock_metrics_service.get_vendor_metrics.side_effect = ValueError("Test error")

        parsed = ParsedQuery(
            intent=QueryIntent.VENDOR_METRICS,
            vendors=["Vendor_A"],
            raw_query="metrics for Vendor_A",
        )

        result = query_executor.execute(parsed)

        assert result.success is False
        assert result.error is not None
        assert "Test error" in result.error


# =============================================================================
# Tests - QueryService
# =============================================================================


class TestQueryService:
    """Test QueryService integration."""

    def test_get_supported_queries(self):
        """Return list of supported query patterns."""
        # Use real service for this (no LLM call)
        service = QueryService(parser=MagicMock(), executor=MagicMock())

        patterns = service.get_supported_queries()

        assert len(patterns) == 5
        intents = [p["intent"] for p in patterns]
        assert "vendor_metrics" in intents
        assert "compare_vendors" in intents

    def test_process_query_calls_parser_and_executor(self):
        """Verify pipeline: parser → executor."""
        mock_parser = MagicMock()
        mock_executor = MagicMock()

        parsed = ParsedQuery(
            intent=QueryIntent.LIST_VENDORS,
            raw_query="list vendors",
        )
        mock_parser.parse.return_value = parsed
        mock_executor.execute.return_value = QueryResult(
            intent=QueryIntent.LIST_VENDORS,
            data={"vendors": []},
            explanation="Listed vendors",
        )

        service = QueryService(parser=mock_parser, executor=mock_executor)
        result, returned_parsed = service.process_query("list vendors")

        mock_parser.parse.assert_called_once_with("list vendors")
        mock_executor.execute.assert_called_once_with(parsed)
        assert returned_parsed == parsed
