"""Query API v1 routes - Natural language queries about vendor metrics."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.models import (
    QueryEntities,
    QueryRequest,
    QueryResponse,
    SupportedQueryResponse,
)
from app.services import QueryService, get_query_service

router = APIRouter(prefix="/query", tags=["Natural Language Queries v1"])

QueryServiceDep = Annotated[QueryService, Depends(get_query_service)]


@router.post("", response_model=QueryResponse, summary="Process natural language query")
async def process_query(
    request: QueryRequest,
    query_service: QueryServiceDep,
) -> QueryResponse:
    """Process a natural language query about vendor metrics."""
    result, parsed = query_service.process_query(request.query)
    return QueryResponse(
        intent=result.intent.value,
        entities=QueryEntities(
            vendors=parsed.vendors,
            start_date=str(parsed.start_date) if parsed.start_date else None,
            end_date=str(parsed.end_date) if parsed.end_date else None,
        ),
        data=result.data,
        explanation=result.explanation,
        success=result.success,
        error=result.error,
    )


@router.get("/supported", response_model=list[SupportedQueryResponse])
async def get_supported_queries(
    query_service: QueryServiceDep,
) -> list[SupportedQueryResponse]:
    """Get supported query patterns with examples."""
    return [SupportedQueryResponse(**p) for p in query_service.get_supported_queries()]
