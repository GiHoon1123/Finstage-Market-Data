from sqlalchemy.orm import Session
from app.models.income_statement import IncomeStatement
from app.models.balance_sheet import BalanceSheet
from app.models.cash_flow_statement import CashFlowStatement

class FinancialRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_income_statement(self, symbol, date, revenue, cost_of_revenue, gross_profit, operating_income, net_income, eps):
        stmt = IncomeStatement(
            symbol=symbol,
            date=date,
            revenue=revenue,
            cost_of_revenue=cost_of_revenue,
            gross_profit=gross_profit,
            operating_income=operating_income,
            net_income=net_income,
            eps=eps
        )
        self.db.add(stmt)

    def save_balance_sheet(self, symbol, date, total_assets, total_liabilities, total_equity):
        stmt = BalanceSheet(
            symbol=symbol,
            date=date,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            total_equity=total_equity
        )
        self.db.add(stmt)

    def save_cash_flow_statement(self, symbol, date, operating_cash_flow, investing_cash_flow, financing_cash_flow, free_cash_flow):
        stmt = CashFlowStatement(
            symbol=symbol,
            date=date,
            operating_cash_flow=operating_cash_flow,
            investing_cash_flow=investing_cash_flow,
            financing_cash_flow=financing_cash_flow,
            free_cash_flow=free_cash_flow
        )
        self.db.add(stmt)

    def commit(self):
        self.db.commit()

    
    def get_income_statements(self, symbol: str):
        return self.db.query(IncomeStatement).filter_by(symbol=symbol).order_by(IncomeStatement.date.desc()).all()

    def get_balance_sheets(self, symbol: str):
        return self.db.query(BalanceSheet).filter_by(symbol=symbol).order_by(BalanceSheet.date.desc()).all()

    def get_cash_flow_statements(self, symbol: str):
        return self.db.query(CashFlowStatement).filter_by(symbol=symbol).order_by(CashFlowStatement.date.desc()).all()
