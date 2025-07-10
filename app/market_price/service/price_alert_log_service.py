from datetime import datetime, timedelta
from app.market_price.infra.model.repository.price_alert_log_repository import PriceAlertLogRepository
from app.market_price.infra.model.entity.price_alert_log import PriceAlertLog
from app.common.infra.database.config.database_config import SessionLocal


class PriceAlertLogService:
    def __init__(self):
        # DB 세션 생성 및 레포지토리 주입
        self.session = SessionLocal()
        self.repository = PriceAlertLogRepository(self.session)

    def exists_recent_alert(self, symbol: str, alert_type: str, base_type: str, min_minutes_gap: int = 60) -> bool:
        """
        일정 시간 내에 같은 종류의 알림이 이미 발송됐는지 확인 (중복 방지용)
        """
        threshold_time = datetime.utcnow() - timedelta(minutes=min_minutes_gap)

        alert = (
            self.session.query(PriceAlertLog)
            .filter(
                PriceAlertLog.symbol == symbol,
                PriceAlertLog.alert_type == alert_type,
                PriceAlertLog.base_type == base_type,
                PriceAlertLog.triggered_at >= threshold_time,
            )
            .order_by(PriceAlertLog.triggered_at.desc())
            .first()
        )

        if alert:
            time_diff = datetime.utcnow() - alert.triggered_at
            remaining = timedelta(minutes=min_minutes_gap) - time_diff
            print(f"⚠️ 최근 알림 있음 → {alert.triggered_at} (남은 차단 시간: {remaining})")
            return True
        else:
            print(f"✅ 최근 알림 없음 (기준 시각: {threshold_time})")
            return False

    def save_alert(
        self,
        symbol: str,
        alert_type: str,
        base_type: str,
        base_price: float,
        current_price: float,
        threshold_percent: float,
        actual_percent: float,
        base_time: datetime,
        triggered_at: datetime
    ):
        """
        새로운 알림 로그 저장

        :param symbol: 종목/지수 심볼
        :param alert_type: 알림 유형 (e.g. 'price_rise', 'drop_from_high')
        :param base_type: 기준 유형 ('prev_close' 또는 'all_time_high')
        :param base_price: 기준 가격
        :param current_price: 현재 가격
        :param threshold_percent: 기준 변화 임계값 (예: 2%)
        :param actual_percent: 실제 변화율
        :param base_time: 기준 가격의 기록 시점
        :param triggered_at: 알림 발생 시각
        """
        try:
            # 엔티티 생성
            alert_log = PriceAlertLog(
                symbol=symbol,
                alert_type=alert_type,
                base_type=base_type,
                base_price=base_price,
                current_price=current_price,
                threshold_percent=threshold_percent,
                actual_percent=actual_percent,
                base_time=base_time,
                triggered_at=triggered_at
            )

            # 저장 및 커밋
            self.repository.save(alert_log)
            self.session.commit()
            print(f"📌 {symbol} 알림 로그 저장 완료: {alert_type} 기준 {base_type}")

        except Exception as e:
            # 예외 발생 시 롤백
            self.session.rollback()
            print(f"❌ {symbol} 알림 로그 저장 실패: {e}")

        finally:
            # 세션 종료
            self.session.close()
