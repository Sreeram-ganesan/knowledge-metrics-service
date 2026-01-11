"""Query Service - LLM-powered natural language query processing.

This module uses OpenAI to parse natural language queries about vendor metrics.
The LLM handles both entity extraction and intent classification in a single call,
making the code simpler and more maintainable.

When OpenAI API key is not configured, falls back to a regex-based parser.

Architecture:
    Query Input → LLM/Regex Parser (parse intent + entities) → Query Executor → Response
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Optional

from app.core.config import get_settings
from app.services.data_loader import get_data_loader
from app.services.metrics_service import MetricsService, get_metrics_service

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """Recognized query intents."""

    VENDOR_METRICS = "vendor_metrics"
    PERIOD_METRICS = "period_metrics"
    COMPARE_VENDORS = "compare_vendors"
    DRAWDOWN_ANALYSIS = "drawdown_analysis"
    LIST_VENDORS = "list_vendors"
    UNKNOWN = "unknown"


@dataclass
class ParsedQuery:
    """LLM-parsed query with intent and entities."""

    intent: QueryIntent
    vendors: list[str] = field(default_factory=list)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    raw_query: str = ""


@dataclass
class QueryResult:
    """Result of a processed query."""

    intent: QueryIntent
    data: Any
    explanation: str
    success: bool = True
    error: Optional[str] = None


class QueryParser(ABC):
    """Abstract base class for query parsers."""

    @abstractmethod
    def parse(self, query: str) -> ParsedQuery:
        """Parse a natural language query."""
        pass


class RegexQueryParser(QueryParser):
    """
    Regex-based fallback parser for when LLM is not available.

    Uses pattern matching to extract intent and entities from queries.
    Less flexible than LLM but works offline without API keys.
    """

    # Intent patterns (order matters - more specific patterns first)
    INTENT_PATTERNS = [
        # Compare vendors (check before list_vendors since "which vendor" could match both)
        (
            r"\b(compare|rank|ranking|best|worst|top|bottom)\b",
            QueryIntent.COMPARE_VENDORS,
        ),
        (r"\bwhich\b.*\b(better|best|worst)\b", QueryIntent.COMPARE_VENDORS),
        # List vendors
        (r"\b(list|show|what)\b.*\bvendors?\b", QueryIntent.LIST_VENDORS),
        (r"\bvendors?\b.*\b(available|list)\b", QueryIntent.LIST_VENDORS),
        # Drawdown analysis
        (r"\b(drawdown|stress|crisis)\b", QueryIntent.DRAWDOWN_ANALYSIS),
        # Period metrics (dates mentioned without specific vendor)
        (
            r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b.*\d{4}",
            QueryIntent.PERIOD_METRICS,
        ),
        (r"\d{4}-\d{2}-\d{2}", QueryIntent.PERIOD_METRICS),
        (
            r"\b(period|time\s*range|from|between)\b.*\b(to|and)\b",
            QueryIntent.PERIOD_METRICS,
        ),
        # Vendor metrics (fallback for vendor-specific queries)
        (
            r"\b(metrics?|signal|performance|stats?|statistics?)\b",
            QueryIntent.VENDOR_METRICS,
        ),
    ]

    # Month name to number mapping
    MONTHS = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }

    # Days per month (non-leap year default)
    MONTH_DAYS = {
        1: 31,
        2: 28,
        3: 31,
        4: 30,
        5: 31,
        6: 30,
        7: 31,
        8: 31,
        9: 30,
        10: 31,
        11: 30,
        12: 31,
    }

    def __init__(self):
        self._data_loader = get_data_loader()

    def parse(self, query: str) -> ParsedQuery:
        """
        Parse query using regex patterns.

        Args:
            query: Natural language query string.

        Returns:
            ParsedQuery with intent and extracted entities.
        """
        logger.debug(
            f"Parsing query with regex parser: '{query[:100]}...'"
            if len(query) > 100
            else f"Parsing query with regex parser: '{query}'"
        )
        query_lower = query.lower()

        # Extract intent
        intent = self._extract_intent(query_lower)
        logger.debug(f"Extracted intent: {intent.value}")

        # Extract vendors
        vendors = self._extract_vendors(query)
        if vendors:
            logger.debug(f"Extracted vendors: {len(vendors)} found")

        # Extract dates
        start_date, end_date = self._extract_dates(query_lower)
        if start_date or end_date:
            logger.debug(f"Extracted dates: start={start_date}, end={end_date}")

        # Adjust intent based on extracted entities
        if intent == QueryIntent.VENDOR_METRICS and not vendors:
            # No vendor mentioned, check if it's really period metrics
            if start_date or end_date:
                logger.debug(
                    "Adjusting intent: VENDOR_METRICS -> PERIOD_METRICS (no vendor, has dates)"
                )
                intent = QueryIntent.PERIOD_METRICS

        parsed = ParsedQuery(
            intent=intent,
            vendors=vendors,
            start_date=start_date,
            end_date=end_date,
            raw_query=query,
        )

        logger.info(
            f"Query parsed (regex): intent={intent.value}, "
            f"vendors={len(vendors)}, "
            f"date_range={start_date} to {end_date}"
        )
        return parsed

    def _extract_intent(self, query_lower: str) -> QueryIntent:
        """Extract intent from query using regex patterns."""
        for pattern, intent in self.INTENT_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return intent
        return QueryIntent.UNKNOWN

    def _extract_vendors(self, query: str) -> list[str]:
        """Extract vendor names from query."""
        available_vendors = self._data_loader.get_vendors()
        found_vendors = []

        for vendor in available_vendors:
            # Case-insensitive search for vendor name
            if re.search(rf"\b{re.escape(vendor)}\b", query, re.IGNORECASE):
                found_vendors.append(vendor)

        return found_vendors

    def _extract_dates(self, query_lower: str) -> tuple[Optional[date], Optional[date]]:
        """Extract date range from query."""
        start_date = None
        end_date = None

        # Pattern: YYYY-MM-DD
        iso_dates = re.findall(r"\d{4}-\d{2}-\d{2}", query_lower)
        if len(iso_dates) >= 2:
            start_date = date.fromisoformat(iso_dates[0])
            end_date = date.fromisoformat(iso_dates[1])
        elif len(iso_dates) == 1:
            start_date = date.fromisoformat(iso_dates[0])

        # Pattern: Month YYYY (e.g., "January 2020")
        if not start_date:
            month_year = re.search(
                r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})\b",
                query_lower,
            )
            if month_year:
                month_name = month_year.group(1)
                year = int(month_year.group(2))
                month = self.MONTHS[month_name]
                start_date = date(year, month, 1)
                # Last day of month
                end_date = date(year, month, self.MONTH_DAYS[month])

        return start_date, end_date


class LLMQueryParser(QueryParser):
    """
    Uses OpenAI to parse natural language queries.

    The LLM extracts both intent and entities in a single call using
    structured JSON output. This is simpler than regex patterns and
    handles variations in phrasing naturally.
    """

    SYSTEM_PROMPT = """You are a query parser for a vendor metrics system.
