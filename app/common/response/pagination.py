from typing import TypeVar, Generic, List
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    page: int
    size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    items: List[T]
