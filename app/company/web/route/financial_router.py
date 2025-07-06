
from fastapi import APIRouter
from app.company.handler.financial_handler import handle_get_financials

router = APIRouter()

@router.get("/financials/{symbol}",
summary="특정 심볼의 재무제표를 보여줌",
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
}
)
def get_financials(symbol: str):
    return handle_get_financials(symbol)
