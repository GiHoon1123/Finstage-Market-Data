from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from app.services.financial_service import FinancialService
from app.infra.db.db import get_db
import pandas as pd
import json



router = APIRouter()

def safe_df_to_dict(df: pd.DataFrame) -> dict:
    return json.loads(df.to_json())

@router.get(
    "/financials",
    summary="재무제표 조회",
    tags=["Financial"],
    responses={
        200: {
            "description": "성공적으로 재무제표를 조회했습니다.",
            "content": {
                "application/json": {
                    "example": {
                        "income_statement": [
                            {
                                "id": 26,
                                "symbol": "AAL",
                                "date": "2024-12-31",
                                "gross_profit": 16694000000,
                                "net_income": 846000000,
                                "cost_of_revenue": 37517000000,
                                "revenue": 54211000000,
                                "operating_income": 2614000000,
                                "eps": 1.29
                            }
                        ],
                        "balance_sheet": [
                            {
                                "id": 26,
                                "symbol": "AAL",
                                "date": "2024-12-31",
                                "total_assets": 61783000000,
                                "total_liabilities": 65760000000,
                                "total_equity": -3977000000,
                                "inventory": None,
                                "cash_and_equivalents": None
                            }
                        ],
                        "cash_flow": [
                            {
                                "id": 26,
                                "symbol": "AAL",
                                "date": "2024-12-31",
                                "operating_cash_flow": 3983000000,
                                "investing_cash_flow": -968000000,
                                "financing_cash_flow": -2794000000,
                                "free_cash_flow": 1300000000
                            }
                        ]
                    }
                }
            }
        },
        404: {
            "description": "심볼이 존재하지 않습니다.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "해당 심볼은 존재하지 않습니다."
                    }
                }
            }
        },
        422: {
            "description": "잘못된 요청 매개변수로 인해 요청이 실패했습니다.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["query", "symbol"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
                    }
                }
            }
        }
    }
)
def get_financials(symbol: str = Query(..., example="AAL"), db: Session = Depends(get_db)):
    service = FinancialService(db)
    result = service.load_statements(symbol)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="해당 심볼에 대한 데이터가 존재하지 않습니다."
        )

    return result