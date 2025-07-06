from sqlalchemy.orm import Session
from app.company.infra.model.financial.entity.income_statement import IncomeStatement
from app.company.infra.model.financial.entity.balance_sheet import BalanceSheet
from app.company.infra.model.financial.entity.cash_flow_statement import CashFlowStatement


def save_income_statement(session: Session, symbol, date, revenue, cost_of_revenue, gross_profit, operating_income, net_income, eps):
    stmt = IncomeStatement(
        symbol=symbol,
        date=date,
        revenue=revenue,
        cost_of_revenue=cost_of_revenue,
        gross_profit=gross_profit,
        operating_income=operating_income,
        net_income=net_income,
        eps=eps,
    )
    session.add(stmt)


def save_balance_sheet(session: Session, symbol, date, total_assets, total_liabilities, total_equity):
    stmt = BalanceSheet(
        symbol=symbol,
        date=date,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
    )
    session.add(stmt)


def save_cash_flow_statement(session: Session, symbol, date, operating_cash_flow, investing_cash_flow, financing_cash_flow, free_cash_flow):
    stmt = CashFlowStatement(
        symbol=symbol,
        date=date,
        operating_cash_flow=operating_cash_flow,
        investing_cash_flow=investing_cash_flow,
        financing_cash_flow=financing_cash_flow,
        free_cash_flow=free_cash_flow,
    )
    session.add(stmt)


def get_income_statements(session: Session, symbol: str):
    return (
        session.query(IncomeStatement)
        .filter_by(symbol=symbol)
        .order_by(IncomeStatement.date.desc())
        .all()
    )


def get_balance_sheets(session: Session, symbol: str):
    return (
        session.query(BalanceSheet)
        .filter_by(symbol=symbol)
        .order_by(BalanceSheet.date.desc())
        .all()
    )


def get_cash_flow_statements(session: Session, symbol: str):
    return (
        session.query(CashFlowStatement)
        .filter_by(symbol=symbol)
        .order_by(CashFlowStatement.date.desc())
        .all()
    )
