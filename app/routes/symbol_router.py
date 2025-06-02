from fastapi import APIRouter, Query
from app.services.symbol_service import get_paginated_symbols

router = APIRouter()

@router.get(
    "/symbols",
    summary="심볼 목록 조회 (페이지네이션)",
    tags=["Symbol"],
    responses={
        200: {
            "description": "심볼 목록을 성공적으로 조회했습니다.",
            "content": {
                "application/json": {
                    "example": {
                        "total": 3814,
                        "page": 1,
                        "size": 1,
                        "total_pages": 3814,
                        "has_next": True,
                        "has_prev": False,
                        "items": [
                            {
                                "symbol": "AACB",
                                "name": "Artius II Acquisition Inc. Class A Ordinary Shares",
                                "country": "United States"
                            }
                        ]
                    }
                }
            }
        }
    }
)
def list_symbols(
    page: int = Query(1, description="Page number (starts from 1)", ge=1),
    size: int = Query(20, description="Number of items per page", ge=1, le=100)
):
    return get_paginated_symbols(page, size)
