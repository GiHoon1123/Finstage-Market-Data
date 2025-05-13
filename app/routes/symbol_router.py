from fastapi import APIRouter, Query
from app.services.symbol_service import get_paginated_symbols
from app.schemas.symbol_response import PaginatedSymbolResponse



router = APIRouter()

@router.get(
        "/symbols",
        response_model=PaginatedSymbolResponse,
        )
def list_symbols(
    page: int = Query(1, description="Page number (starts from 1)", ge=1),
    size: int = Query(20, description="Number of items per page", ge=1, le=100)
):
    return get_paginated_symbols(page, size)