Parse the user's query and return a JSON object with:
- intent: one of "vendor_metrics", "period_metrics", "compare_vendors", "drawdown_analysis", "list_vendors", "unknown"
- vendors: list of vendor names mentioned (use exact names from available vendors)
- start_date: start date in YYYY-MM-DD format if mentioned (null otherwise)
- end_date: end date in YYYY-MM-DD format if mentioned (null otherwise)

Available vendors: {vendors}

Intent descriptions (use these to classify the query):
- vendor_metrics: Get metrics for a SPECIFIC vendor mentioned by name
- period_metrics: Get metrics for a specific time period (dates/months mentioned)
- compare_vendors: Compare or rank vendors, find the best/worst vendor, any question about which vendor is better/best/worst, ranking vendors by any metric
- drawdown_analysis: Analyze drawdown/stress periods, find which vendors had drawdowns, any question about drawdowns or stress events
- list_vendors: List or enumerate available vendors


For single month queries like "metrics for February 2020", set start_date to first day and end_date to last day of that month.

Return ONLY valid JSON, no explanation."""

    def __init__(self):
        from openai import OpenAI

        settings = get_settings()
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model
        self._data_loader = get_data_loader()

    def parse(self, query: str) -> ParsedQuery:
        """
        Parse a natural language query using OpenAI.

        Args:
            query: Natural language query string.

        Returns:
            ParsedQuery with intent and extracted entities.
        """
        logger.debug(
            f"Parsing query with LLM: '{query[:100]}...'"
            if len(query) > 100
            else f"Parsing query with LLM: '{query}'"
        )

        vendors = self._data_loader.get_vendors()
        system_prompt = self.SYSTEM_PROMPT.format(vendors=", ".join(vendors))

        logger.debug(f"Calling OpenAI API (model={self._model})")
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            response_format={"type": "json_object"},
            temperature=0,  # Deterministic output
        )

        # Parse LLM response
        content = response.choices[0].message.content
        if content is None:
            logger.error("LLM response content is None")
            raise ValueError("LLM response content is None")

        logger.debug(f"LLM response received: {len(content)} chars")
        result = json.loads(content)

        # Convert to ParsedQuery
        intent = QueryIntent(result.get("intent", "unknown"))

        start_date = None
        if result.get("start_date"):
            start_date = date.fromisoformat(result["start_date"])

        end_date = None
        if result.get("end_date"):
            end_date = date.fromisoformat(result["end_date"])

        parsed_vendors = result.get("vendors", [])

        logger.info(
            f"Query parsed (LLM): intent={intent.value}, "
            f"vendors={len(parsed_vendors)}, "
            f"date_range={start_date} to {end_date}"
        )

        return ParsedQuery(
            intent=intent,
            vendors=parsed_vendors,
            start_date=start_date,
            end_date=end_date,
            raw_query=query,
        )


class QueryExecutor:
    """Execute queries based on parsed intent and entities."""

    def __init__(self, metrics_service: Optional[MetricsService] = None):
        self._metrics = metrics_service or get_metrics_service()
        self._data_loader = get_data_loader()

    def execute(self, parsed: ParsedQuery) -> QueryResult:
        """
        Execute a query based on parsed intent and entities.

        Args:
            parsed: LLM-parsed query with intent and entities.

        Returns:
            QueryResult with data and explanation.
        """
        logger.debug(f"Executing query: intent={parsed.intent.value}")

        try:
            match parsed.intent:
                case QueryIntent.LIST_VENDORS:
                    result = self._list_vendors()
                case QueryIntent.VENDOR_METRICS:
                    result = self._vendor_metrics(parsed)
                case QueryIntent.PERIOD_METRICS:
                    result = self._period_metrics(parsed)
                case QueryIntent.COMPARE_VENDORS:
                    result = self._compare_vendors()
                case QueryIntent.DRAWDOWN_ANALYSIS:
                    result = self._drawdown_analysis(parsed)
                case _:
                    result = self._unknown_query()

            logger.info(
                f"Query executed: intent={parsed.intent.value}, "
                f"success={result.success}"
            )
            return result

        except Exception as e:
            logger.error(
                f"Query execution failed: intent={parsed.intent.value}, "
                f"error={str(e)}"
            )
            return QueryResult(
                intent=parsed.intent,
                data=None,
                explanation=f"Error: {str(e)}",
                success=False,
                error=str(e),
            )

    def _list_vendors(self) -> QueryResult:
        """List all available vendors."""
        vendors = self._data_loader.get_vendors()
        return QueryResult(
            intent=QueryIntent.LIST_VENDORS,
            data={"vendors": vendors, "count": len(vendors)},
            explanation=f"Found {len(vendors)} vendors: {', '.join(vendors)}",
        )

    def _vendor_metrics(self, parsed: ParsedQuery) -> QueryResult:
        """Get metrics for specific vendor(s)."""
        if not parsed.vendors:
            return QueryResult(
                intent=QueryIntent.VENDOR_METRICS,
                data=None,
                explanation="No vendor specified. Please mention a vendor name.",
                success=False,
                error="No vendor specified",
            )

        results = {}
        for vendor in parsed.vendors:
            metrics = self._metrics.get_vendor_metrics(
                vendor, parsed.start_date, parsed.end_date
            )
            results[vendor] = {
                "vendor": metrics.vendor,
                "universes": metrics.universes,
                "record_count": metrics.record_count,
                "date_range": [str(d) for d in metrics.date_range],
                "signal_strength_mean": metrics.signal_strength_mean,
                "signal_strength_std": metrics.signal_strength_std,
                "drawdown_rate": metrics.drawdown_rate,
                "signal_volatility": metrics.signal_volatility,
                "avg_signal_during_drawdown": metrics.avg_signal_during_drawdown,
                "avg_signal_outside_drawdown": metrics.avg_signal_outside_drawdown,
            }

        return QueryResult(
            intent=QueryIntent.VENDOR_METRICS,
            data=results,
            explanation=f"Retrieved metrics for {', '.join(parsed.vendors)}",
        )

    def _period_metrics(self, parsed: ParsedQuery) -> QueryResult:
        """Get aggregated metrics for a time period."""
        period = self._metrics.get_period_metrics(parsed.start_date, parsed.end_date)

        date_desc = ""
        if parsed.start_date and parsed.end_date:
            date_desc = f"from {parsed.start_date} to {parsed.end_date}"
        elif parsed.start_date:
            date_desc = f"from {parsed.start_date}"

        return QueryResult(
            intent=QueryIntent.PERIOD_METRICS,
            data={
                "start_date": str(period.start_date),
                "end_date": str(period.end_date),
                "record_count": period.record_count,
                "vendor_count": period.vendor_count,
                "avg_signal_strength": period.avg_signal_strength,
                "total_drawdown_events": period.total_drawdown_events,
                "vendor_avg_signals": period.vendor_avg_signals,
                "vendor_drawdown_rates": period.vendor_drawdown_rates,
            },
            explanation=f"Aggregated metrics {date_desc} across {period.vendor_count} vendors",
        )

    def _compare_vendors(self) -> QueryResult:
        """Compare all vendors."""
        comparison = self._metrics.get_comparative_metrics()
        return QueryResult(
            intent=QueryIntent.COMPARE_VENDORS,
            data={
                "vendors": comparison.vendors,
                "best_avg_signal": comparison.best_avg_signal,
                "lowest_drawdown_rate": comparison.lowest_drawdown_rate,
                "highest_signal_volatility": comparison.highest_signal_volatility,
                "ranking_by_avg_signal": comparison.ranking_by_avg_signal,
                "ranking_by_stability": comparison.ranking_by_stability,
            },
            explanation=f"Best signal: {comparison.best_avg_signal}, Most stable: {comparison.lowest_drawdown_rate}",
        )

    def _drawdown_analysis(self, parsed: ParsedQuery) -> QueryResult:
        """Analyze drawdown periods."""
        vendor = parsed.vendors[0] if parsed.vendors else None
        analysis = self._metrics.get_drawdown_analysis(vendor)
        vendor_desc = f"for {vendor}" if vendor else "across all vendors"
        return QueryResult(
            intent=QueryIntent.DRAWDOWN_ANALYSIS,
            data=analysis,
            explanation=f"Drawdown analysis {vendor_desc}: {analysis['total_drawdown_events']} events",
        )

    def _unknown_query(self) -> QueryResult:
        """Handle unknown queries."""
        return QueryResult(
            intent=QueryIntent.UNKNOWN,
            data={
                "suggestions": [
                    "Try: 'metrics for AlphaSignals'",
                    "Try: 'compare all vendors'",
                    "Try: 'show drawdown periods'",
                    "Try: 'metrics in January 2020'",
                ]
            },
            explanation="I couldn't understand your query. See suggestions.",
            success=False,
            error="Unknown query intent",
        )


class QueryService:
    """
    Main service for processing natural language queries.

    Simple pipeline:
    1. LLM/Regex parses query → intent + entities
    2. Executor runs the appropriate query
    3. Return formatted result

    Falls back to regex parser when OpenAI API key is not configured.
    """

    def __init__(
        self,
        parser: Optional[QueryParser] = None,
        executor: Optional[QueryExecutor] = None,
    ):
        self._parser = parser or self._create_parser()
        self._executor = executor or QueryExecutor()

    def _create_parser(self) -> QueryParser:
        """Create the appropriate parser based on configuration."""
        try:
            parser = LLMQueryParser()
            logger.info("Using LLM-based query parser (OpenAI)")
            return parser
        except (ValueError, ImportError) as e:
            logger.warning(f"LLM parser unavailable ({e}), using regex fallback")
            return RegexQueryParser()

    def process_query(self, query: str) -> tuple[QueryResult, ParsedQuery]:
        """
        Process a natural language query.

        Args:
            query: Natural language query string.

        Returns:
            Tuple of (QueryResult with data and explanation, ParsedQuery with entities).
        """
        logger.info(
            f"Processing NL query: '{query[:80]}...'"
            if len(query) > 80
            else f"Processing NL query: '{query}'"
        )

        parsed = self._parser.parse(query)
        result = self._executor.execute(parsed)

        logger.info(
            f"Query processing complete: intent={parsed.intent.value}, "
            f"success={result.success}, "
            f"parser_type={type(self._parser).__name__}"
        )

        return result, parsed

    def get_supported_queries(self) -> list[dict]:
        """Get list of supported query patterns with examples."""
        return [
            {
                "intent": "vendor_metrics",
                "description": "Get metrics for a specific vendor",
                "examples": [
                    "What are the metrics for AlphaSignals?",
                    "Show me signal strength for BetaFlow",
                ],
            },
            {
                "intent": "period_metrics",
                "description": "Get aggregated metrics for a time period",
                "examples": [
                    "Metrics in January 2020",
                    "Show data from 2020-01-01 to 2020-02-01",
                ],
            },
            {
                "intent": "compare_vendors",
                "description": "Compare performance across vendors",
                "examples": ["Compare all vendors", "Which vendor is best?"],
            },
            {
                "intent": "drawdown_analysis",
                "description": "Analyze drawdown/stress periods",
                "examples": [
                    "Show drawdown periods",
                    "Analyze drawdowns for AlphaSignals",
                ],
            },
            {
                "intent": "list_vendors",
                "description": "List available vendors",
                "examples": ["List all vendors", "What vendors are available?"],
            },
        ]


def get_query_service() -> QueryService:
    """Factory function for QueryService (for FastAPI dependency injection)."""
    return QueryService()
