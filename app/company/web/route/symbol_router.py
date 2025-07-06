from fastapi import APIRouter, Query
from app.company.handler.symbol_handler import handle_get_paginated_symbols
import pandas as pd
import json


router = APIRouter()

def safe_df_to_dict(df: pd.DataFrame) -> dict:
    return json.loads(df.to_json())

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
def get_symbols(
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)"),
    size: int = Query(10, ge=1, le=100, description="페이지당 항목 수 (최대 100)")
):
    result = handle_get_paginated_symbols(page, size)
    if not result.items:
        return {
            "total": 0,
            "page": page,
            "size": size,
            "total_pages": 0,
            "has_next": False,
            "has_prev": False,
            "items": []
        }
    return result
