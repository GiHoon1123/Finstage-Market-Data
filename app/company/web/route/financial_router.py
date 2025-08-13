from fastapi import APIRouter, Path, HTTPException
from app.company.handler.financial_handler import handle_get_financials
from app.company.dto.financial_response import FinancialResponse
from app.common.dto.api_response import ApiResponse
from app.common.utils.response_helper import (
    success_response,
    not_found_response,
    handle_service_error,
)

router = APIRouter()


@router.get(
    "/financials/{symbol}",
    response_model=ApiResponse,
    summary="기업 재무제표 조회",
    description="""
    특정 기업의 종합 재무제표 정보를 조회합니다.
    
    **포함 데이터:**
    - **손익계산서**: 매출, 비용, 순이익 등
    - **재무상태표**: 자산, 부채, 자본 등  
    - **현금흐름표**: 영업/투자/재무 활동 현금흐름
    
    **사용 예시:**
    - 기업 분석 및 투자 의사결정
    - 재무 건전성 평가
    - 수익성 및 성장성 분석
    """,
    tags=["Company Financials"],
    responses={
        200: {
            "description": "재무제표를 성공적으로 조회했습니다.",
            "content": {
                "application/json": {
                    "example": {
                        "status": 200,
                        "message": "AAPL 재무제표 조회가 완료되었습니다",
                        "data": {
                            "symbol": "AAPL",
                            "income_statement": {
                                "revenue": 394328000000,
                                "net_income": 96995000000,
                                "fiscal_year": 2023
                            },
                            "balance_sheet": {
                                "total_assets": 352755000000,
                                "total_liabilities": 287912000000,
                                "total_equity": 64843000000
                            },
                            "cash_flow": {
                                "operating_cash_flow": 110543000000,
                                "investing_cash_flow": -10982000000,
                                "financing_cash_flow": -110749000000
                            }
                        }
                    }
                }
            },
        },
        404: {
            "description": "해당 심볼의 재무제표를 찾을 수 없습니다.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Symbol 'INVALID' not found in financial database"
                    }
                }
            },
        },
        422: {
            "description": "잘못된 심볼 형식입니다.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["path", "symbol"],
                                "msg": "심볼은 1-10자의 영문자여야 합니다",
                                "type": "value_error",
                            }
                        ]
                    }
                }
            },
        },
    },
)
def get_financials(
    symbol: str = Path(
        ...,
        example="AAPL",
        description="조회할 기업의 주식 심볼 (예: AAPL, MSFT, GOOGL)",
        min_length=1,
        max_length=10,
        regex="^[A-Z]+$",
    )
) -> ApiResponse:
    """
    기업의 종합 재무제표 정보를 조회합니다.

    최신 재무제표 데이터를 기반으로 손익계산서, 재무상태표, 현금흐름표를 제공합니다.
    """
    try:
        financial_data = handle_get_financials(symbol)
        
        return success_response(
            data=financial_data,
            message=f"{symbol} 재무제표 조회가 완료되었습니다"
        )
    except Exception as e:
        handle_service_error(e, f"{symbol} 재무제표 조회 실패")
