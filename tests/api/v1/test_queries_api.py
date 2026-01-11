"""Unit tests for Query API v1 endpoints.

This module demonstrates how FastAPI's dependency injection enables clean,
isolated unit tests by overriding dependencies with mocks.

KEY CONCEPT:
    Instead of patching imports with unittest.mock.patch, FastAPI lets us
    swap dependencies at runtime using `app.dependency_overrides`. This is
    cleaner, more explicit, and doesn't require knowing the import path.
"""

from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import get_query_service
from app.services.query_service import (
    ParsedQuery,
    QueryIntent,
    QueryResult,
    QueryService,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_query_service():
    """
    Create a mock QueryService.
    
    MagicMock(spec=QueryService) ensures the mock only has methods
    that exist on the real QueryService class.
    """
    return MagicMock(spec=QueryService)


@pytest.fixture
def override_query_service(mock_query_service):
    """
    Override the QueryService dependency with our mock.
    
    THIS IS THE KEY BENEFIT OF DEPENDENCY INJECTION:
    
    In the route, we have:
        async def process_query(query_service: QueryServiceDep):
            result = query_service.process_query(...)
    
    Normally, FastAPI calls `get_query_service()` to create the real service.
    But here, we tell FastAPI: "When anyone asks for get_query_service,
    give them our mock instead."
    
    No need for:
        - @patch('app.api.v1.routes.queries.get_query_service')
        - Complex import path management
        - Worrying about where the function is imported
    """
    app.dependency_overrides[get_query_service] = lambda: mock_query_service
    yield mock_query_service
    # Cleanup: restore normal behavior after the test
    app.dependency_overrides.clear()


# =============================================================================
# Helper
# =============================================================================


def create_query_result(
    intent: QueryIntent = QueryIntent.VENDOR_METRICS,
    data: Any = None,
    explanation: str = "Test explanation",
    success: bool = True,
    error: str | None = None,
) -> QueryResult:
    """Factory function to create QueryResult instances for testing."""
    return QueryResult(
        intent=intent,
        data=data,
        explanation=explanation,
        success=success,
        error=error,
    )


def create_parsed_query(
    intent: QueryIntent = QueryIntent.VENDOR_METRICS,
    vendors: list[str] | None = None,
    raw_query: str = "test query",
) -> ParsedQuery:
    """Factory function to create ParsedQuery instances for testing."""
    return ParsedQuery(
        intent=intent,
        vendors=vendors or [],
        start_date=None,
        end_date=None,
        raw_query=raw_query,
    )


# =============================================================================
# The Test - Demonstrating DI Benefits
# =============================================================================


class TestProcessQueryWithDependencyInjection:
    """
    Single test demonstrating why dependency injection makes testing easy.
    """

    def test_process_query_with_mocked_service(
        self, client: TestClient, override_query_service: MagicMock
    ):
        """
        This test demonstrates the power of FastAPI's dependency injection.

        WHAT WE'RE TESTING:
            The route layer correctly:
            1. Receives the HTTP request
            2. Passes the query to the service
            3. Formats the response correctly

        WHAT WE'RE NOT TESTING:
            - Real QueryService logic (that's a separate unit test)
            - Real data loading from CSV
            - Real LLM parsing

        WHY THIS IS POWERFUL:
            1. FAST: No real I/O, no data loading, no LLM calls
            2. ISOLATED: Route tests don't break when service logic changes
            3. CONTROLLABLE: We decide exactly what the service returns
            4. EASY ERROR TESTING: Just set mock.return_value to an error response
        """
        # ARRANGE: Configure the mock to return a fake result
        # The real service would load CSV, call LLM, etc.
        # Our mock just returns what we tell it to.
        mock_result = create_query_result(
            intent=QueryIntent.VENDOR_METRICS,
            data={
                "AlphaSignals": {
                    "signal_strength_mean": 0.256,
                    "drawdown_rate": 0.32,
                }
            },
            explanation="Retrieved metrics for AlphaSignals",
        )
        mock_parsed = create_parsed_query(
            intent=QueryIntent.VENDOR_METRICS,
            vendors=["AlphaSignals"],
            raw_query="What are the metrics for AlphaSignals?",
        )
        override_query_service.process_query.return_value = (mock_result, mock_parsed)

        # ACT: Make the HTTP request
        # FastAPI will:
        #   1. Route to process_query()
        #   2. Try to inject QueryService via get_query_service
        #   3. Find our override and use the mock instead
        #   4. Call mock.process_query("What are the metrics...")
        #   5. Get our pre-configured fake response
        response = client.post(
            "/api/v1/query",
            json={"query": "What are the metrics for AlphaSignals?"},
        )

        # ASSERT: Verify the route formatted everything correctly
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["intent"] == "vendor_metrics"
        assert data["entities"]["vendors"] == ["AlphaSignals"]
        assert data["data"]["AlphaSignals"]["signal_strength_mean"] == 0.256

        # VERIFY: The service was called with the right argument
        # This proves the route correctly passed the query string to the service
        override_query_service.process_query.assert_called_once_with(
            "What are the metrics for AlphaSignals?"
        )
