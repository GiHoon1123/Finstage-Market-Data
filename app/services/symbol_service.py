# app/services/company_service.py

from app.schemas.symbol_response import PaginatedSymbolResponse
from app.repositories import symbol_repository
from app.infra.db.db import SessionLocal
import math

def get_paginated_symbols(page: int, size: int) -> PaginatedSymbolResponse:
    session = SessionLocal()
    try:
        total, items = symbol_repository.get_symbols_with_pagination(session, page, size)

        total_pages = math.ceil(total / size)
        has_next = page < total_pages
        has_prev = page > 1

        return PaginatedSymbolResponse(
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
            items=items
        )
    finally:
        session.close()
