#!/usr/bin/env python3
"""Quick integration test script.

Runs a basic smoke test against all endpoints.
Exit code 0 = all tests passed, 1 = failures.

Usage:
    python scripts/run_tests.py [--base-url http://localhost:8000]
"""

import argparse
import sys

import httpx


def test_endpoint(
    client: httpx.Client,
    method: str,
    path: str,
    expected_status: int = 200,
    json_body: dict | None = None,
    params: dict | None = None,
) -> bool:
    """Test a single endpoint."""
    try:
        if method == "GET":
            response = client.get(path, params=params)
        elif method == "POST":
            response = client.post(path, json=json_body)
        else:
            raise ValueError(f"Unknown method: {method}")

        if response.status_code == expected_status:
            print(f"[OK] {method} {path} -> {response.status_code}")
            return True
        else:
            print(
                f"[FAIL] {method} {path} -> {response.status_code} (expected {expected_status})"
            )
            return False
    except Exception as e:
        print(f"[FAIL] {method} {path} -> Error: {e}")
        return False


def main():
    """Run integration tests."""
    parser = argparse.ArgumentParser(description="Run integration tests")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL for the API",
    )
    args = parser.parse_args()

    print(f"Running integration tests against {args.base_url}")
    print("=" * 60)

    tests = [
        # Health & Root
        ("GET", "/", 200, None, None),
        ("GET", "/health", 200, None, None),
        # Metrics endpoints
        ("GET", "/api/v1/metrics/info", 200, None, None),
        ("GET", "/api/v1/metrics/vendors/AlphaSignals", 200, None, None),
        ("GET", "/api/v1/metrics/vendors/UnknownVendor", 404, None, None),
        (
            "GET",
            "/api/v1/metrics/vendors/BetaFlow",
            200,
            None,
            {"start_date": "2020-01-01"},
        ),
        ("GET", "/api/v1/metrics/period", 200, None, None),
        (
            "GET",
            "/api/v1/metrics/period",
            200,
            None,
            {"start_date": "2020-01-01", "end_date": "2020-01-31"},
        ),
        ("GET", "/api/v1/metrics/compare", 200, None, None),
        ("GET", "/api/v1/metrics/drawdowns", 200, None, None),
        ("GET", "/api/v1/metrics/drawdowns", 200, None, {"vendor": "GammaEdge"}),
        # Query endpoints
        ("GET", "/api/v1/query/supported", 200, None, None),
        ("POST", "/api/v1/query", 200, {"query": "List all vendors"}, None),
        ("POST", "/api/v1/query", 200, {"query": "Metrics for AlphaSignals"}, None),
        ("POST", "/api/v1/query", 200, {"query": "Compare all vendors"}, None),
        ("POST", "/api/v1/query", 200, {"query": "Show drawdowns"}, None),
    ]

    passed = 0
    failed = 0

    with httpx.Client(base_url=args.base_url, timeout=30.0) as client:
        for method, path, expected, json_body, params in tests:
            if test_endpoint(client, method, path, expected, json_body, params):
                passed += 1
            else:
                failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")

    if failed > 0:
        print("[FAIL] Some tests failed!")
        sys.exit(1)
    else:
        print("[OK] All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
