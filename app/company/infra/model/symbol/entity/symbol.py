from sqlalchemy import Column, Integer, String
from app.common.infra.database.config.database_config import Base


class Symbol(Base):
    __tablename__ = "symbols"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, unique=True)  
    name = Column(String(255), nullable=False)
    country = Column(String(100), nullable=True)
    korea_name = Column(String(255), nullable=True)
