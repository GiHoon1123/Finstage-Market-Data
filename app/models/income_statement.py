from sqlalchemy import Column, Integer, String, Float, Date
from app.infra.db.db import Base

class IncomeStatement(Base):
    __tablename__ = "income_statements"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(16), index=True)
    date = Column(Date)
    revenue = Column(Float)
    cost_of_revenue = Column(Float)
    gross_profit = Column(Float)
    operating_income = Column(Float)
    net_income = Column(Float)
    eps = Column(Float)