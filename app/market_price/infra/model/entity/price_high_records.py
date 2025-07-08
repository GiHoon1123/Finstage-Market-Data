from sqlalchemy import Column, BigInteger, String, Float, DateTime
from datetime import datetime
from app.common.infra.database.config.database_config import Base


class PriceHighRecord(Base):
    __tablename__ = "price_high_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    symbol = Column(String(20), nullable=False, index=True, comment="종목 코드")
    source = Column(String(30), nullable=False, comment="데이터 제공자 (예: yahoo)")
    price = Column(Float, nullable=False, comment="기록된 최고가")
    recorded_at = Column(DateTime, nullable=False, comment="해당 고점이 기록된 시점")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="기록 저장 시각")

    def __repr__(self):
        return f"<PriceHighRecord(symbol={self.symbol}, price={self.price})>"
