from sqlalchemy import Column, BigInteger, String, Float, DateTime
from datetime import datetime
from app.common.infra.database.config.database_config import Base


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="PK")
    
    symbol = Column(String(20), nullable=False, index=True, comment="종목 코드 (예: AAPL, ^IXIC)")
    source = Column(String(30), nullable=False, comment="데이터 제공자 (예: yahoo, investing)")
    
    open = Column(Float, nullable=True, comment="시가")
    close = Column(Float, nullable=True, comment="종가")
    high = Column(Float, nullable=True, comment="고가")
    low = Column(Float, nullable=True, comment="저가")
    volume = Column(Float, nullable=True, comment="거래량")

    snapshot_at = Column(DateTime, nullable=False, comment="가격 기준 시각 (예: 2024-07-08 00:00)")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="저장된 시각")

    def __repr__(self):
        return f"<PriceSnapshot(symbol={self.symbol}, snapshot_at={self.snapshot_at})>"
