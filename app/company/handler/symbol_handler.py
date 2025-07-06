from app.company.service.symbol_service import get_paginated_symbols
from app.common.response.pagination import PaginatedResponse
from app.company.dto.symbol_response import SymbolResponse

def handle_get_paginated_symbols(page: int, size: int) -> PaginatedResponse[SymbolResponse]:
    return get_paginated_symbols(page, size)
