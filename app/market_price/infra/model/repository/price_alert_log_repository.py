from sqlalchemy.orm import Session
from app.market_price.infra.model.entity.price_alert_log import PriceAlertLog


class PriceAlertLogRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, alert_log: PriceAlertLog):
        self.session.add(alert_log)

    def get_latest_by_symbol_and_type(self, symbol: str, alert_type: str, base_type: str) -> PriceAlertLog | None:
        return (
            self.session.query(PriceAlertLog)
            .filter_by(symbol=symbol, alert_type=alert_type, base_type=base_type)
            .order_by(PriceAlertLog.triggered_at.desc())
            .first()
        )

    def exists_recent_alert(self, symbol: str, alert_type: str, base_type: str, min_minutes_gap: int = 60) -> bool:
        """
        일정 시간 내에 같은 종류의 알림이 이미 발송됐는지 확인 (중복 방지용)
        """
        from datetime import datetime, timedelta

        threshold_time = datetime.utcnow() - timedelta(minutes=min_minutes_gap)

        return (
            self.session.query(PriceAlertLog)
            .filter(
                PriceAlertLog.symbol == symbol,
                PriceAlertLog.alert_type == alert_type,
                PriceAlertLog.base_type == base_type,
                PriceAlertLog.triggered_at >= threshold_time,
            )
            .first()
            is not None
        )
