import requests
from typing import Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.repositories.financial_repository import FinancialRepository
from app.models.income_statement import IncomeStatement
from app.models.balance_sheet import BalanceSheet
from app.models.cash_flow_statement import CashFlowStatement

API_KEY = "eoDSOYepbOmtV3vXmXuhsbhe7ncQ5A5y"
BASE_URL = "https://financialmodelingprep.com/api/v3"

class FinancialService:
    def __init__(self, db: Session):
        self.api_key = API_KEY
        self.repo = FinancialRepository(db)
        self.db = db

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

    def search_symbol(self, symbol: str) -> Optional[str]:
        # 심볼 검증용으로만 사용. 반드시 심볼을 직접 입력해야 함.
        try:
            url = f"{BASE_URL}/profile/{symbol}?apikey={self.api_key}"
            response = requests.get(url).json()
            if response and isinstance(response, list):
                return response[0]["symbol"]
            return None
        except Exception as e:
            print(f"티커 검증 실패: {e}")
            return None

    def save_statements_to_db(self, symbol: str, data: Dict) -> bool:
        try:
            # 이미 존재하는지 확인
            existing = self.repo.get_income_statements(symbol)
            if existing:
                print(f"🔄 이미 존재하는 심볼({symbol}), 저장 생략")
                return True

            # 트랜잭션 시작
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

            for entry in data["balance_sheet"]:
                self.repo.save_balance_sheet(
                    symbol=symbol,
                    date=datetime.strptime(entry["date"], "%Y-%m-%d"),
                    total_assets=entry.get("totalAssets"),
                    total_liabilities=entry.get("totalLiabilities"),
                    total_equity=entry.get("totalEquity")
                )

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
            return True

        except SQLAlchemyError as e:
            print(f"❌ DB 저장 중 오류 발생: {e}")
            self.db.rollback()
            return False

    def load_statements(self, symbol: str) -> Optional[Dict]:
        income = self.repo.get_income_statements(symbol)
        balance = self.repo.get_balance_sheets(symbol)
        cashflow = self.repo.get_cash_flow_statements(symbol)

        if not (income or balance or cashflow):
            return None

        return {
            "income_statement": [self._serialize_model(i) for i in income],
            "balance_sheet": [self._serialize_model(b) for b in balance],
            "cash_flow": [self._serialize_model(c) for c in cashflow],
        }

    def _serialize_model(self, model):
        data = model.__dict__.copy()
        data.pop("_sa_instance_state", None)
        return data

# 테스트용 예제 (직접 실행할 때만 동작)
if __name__ == "__main__":
    from app.infra.db.db import SessionLocal

    db = SessionLocal()
    service = FinancialService(db)

    symbol = "META"  # 심볼로 직접 지정
    print("✅ 티커:", symbol)

    data = service.get_financial_statements(symbol)
    if data:
        success = service.save_statements_to_db(symbol, data)
        print("✅ DB 저장 완료" if success else "❌ 저장 실패")

        result = service.load_statements(symbol)
        print("✅ DB 조회 결과:", result)

    db.close()
