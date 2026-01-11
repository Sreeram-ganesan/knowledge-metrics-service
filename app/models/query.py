"""Natural language query schemas."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Natural language query request."""

    query: str = Field(
        min_length=3,
        max_length=500,
        description="Natural language query about vendor metrics",
        json_schema_extra={
            "examples": [
                "What are the metrics for AlphaSignals?",
                "Compare all vendors",
                "Show drawdown periods in January 2020",
            ]
        },
    )


class QueryEntities(BaseModel):
    """Entities extracted from the query."""

    vendors: list[str] = Field(
        default_factory=list, description="Vendor names mentioned"
    )
    start_date: Optional[str] = Field(
        default=None, description="Start date if mentioned"
    )
    end_date: Optional[str] = Field(default=None, description="End date if mentioned")


class QueryResponse(BaseModel):
    """Natural language query response."""

    intent: str = Field(description="Classified query intent")
    entities: QueryEntities = Field(description="Extracted entities from query")
    data: Optional[Any] = Field(default=None, description="Query result data")
    explanation: str = Field(description="Human-readable explanation")
    success: bool = Field(default=True, description="Whether query succeeded")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class SupportedQueryResponse(BaseModel):
    """Supported query patterns."""

    intent: str = Field(description="Intent identifier")
    description: str = Field(description="What this query type does")
    examples: list[str] = Field(description="Example queries")
