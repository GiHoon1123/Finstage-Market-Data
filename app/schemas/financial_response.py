from typing import Dict, Optional, Any
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.services.financial_service import FinancialService

router = APIRouter()

class FinancialStatementResponse(BaseModel):
    income_statement: Dict[str, Dict[str, Optional[float]]]
    balance_sheet: Dict[str, Dict[str, Optional[float]]]
    cash_flow: Dict[str, Dict[str, Optional[float]]]

    class Config:
        schema_extra = {
            "example": {
                "income_statement": {
                    "2024-09-30": {
                        "Total Revenue": 391035000000,
                        "Net Income": 93736000000,
                        "Diluted EPS": 6.08,
                        "Research And Development": 31370000000
                    },
                    "2023-09-30": {
                        "Total Revenue": 383285000000,
                        "Net Income": 96995000000,
                        "Diluted EPS": 6.13,
                        "Research And Development": 29915000000
                    }
                },
                "balance_sheet": {
                    "2024-09-30": {
                        "Total Assets": 364980000000,
                        "Total Liabilities Net Minority Interest": 308030000000,
                        "Stockholders Equity": 56950000000
                    }
                },
                "cash_flow": {
                    "2024-09-30": {
                        "Operating Cash Flow": 118254000000,
                        "Free Cash Flow": 108807000000,
                        "Capital Expenditure": -9447000000
                    }
                }
            }
        }

@router.get("/financials", response_model=FinancialStatementResponse, summary="재무제표 조회", tags=["Financial"])
async def get_financials(company: str = Query(..., example="Apple")):
    """
    입력한 회사명에 대해 손익계산서, 재무상태표, 현금흐름표 데이터를 제공합니다.

    - **company**: 예) Apple, Samsung, Microsoft
    """
    service = FinancialService()
    result = service.get_financial_statements(company)

    if result is None:
        raise HTTPException(status_code=404, detail="Company not found or financials unavailable")

    return result
