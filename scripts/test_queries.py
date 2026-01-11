#!/usr/bin/env python3
"""Test client for Natural Language Query API endpoints.

This script demonstrates how to interact with the query endpoints.
Run the API server first: uv run uvicorn app.main:app --reload

Usage:
    python scripts/test_queries.py [--base-url http://localhost:8000]
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
    print("\n[CHECK] API health...")
    try:
        response = client.get("/health")
        response.raise_for_status()
        print("[OK] API is healthy")
        return True
    except httpx.HTTPError as e:
        print(f"[FAIL] Health check failed: {e}")
        return False


def test_supported_queries(client: httpx.Client) -> None:
    """Test supported queries endpoint."""
    print("\n[TEST] /api/v1/query/supported endpoint...")
    response = client.get("/api/v1/query/supported")
    response.raise_for_status()
    print_json(response.json(), "Supported Query Patterns")


def send_query(client: httpx.Client, query: str) -> dict:
    """Send a natural language query."""
    print(f'\n[QUERY] "{query}"')
    print("-" * 60)

    response = client.post(
        "/api/v1/query",
        json={"query": query},
    )
    response.raise_for_status()
    data = response.json()

    # Print structured response
    print(f"Intent: {data['intent']}")
    print(f"Success: {data['success']}")
    print(f"Explanation: {data['explanation']}")

    if data.get("entities", {}).get("vendors"):
        print(f"Detected Vendors: {data['entities']['vendors']}")
    if data.get("entities", {}).get("start_date"):
        print(
            f"Date Range: {data['entities']['start_date']} to {data['entities'].get('end_date', 'N/A')}"
        )

    print("\nData:")
    print(json.dumps(data.get("data"), indent=2, default=str))

    return data


def main():
    """Run all query API tests."""
    parser = argparse.ArgumentParser(description="Test Natural Language Query API")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL for the API (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    print(f"Testing Query API at {args.base_url}")
    print("=" * 60)

    with httpx.Client(base_url=args.base_url, timeout=30.0) as client:
        # Test health first
        if not test_health(client):
            print("\n[FAIL] API is not healthy. Is the server running?")
            print("   Start it with: uv run uvicorn app.main:app --reload")
            sys.exit(1)

        # Show supported queries
        test_supported_queries(client)

        # Test one query per intent type (5 intents + 1 edge case)
        print("\n" + "=" * 60)
        print("  Testing Natural Language Queries")
        print("=" * 60)

        # One per intent - demonstrates capability without redundancy
        send_query(client, "What are the metrics for AlphaSignals?")  # vendor_metrics
        send_query(client, "List all vendors")  # list_vendors
        send_query(client, "Which vendor is best?")  # compare_vendors
        send_query(client, "Show drawdown periods")  # drawdown_analysis
        send_query(client, "Metrics in January 2020")  # period_metrics

        # Edge case
        send_query(client, "Tell me about the weather")  # unknown intent

    print("\n" + "=" * 60)
    print("[OK] All query API tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
