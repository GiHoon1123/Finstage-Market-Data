import requests
from typing import Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from app.repositories.financial_repository import FinancialRepository

API_KEY = "eoDSOYepbOmtV3vXmXuhsbhe7ncQ5A5y"
BASE_URL = "https://financialmodelingprep.com/api/v3"

class FinancialService:
    def get_statements_from_db(self, symbol: str) -> Optional[Dict]:
        income = self.repo.get_income_statements(symbol)
        balance = self.repo.get_balance_sheets(symbol)
        cashflow = self.repo.get_cash_flow_statements(symbol)

        if not (income or balance or cashflow):
            return None

        return {
            "income_statement": [i.__dict__ for i in income],
            "balance_sheet": [b.__dict__ for b in balance],
            "cash_flow": [c.__dict__ for c in cashflow],
        }


    def __init__(self, db: Session):
        self.api_key = API_KEY
        self.repo = FinancialRepository(db)

    def get_financial_statements(self, symbol: str) -> Optional[Dict]:
        try:
            income_url = f"{BASE_URL}/income-statement/{symbol}?limit=5&apikey={self.api_key}"
            balance_url = f"{BASE_URL}/balance-sheet-statement/{symbol}?limit=5&apikey={self.api_key}"
            cashflow_url = f"{BASE_URL}/cash-flow-statement/{symbol}?limit=5&apikey={self.api_key}"

            income = requests.get(income_url).json()
            balance = requests.get(balance_url).json()
            cashflow = requests.get(cashflow_url).json()

            return {
                "income_statement": income,
                "balance_sheet": balance,
                "cash_flow": cashflow
            }
        except Exception as e:
            print(f"데이터 수집 오류: {e}")
            return None

    def search_symbol(self, company_name: str) -> Optional[str]:
        try:
            url = f"{BASE_URL}/search?query={company_name}&limit=5&exchange=NASDAQ&apikey={self.api_key}"
            response = requests.get(url).json()
            return response[0]["symbol"] if response else None
        except Exception as e:
            print(f"티커 검색 실패: {e}")
            return None

    def save_statements_to_db(self, symbol: str, data: Dict):
        # 손익계산서 저장
        for entry in data["income_statement"]:
            self.repo.save_income_statement(
                symbol=symbol,
                date=datetime.strptime(entry["date"], "%Y-%m-%d"),
                revenue=entry.get("revenue"),
                cost_of_revenue=entry.get("costOfRevenue"),
                gross_profit=entry.get("grossProfit"),
                operating_income=entry.get("operatingIncome"),
                net_income=entry.get("netIncome"),
                eps=entry.get("eps")
            )

        # 재무상태표 저장
        for entry in data["balance_sheet"]:
            self.repo.save_balance_sheet(
                symbol=symbol,
                date=datetime.strptime(entry["date"], "%Y-%m-%d"),
                total_assets=entry.get("totalAssets"),
                total_liabilities=entry.get("totalLiabilities"),
                total_equity=entry.get("totalEquity")
            )

        # 현금흐름표 저장
        for entry in data["cash_flow"]:
            self.repo.save_cash_flow_statement(
                symbol=symbol,
                date=datetime.strptime(entry["date"], "%Y-%m-%d"),
                operating_cash_flow=entry.get("operatingCashFlow"),
                investing_cash_flow=entry.get("netCashUsedForInvestingActivites"),
                financing_cash_flow=entry.get("netCashUsedProvidedByFinancingActivities"),
                free_cash_flow=entry.get("freeCashFlow")
            )

        self.repo.commit()

# 테스트용 예제 (직접 실행할 때만 동작)
if __name__ == "__main__":
    from app.infra.db.db import SessionLocal

    db = SessionLocal()
    service = FinancialService(db)

    symbol = service.search_symbol("Apple")
    print("✅ 티커:", symbol)

    if symbol:
        data = service.get_financial_statements(symbol)
        service.save_statements_to_db(symbol, data)
        print("✅ DB 저장 완료")
