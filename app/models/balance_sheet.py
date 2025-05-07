from sqlalchemy import Column, Integer, String, Float, Date
from app.infra.db.db import Base



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
