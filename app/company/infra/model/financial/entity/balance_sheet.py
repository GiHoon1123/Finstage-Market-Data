from sqlalchemy import Column, Integer, String, Float, Date, UniqueConstraint
from app.common.infra.database.config.database_config import Base


class BalanceSheet(Base):
    __tablename__ = "balance_sheets"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(16), index=True)
    date = Column(Date)
    total_assets = Column(Float)
    total_liabilities = Column(Float)
    total_equity = Column(Float)
    cash_and_equivalents = Column(Float)
    inventory = Column(Float)

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_balance_symbol_date"),
    )
