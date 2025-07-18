from datetime import datetime
from typing import Optional
from app.common.infra.client.yahoo_price_client import YahooPriceClient
from app.market_price.service.price_snapshot_service import PriceSnapshotService
from app.market_price.service.price_high_record_service import PriceHighRecordService
from app.market_price.service.price_alert_log_service import PriceAlertLogService
from app.common.constants.thresholds import CATEGORY_THRESHOLDS, SYMBOL_THRESHOLDS
from app.common.constants.symbol_names import SYMBOL_MONITORING_CATEGORY_MAP
from app.common.utils.telegram_notifier import (
    send_price_rise_message,
    send_price_drop_message,
    send_new_high_message,
    send_drop_from_high_message,
    send_break_previous_high,
    send_break_previous_low,
)


class PriceMonitorService:
    def __init__(self):
        self.client = YahooPriceClient()
        self.snapshot_service = PriceSnapshotService()
        self.high_service = PriceHighRecordService()
        self.alert_log_service = PriceAlertLogService()

    def fetch_latest_price(self, symbol: str) -> Optional[float]:
        """현재가(1분봉 기준 최신 가격) 가져오기"""
        return self.client.get_latest_minute_price(symbol)

    def _get_threshold(self, symbol: str, alert_type: str) -> Optional[float]:
        """
        심볼별 또는 카테고리별 임계치 반환
        예: "price_rise", "price_drop", "drop_from_high"
        """
        if symbol in SYMBOL_THRESHOLDS and alert_type in SYMBOL_THRESHOLDS[symbol]:
            return SYMBOL_THRESHOLDS[symbol][alert_type]

        category = SYMBOL_MONITORING_CATEGORY_MAP.get(symbol)
        if category and alert_type in CATEGORY_THRESHOLDS.get(category, {}):
            return CATEGORY_THRESHOLDS[category][alert_type]

        return None

    def check_price_against_baseline(self, symbol: str):
        """전일 종가, 상장 후 최고가, 전일 고/저점 기준으로 가격을 모니터링하고 알림 전송"""
        current_price = self.fetch_latest_price(symbol)
        if current_price is None:
            print(f"⚠️ {symbol} 현재 가격 가져오기 실패")
            return

        now = datetime.utcnow()

        ### 1. 전일 종가 기준 ###
        prev_snapshot = self.snapshot_service.get_latest_snapshot(symbol)
        if prev_snapshot and prev_snapshot.close is not None:
            diff = current_price - prev_snapshot.close
            percent = (diff / prev_snapshot.close) * 100
            print(
                f"📊 {symbol} 전일 종가 기준: 현재가 {current_price:.2f}, 기준가 {prev_snapshot.close:.2f}, 변동률 {percent:.2f}%"
            )

            # 상승 알림
            rise_threshold = self._get_threshold(symbol, "price_rise")
            if rise_threshold is not None and percent >= rise_threshold:
                if not self.alert_log_service.exists_recent_alert(
                    symbol, "price_rise", "prev_close", 1440
                ):
                    send_price_rise_message(
                        symbol, current_price, prev_snapshot.close, percent, now
                    )
                    self.alert_log_service.save_alert(
                        symbol=symbol,
                        alert_type="price_rise",
                        base_type="prev_close",
                        base_price=prev_snapshot.close,
                        current_price=current_price,
                        threshold_percent=rise_threshold,
                        actual_percent=percent,
                        base_time=prev_snapshot.snapshot_at,
                        triggered_at=now,
                    )

            # 하락 알림
            drop_threshold = self._get_threshold(symbol, "price_drop")
            if drop_threshold is not None and percent <= drop_threshold:
                if not self.alert_log_service.exists_recent_alert(
                    symbol, "price_drop", "prev_close", 1440
                ):
                    send_price_drop_message(
                        symbol, current_price, prev_snapshot.close, percent, now
                    )
                    self.alert_log_service.save_alert(
                        symbol=symbol,
                        alert_type="price_drop",
                        base_type="prev_close",
                        base_price=prev_snapshot.close,
                        current_price=current_price,
                        threshold_percent=abs(drop_threshold),
                        actual_percent=percent,
                        base_time=prev_snapshot.snapshot_at,
                        triggered_at=now,
                    )

        ### 2. 상장 후 최고가 기준 ###
        high_record = self.high_service.get_latest_record(symbol)
        if high_record:
            diff = current_price - high_record.price
            percent = (diff / high_record.price) * 100
            print(
                f"🚨 {symbol} 최고가 기준: 현재가 {current_price:.2f}, 기준가 {high_record.price:.2f}, 변동률 {percent:.2f}%"
            )

            # 최고가 갱신
            if current_price > high_record.price:
                if not self.alert_log_service.exists_recent_alert(
                    symbol, "new_high", "all_time_high", 360
                ):
                    send_new_high_message(symbol, current_price, now)
                    self.alert_log_service.save_alert(
                        symbol=symbol,
                        alert_type="new_high",
                        base_type="all_time_high",
                        base_price=high_record.price,
                        current_price=current_price,
                        threshold_percent=0.0,
                        actual_percent=percent,
                        base_time=high_record.recorded_at,
                        triggered_at=now,
                    )

            # 최고가 대비 하락
            drop_from_high_threshold = self._get_threshold(symbol, "drop_from_high")
            if (
                drop_from_high_threshold is not None
                and percent <= drop_from_high_threshold
            ):
                if not self.alert_log_service.exists_recent_alert(
                    symbol, "drop_from_high", "all_time_high", 360
                ):
                    send_drop_from_high_message(
                        symbol,
                        current_price,
                        high_record.price,
                        percent,
                        now,
                        high_record.recorded_at,
                    )
                    self.alert_log_service.save_alert(
                        symbol=symbol,
                        alert_type="drop_from_high",
                        base_type="all_time_high",
                        base_price=high_record.price,
                        current_price=current_price,
                        threshold_percent=abs(drop_from_high_threshold),
                        actual_percent=percent,
                        base_time=high_record.recorded_at,
                        triggered_at=now,
                    )

        ### 3. 전일 고점 / 저점 기준 ###
        prev_high = self.snapshot_service.get_previous_high(symbol)
        prev_low = self.snapshot_service.get_previous_low(symbol)

        if prev_high:
            diff = current_price - prev_high
            percent = (diff / prev_high) * 100
            print(
                f"📈 {symbol} 전일 고점 기준: 현재가 {current_price:.2f}, 기준가 {prev_high:.2f}, 변동률 {percent:.2f}%"
            )
            if current_price > prev_high:
                if not self.alert_log_service.exists_recent_alert(
                    symbol, "break_prev_high", "prev_high", 1440
                ):
                    send_break_previous_high(symbol, current_price, prev_high, now)
                    self.alert_log_service.save_alert(
                        symbol=symbol,
                        alert_type="break_prev_high",
                        base_type="prev_high",
                        base_price=prev_high,
                        current_price=current_price,
                        threshold_percent=0.0,
                        actual_percent=((current_price - prev_high) / prev_high) * 100,
                        base_time=now.replace(
                            hour=0, minute=0, second=0, microsecond=0
                        ),
                        triggered_at=now,
                    )

        if prev_low:
            diff = current_price - prev_low
            percent = (diff / prev_low) * 100
            print(
                f"📉 {symbol} 전일 저점 기준: 현재가 {current_price:.2f}, 기준가 {prev_low:.2f}, 변동률 {percent:.2f}%"
            )
            if current_price < prev_low:
                if not self.alert_log_service.exists_recent_alert(
                    symbol, "break_prev_low", "prev_low", 1440
                ):
                    send_break_previous_low(symbol, current_price, prev_low, now)
                    self.alert_log_service.save_alert(
                        symbol=symbol,
                        alert_type="break_prev_low",
                        base_type="prev_low",
                        base_price=prev_low,
                        current_price=current_price,
                        threshold_percent=0.0,
                        actual_percent=((current_price - prev_low) / prev_low) * 100,
                        base_time=now.replace(
                            hour=0, minute=0, second=0, microsecond=0
                        ),
                        triggered_at=now,
                    )
