from typing import Optional, Dict
from sqlalchemy.orm import Session
from app.common.infra.database.config.database_config import SessionLocal
from app.company.infra.model.symbol.repository.symbol_repository import exists_symbol
from app.company.infra.model.financial.entity.income_statement import IncomeStatement
from app.company.infra.model.financial.entity.balance_sheet import BalanceSheet
from app.company.infra.model.financial.entity.cash_flow_statement import CashFlowStatement

def serialize_model(model) -> Dict:
    data = model.__dict__.copy()
    data.pop("_sa_instance_state", None)
    return data

def load_statements(symbol: str) -> Optional[Dict]:
    """DB 세션을 내부에서 생성해서 사용"""
    session: Session = SessionLocal()
    try:
        if not exists_symbol(session, symbol):
            print(f"❌ 심볼({symbol})은 심볼 테이블에 존재하지 않음")
            return None

        income = session.query(IncomeStatement).filter_by(symbol=symbol).order_by(IncomeStatement.date.desc()).all()
        balance = session.query(BalanceSheet).filter_by(symbol=symbol).order_by(BalanceSheet.date.desc()).all()
        cashflow = session.query(CashFlowStatement).filter_by(symbol=symbol).order_by(CashFlowStatement.date.desc()).all()

        return {
            "income_statement": [serialize_model(i) for i in income],
            "balance_sheet": [serialize_model(b) for b in balance],
            "cash_flow": [serialize_model(c) for c in cashflow],
        }

    finally:
        session.close()
