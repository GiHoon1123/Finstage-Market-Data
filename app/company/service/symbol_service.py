from app.common.response.pagination import PaginatedResponse
from app.company.infra.model.symbol.repository import symbol_repository
from app.common.infra.database.config.database_config import SessionLocal
from app.company.dto.symbol_response import SymbolResponse

import math

def get_paginated_symbols(page: int, size: int) -> PaginatedResponse[SymbolResponse]:
    session = SessionLocal()
    try:
        total, items = symbol_repository.get_symbols_with_pagination(session, page, size)

        total_pages = math.ceil(total / size)
        has_next = page < total_pages
        has_prev = page > 1

        # SQLAlchemy 모델 → Pydantic 모델로 변환
        symbol_dtos = [SymbolResponse.model_validate(item) for item in items]

        return PaginatedResponse[SymbolResponse](
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
            items=symbol_dtos
        )
    finally:
        session.close()
