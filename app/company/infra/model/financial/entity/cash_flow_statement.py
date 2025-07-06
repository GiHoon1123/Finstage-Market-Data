from sqlalchemy import Column, Integer, String, Float, Date, UniqueConstraint
from app.common.infra.database.config.database_config import Base


class CashFlowStatement(Base):
    __tablename__ = "cash_flow_statements"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(16), index=True)
    date = Column(Date)
    operating_cash_flow = Column(Float)
    investing_cash_flow = Column(Float)
    financing_cash_flow = Column(Float)
    free_cash_flow = Column(Float)

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_cashflow_symbol_date"),
    )
