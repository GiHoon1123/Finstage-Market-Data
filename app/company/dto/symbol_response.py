from pydantic import BaseModel

class SymbolResponse(BaseModel):
    symbol: str
    name: str
    country: str
    korea_name: str | None = None

    class Config:
        from_attributes = True  # v2에선 ORM mode
