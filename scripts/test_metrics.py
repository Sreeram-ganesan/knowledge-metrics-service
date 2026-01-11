#!/usr/bin/env python3
"""Test client for Metrics API endpoints.

This script demonstrates how to interact with the metrics endpoints.
Run the API server first: uvicorn learn_fastapi:app --reload

Usage:
    python scripts/test_metrics.py [--base-url http://localhost:8000]
"""

import argparse
import json
import sys

import httpx


def print_json(data: dict, title: str = "") -> None:
    """Pretty print JSON data."""
    if title:
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}")
    print(json.dumps(data, indent=2, default=str))


def test_health(client: httpx.Client) -> bool:
    """Test health endpoint."""
    print("\n[TEST] /health endpoint...")
    try:
        response = client.get("/health")
        response.raise_for_status()
        print_json(response.json(), "Health Check")
        return True
    except httpx.HTTPError as e:
        print(f"[FAIL] Health check failed: {e}")
        return False


def test_data_info(client: httpx.Client) -> list[str]:
    """Test data info endpoint and extract vendors list."""
    print("\n[TEST] /api/v1/metrics/info endpoint...")
    response = client.get("/api/v1/metrics/info")
    response.raise_for_status()
    data = response.json()
    print_json(data, "Dataset Information")
    return data["vendors"]


def test_vendor_metrics(client: httpx.Client, vendor: str) -> None:
    """Test vendor metrics endpoint."""
    print(f"\n[TEST] /api/v1/metrics/vendors/{vendor} endpoint...")
    response = client.get(f"/api/v1/metrics/vendors/{vendor}")
    response.raise_for_status()
    print_json(response.json(), f"Metrics for {vendor}")


def test_vendor_metrics_with_dates(
    client: httpx.Client,
    vendor: str,
    start_date: str,
    end_date: str,
) -> None:
    """Test vendor metrics with date filtering."""
    print(f"\n[TEST] /api/v1/metrics/vendors/{vendor} with date range...")
    response = client.get(
        f"/api/v1/metrics/vendors/{vendor}",
        params={"start_date": start_date, "end_date": end_date},
    )
    response.raise_for_status()
    print_json(
        response.json(),
        f"Metrics for {vendor} ({start_date} to {end_date})",
    )


def test_period_metrics(client: httpx.Client) -> None:
    """Test period metrics endpoint."""
    print("\n[TEST] /api/v1/metrics/period endpoint...")
    response = client.get("/api/v1/metrics/period")
    response.raise_for_status()
    print_json(response.json(), "Period Metrics (All Data)")


def test_period_metrics_filtered(
    client: httpx.Client,
    start_date: str,
    end_date: str,
) -> None:
    """Test period metrics with date filtering."""
    print("\n[TEST] /api/v1/metrics/period with date range...")
    response = client.get(
        "/api/v1/metrics/period",
        params={"start_date": start_date, "end_date": end_date},
    )
    response.raise_for_status()
    print_json(response.json(), f"Period Metrics ({start_date} to {end_date})")


def test_compare_vendors(client: httpx.Client) -> None:
    """Test vendor comparison endpoint."""
    print("\n[TEST] /api/v1/metrics/compare endpoint...")
    response = client.get("/api/v1/metrics/compare")
    response.raise_for_status()
    print_json(response.json(), "Vendor Comparison")


def test_drawdown_analysis(client: httpx.Client, vendor: str | None = None) -> None:
    """Test drawdown analysis endpoint."""
    print("\n[TEST] /api/v1/metrics/drawdowns endpoint...")
    params = {"vendor": vendor} if vendor else {}
    response = client.get("/api/v1/metrics/drawdowns", params=params)
    response.raise_for_status()
    title = f"Drawdown Analysis for {vendor}" if vendor else "Drawdown Analysis (All)"
    print_json(response.json(), title)


def test_vendor_not_found(client: httpx.Client) -> None:
    """Test 404 error handling for unknown vendor."""
    print("\n[TEST] Error handling for unknown vendor...")
    response = client.get("/api/v1/metrics/vendors/UnknownVendor")
    print(f"Status: {response.status_code}")
    print_json(response.json(), "Error Response")


def main():
    """Run all metrics API tests."""
    parser = argparse.ArgumentParser(description="Test Metrics API endpoints")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL for the API (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    print(f"Testing Metrics API at {args.base_url}")
    print("=" * 60)

    with httpx.Client(base_url=args.base_url, timeout=30.0) as client:
        # Test health first
        if not test_health(client):
            print("\n[FAIL] API is not healthy. Is the server running?")
            print("   Start it with: uvicorn learn_fastapi:app --reload")
            sys.exit(1)

        # Test all endpoints
        vendors = test_data_info(client)

        if vendors:
            # Test first vendor
            test_vendor_metrics(client, vendors[0])

            # Test with date filtering
            test_vendor_metrics_with_dates(
                client, vendors[0], "2020-01-01", "2020-01-31"
            )

        test_period_metrics(client)
        test_period_metrics_filtered(client, "2020-02-01", "2020-02-28")

        test_compare_vendors(client)

        test_drawdown_analysis(client)
        if vendors:
            test_drawdown_analysis(client, vendors[0])

        test_vendor_not_found(client)

    print("\n" + "=" * 60)
    print("[OK] All metrics API tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
