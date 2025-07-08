from sqlalchemy import Column, BigInteger, String, Float, DateTime
from datetime import datetime
from app.common.infra.database.config.database_config import Base


class PriceAlertLog(Base):
    __tablename__ = "price_alert_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="PK")

    symbol = Column(String(20), nullable=False, index=True, comment="종목 코드")

    alert_type = Column(String(30), nullable=False, comment="알림 종류 (예: price_drop, price_rise)")

    base_type = Column(String(30), nullable=False, comment="기준 종류 (예: previous_close, all_time_high)")
    base_price = Column(Float, nullable=False, comment="기준 가격")
    current_price = Column(Float, nullable=False, comment="현재 가격")

    threshold_percent = Column(Float, nullable=False, comment="기준 등락률 (예: 5.0)")
    actual_percent = Column(Float, nullable=False, comment="실제 변동률 (예: -5.8)")

    base_time = Column(DateTime, nullable=False, comment="기준 시각 (예: 기준 종가나 최고가 시점)")
    triggered_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="알림 발생 시각")

    def __repr__(self):
        return (
            f"<PriceAlertLog(symbol={self.symbol}, alert_type={self.alert_type}, "
            f"base_type={self.base_type}, actual_percent={self.actual_percent})>"
        )
