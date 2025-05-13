# app/schemas/company_response.py (또는 symbol_response.py)

from pydantic import BaseModel, ConfigDict
from typing import List

class SymbolResponse(BaseModel):
    symbol: str
    name: str
    country: str

    model_config = ConfigDict(from_attributes=True)


class PaginatedSymbolResponse(BaseModel):
    total: int
    page: int
    size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    items: List[SymbolResponse]
