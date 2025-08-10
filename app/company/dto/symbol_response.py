from pydantic import BaseModel, Field
from typing import Optional


class SymbolResponse(BaseModel):
    """심볼 정보 응답 모델"""

    symbol: str = Field(
        ..., example="AAPL", description="주식 심볼 코드", min_length=1, max_length=10
    )

    name: str = Field(..., example="Apple Inc.", description="회사명", min_length=1)

    country: Optional[str] = Field(
        None, example="United States", description="상장 국가"
    )

    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "country": "United States",
            }
        }

    country: str
    korea_name: str | None = None

    class Config:
        from_attributes = True  # v2에선 ORM mode
