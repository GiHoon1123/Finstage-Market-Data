from fastapi import APIRouter, Query
from app.company.handler.symbol_handler import handle_get_paginated_symbols
from app.company.dto.symbol_response import SymbolResponse
from app.common.config.api_metadata import common_responses
from app.common.dto.api_response import ApiResponse
from app.common.utils.response_helper import paginated_response, handle_service_error
import pandas as pd
import json


router = APIRouter()


def safe_df_to_dict(df: pd.DataFrame) -> dict:
    return json.loads(df.to_json())


@router.get(
    "/symbols",
    response_model=ApiResponse,
    summary="주식 심볼 목록 조회",
    description="""
    등록된 모든 주식 심볼의 페이지네이션된 목록을 조회합니다.
    
    **주요 기능:**
    - 페이지네이션 지원으로 대용량 데이터 효율적 조회
    - 심볼, 회사명, 상장 국가 정보 제공
    - 검색 및 필터링 기능 (향후 추가 예정)
    
    **사용 사례:**
    - 주식 선택 드롭다운 메뉴 구성
    - 심볼 검색 자동완성 기능
    - 포트폴리오 구성을 위한 종목 탐색
    
    **성능 최적화:**
    - 페이지당 최대 100개 항목으로 제한
    - 캐싱을 통한 빠른 응답 속도
    """,
    tags=["Symbol"],
    responses={
        **common_responses,
        200: {
            "description": "심볼 목록을 성공적으로 조회했습니다.",
            "content": {
                "application/json": {
                    "example": {
                        "status": 200,
                        "message": "심볼 목록 조회가 완료되었습니다",
                        "data": {
                            "items": [
                                {
                                    "symbol": "AAPL",
                                    "company_name": "Apple Inc.",
                                    "country": "US",
                                    "sector": "Technology"
                                },
                                {
                                    "symbol": "MSFT",
                                    "company_name": "Microsoft Corporation",
                                    "country": "US",
                                    "sector": "Technology"
                                }
                            ],
                            "pagination": {
                                "page": 1,
                                "size": 10,
                                "total": 100,
                                "total_pages": 10,
                                "has_next": True,
                                "has_prev": False
                            }
                        }
                    }
                }
            },
        },
    },
)
def get_symbols(
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)", example=1),
    size: int = Query(
        10, ge=1, le=100, description="페이지당 항목 수 (최대 100개)", example=10
    ),
):
    """
    주식 심볼 목록을 페이지네이션하여 조회합니다.

    전체 심볼 데이터베이스에서 요청된 페이지의 심볼들을 반환하며,
    각 심볼에 대한 기본 정보(심볼 코드, 회사명, 상장 국가)를 포함합니다.
    """
    try:
        result = handle_get_paginated_symbols(page, size)

        return paginated_response(
            items=result.items if result.items else [],
            page=page,
            size=size,
            total=result.total if result else 0,
            message="심볼 목록 조회가 완료되었습니다",
        )
    except Exception as e:
        handle_service_error(e, "심볼 목록 조회 실패")
