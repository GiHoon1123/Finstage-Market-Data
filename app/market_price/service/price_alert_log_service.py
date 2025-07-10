from datetime import datetime
from app.market_price.infra.model.repository.price_alert_log_repository import PriceAlertLogRepository
from app.market_price.infra.model.entity.price_alert_log import PriceAlertLog
from app.common.infra.database.config.database_config import SessionLocal


class PriceAlertLogService:
    def __init__(self):
        # DB 세션 생성 및 레포지토리 주입
        self.session = SessionLocal()
        self.repository = PriceAlertLogRepository(self.session)

    def exists_recent_alert(self, symbol: str, alert_type: str, base_type: str, minutes: int = 60) -> bool:
        """
        최근 `minutes`분 내에 동일한 종류의 알림이 이미 존재하는지 확인

        :param symbol: 종목/지수 심볼
        :param alert_type: 알림 유형 (e.g. 'price_rise', 'drop_from_high')
        :param base_type: 기준 유형 ('prev_close' 또는 'all_time_high')
        :param minutes: 중복 알림 제한 시간(분)
        :return: 중복 알림 존재 여부
        """
        return self.repository.exists_recent_alert(
            symbol=symbol,
            alert_type=alert_type,
            base_type=base_type,
            min_minutes_gap=minutes
        )

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
