from sqlalchemy import Column, BigInteger, String, Float, DateTime
from datetime import datetime
from app.common.infra.database.config.database_config import Base


class PriceAlertLog(Base):
    __tablename__ = "price_alert_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="PK")

    symbol = Column(String(20), nullable=False, index=True, comment="종목 코드 (예: AAPL, ^GSPC 등)")

    alert_type = Column(String(30), nullable=False, comment="""
    알림 종류
    - price_rise: 전일 종가 기준 급등 (기준 등락률 이상 상승)
    - price_drop: 전일 종가 기준 급락 (기준 등락률 이하 하락)
    - new_high: 상장 후 최고가 갱신
    - drop_from_high: 상장 후 최고가 대비 급락 (기준 등락률 이하 하락)
    """)

    base_type = Column(String(30), nullable=False, comment="""
    기준 가격 종류
    - prev_close: 전일 종가 기준
    - all_time_high: 상장 후 최고가 기준
    """)

    base_price = Column(Float, nullable=False, comment="비교 기준 가격 (전일 종가 또는 최고가)")
    current_price = Column(Float, nullable=False, comment="현재 시세")

    threshold_percent = Column(Float, nullable=False, comment="알림 기준 등락률 (예: 5.0)")
    actual_percent = Column(Float, nullable=False, comment="실제 변동률 (예: -5.8)")

    base_time = Column(DateTime, nullable=False, comment="기준 가격의 발생 시각 (예: 종가 또는 최고가 시점)")
    triggered_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="알림 발생 시각")

    def __repr__(self):
        return (
            f"<PriceAlertLog(symbol={self.symbol}, alert_type={self.alert_type}, "
            f"base_type={self.base_type}, actual_percent={self.actual_percent})>"
        )
