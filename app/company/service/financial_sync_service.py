from datetime import datetime
import requests
from sqlalchemy.orm import Session
from app.common.infra.database.config.database_config import SessionLocal
from app.company.infra.model.symbol.repository import symbol_repository
from app.company.infra.model.financial.entity.income_statement import IncomeStatement
from app.company.infra.model.financial.entity.balance_sheet import BalanceSheet
from app.company.infra.model.financial.entity.cash_flow_statement import CashFlowStatement

API_KEY = "eoDSOYepbOmtV3vXmXuhsbhe7ncQ5A5y"
BASE_URL = "https://financialmodelingprep.com/api/v3"

def get_financial_statements(symbol: str):
    try:
        income_url = f"{BASE_URL}/income-statement/{symbol}?limit=5&apikey={API_KEY}"
        balance_url = f"{BASE_URL}/balance-sheet-statement/{symbol}?limit=5&apikey={API_KEY}"
        cashflow_url = f"{BASE_URL}/cash-flow-statement/{symbol}?limit=5&apikey={API_KEY}"

        income = requests.get(income_url).json()
        balance = requests.get(balance_url).json()
        cashflow = requests.get(cashflow_url).json()

        return {
            "income_statement": income,
            "balance_sheet": balance,
            "cash_flow": cashflow
        }
    except Exception as e:
        print(f"❌ [{symbol}] 데이터 수집 실패: {e}")
        return None
    
def sync_income_statements(session, symbol, income_data):
    def save(entry):
        date = datetime.strptime(entry["date"], "%Y-%m-%d").date()
        exists = session.query(IncomeStatement).filter_by(symbol=symbol, date=date).first()
        if exists:
            print(f"[→] IncomeStatement 중복 → {symbol} {date} → 패스")
            return False
        stmt = IncomeStatement(
            symbol=symbol,
            date=date,
            revenue=entry.get("revenue"),
            cost_of_revenue=entry.get("costOfRevenue"),
            gross_profit=entry.get("grossProfit"),
            operating_income=entry.get("operatingIncome"),
            net_income=entry.get("netIncome"),
            eps=entry.get("eps")
        )
        session.add(stmt)
        return True

    if isinstance(income_data, dict):
        return int(save(income_data))
    elif isinstance(income_data, list):
        return sum(save(entry) for entry in income_data)
    return 0

def sync_balance_sheets(session, symbol, balance_data):

    def save(entry):
        date = datetime.strptime(entry["date"], "%Y-%m-%d").date()
        exists = session.query(BalanceSheet).filter_by(symbol=symbol, date=date).first()
        if exists:
            print(f"[→] BalanceSheet 중복 → {symbol} {date} → 패스")
            return False
        stmt = BalanceSheet(
            symbol=symbol,
            date=date,
            total_assets=entry.get("totalAssets"),
            total_liabilities=entry.get("totalLiabilities"),
            total_equity=entry.get("totalEquity"),
            cash_and_equivalents=entry.get("cashAndCashEquivalents"),
            inventory=entry.get("inventory")
        )
        session.add(stmt)
        return True

    if isinstance(balance_data, dict):
        return int(save(balance_data))
    elif isinstance(balance_data, list):
        return sum(save(entry) for entry in balance_data)
    return 0

def sync_cash_flow_statements(session, symbol, cashflow_data):
    def save(entry):
        date = datetime.strptime(entry["date"], "%Y-%m-%d").date()
        exists = session.query(CashFlowStatement).filter_by(symbol=symbol, date=date).first()
        if exists:
            print(f"[→] CashFlowStatement 중복 → {symbol} {date} → 패스")
            return False
        stmt = CashFlowStatement(
            symbol=symbol,
            date=date,
            operating_cash_flow=entry.get("operatingCashFlow"),
            investing_cash_flow=entry.get("netCashUsedForInvestingActivites"),
            financing_cash_flow=entry.get("netCashUsedProvidedByFinancingActivities"),
            free_cash_flow=entry.get("freeCashFlow")
        )
        session.add(stmt)
        return True

    if isinstance(cashflow_data, dict):
        return int(save(cashflow_data))
    elif isinstance(cashflow_data, list):
        return sum(save(entry) for entry in cashflow_data)
    return 0


def sync_financials(session: Session, symbol: str, data: dict):
    inserted = 0

    inserted += sync_income_statements(session, symbol, data.get("income_statement"))
    inserted += sync_balance_sheets(session, symbol, data.get("balance_sheet"))
    inserted += sync_cash_flow_statements(session, symbol, data.get("cash_flow"))

    session.commit()
    print(f"[✓] {symbol}: {inserted}건 저장")


def run_financial_sync():
    db = SessionLocal()
    try:
        symbols = symbol_repository.get_all_symbols(db)

        for symbol_obj in symbols:
            symbol = symbol_obj.symbol
            print(f"🚀 {symbol} 재무제표 동기화 중...")

            data = get_financial_statements(symbol)
            if data:
                sync_financials(db, symbol, data)

    finally:
        db.close()


if __name__ == "__main__":
    run_financial_sync()