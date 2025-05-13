# models/company.py

from sqlalchemy import Column, String
from app.infra.db.db import Base

class Symbol(Base):
    __tablename__ = "symbols"

    symbol = Column(String(10), primary_key=True)
    name = Column(String(255), nullable=False)
    country = Column(String(100), nullable=True)


from sqlalchemy import Column, Integer, String, Float, Date
from app.infra.db.db import Base



