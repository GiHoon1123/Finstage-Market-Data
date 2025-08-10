from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date as DateType


class IncomeStatementResponse(BaseModel):
    """손익계산서 응답 모델"""

    id: int = Field(..., example=26, description="레코드 ID")
    symbol: str = Field(..., example="AAPL", description="주식 심볼")
    date: DateType = Field(..., example="2024-12-31", description="재무제표 기준일")
    revenue: Optional[int] = Field(
        None, example=54211000000, description="매출액 (달러)"
    )
    cost_of_revenue: Optional[int] = Field(
        None, example=37517000000, description="매출원가 (달러)"
    )
    gross_profit: Optional[int] = Field(
        None, example=16694000000, description="매출총이익 (달러)"
    )
    operating_income: Optional[int] = Field(
        None, example=2614000000, description="영업이익 (달러)"
    )
    net_income: Optional[int] = Field(
        None, example=846000000, description="순이익 (달러)"
    )
    eps: Optional[float] = Field(None, example=1.29, description="주당순이익")


class BalanceSheetResponse(BaseModel):
    """재무상태표 응답 모델"""

    id: int = Field(..., example=26, description="레코드 ID")
    symbol: str = Field(..., example="AAPL", description="주식 심볼")
    date: DateType = Field(..., example="2024-12-31", description="재무제표 기준일")
    total_assets: Optional[int] = Field(
        None, example=61783000000, description="총자산 (달러)"
    )
    total_liabilities: Optional[int] = Field(
        None, example=65760000000, description="총부채 (달러)"
    )
    total_equity: Optional[int] = Field(
        None, example=-3977000000, description="총자본 (달러)"
    )
    cash_and_equivalents: Optional[int] = Field(
        None, description="현금및현금성자산 (달러)"
    )
    inventory: Optional[int] = Field(None, description="재고자산 (달러)")


class CashFlowResponse(BaseModel):
    """현금흐름표 응답 모델"""

    id: int = Field(..., example=26, description="레코드 ID")
    symbol: str = Field(..., example="AAPL", description="주식 심볼")
    date: DateType = Field(..., example="2024-12-31", description="재무제표 기준일")
    operating_cash_flow: Optional[int] = Field(
        None, example=3983000000, description="영업활동현금흐름 (달러)"
    )
    investing_cash_flow: Optional[int] = Field(
        None, example=-968000000, description="투자활동현금흐름 (달러)"
    )
    financing_cash_flow: Optional[int] = Field(
        None, example=-2794000000, description="재무활동현금흐름 (달러)"
    )
    free_cash_flow: Optional[int] = Field(
        None, example=1300000000, description="잉여현금흐름 (달러)"
    )


class FinancialResponse(BaseModel):
    """종합 재무제표 응답 모델"""

    income_statement: List[IncomeStatementResponse] = Field(
        ..., description="손익계산서 데이터"
    )
    balance_sheet: List[BalanceSheetResponse] = Field(
        ..., description="재무상태표 데이터"
    )
    cash_flow: List[CashFlowResponse] = Field(..., description="현금흐름표 데이터")

    class Config:
        schema_extra = {
            "example": {
                "income_statement": [
                    {
                        "id": 26,
                        "symbol": "AAPL",
                        "date": "2024-12-31",
                        "revenue": 54211000000,
                        "cost_of_revenue": 37517000000,
                        "gross_profit": 16694000000,
                        "operating_income": 2614000000,
                        "net_income": 846000000,
                        "eps": 1.29,
                    }
                ],
                "balance_sheet": [
                    {
                        "id": 26,
                        "symbol": "AAPL",
                        "date": "2024-12-31",
                        "total_assets": 61783000000,
                        "total_liabilities": 65760000000,
                        "total_equity": -3977000000,
                        "cash_and_equivalents": None,
                        "inventory": None,
                    }
                ],
                "cash_flow": [
                    {
                        "id": 26,
                        "symbol": "AAPL",
                        "date": "2024-12-31",
                        "operating_cash_flow": 3983000000,
                        "investing_cash_flow": -968000000,
                        "financing_cash_flow": -2794000000,
                        "free_cash_flow": 1300000000,
                    }
                ],
            }
        }
