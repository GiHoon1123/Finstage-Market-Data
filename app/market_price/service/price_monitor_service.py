from datetime import datetime
from typing import Optional
from app.market_price.infra.client.yahoo_price_client import YahooPriceClient
from app.market_price.service.price_snapshot_service import PriceSnapshotService
from app.market_price.service.price_high_record_service import PriceHighRecordService
from app.common.utils.telegram_notifier import (
    send_price_rise_message,
    send_price_drop_message,
    send_new_high_message,
    send_drop_from_high_message,
)

class PriceMonitorService:
    def __init__(self):
        self.client = YahooPriceClient()
        self.snapshot_service = PriceSnapshotService()
        self.high_service = PriceHighRecordService()

    def fetch_latest_price(self, symbol: str) -> Optional[float]:
        return self.client.get_latest_minute_price(symbol)

    def check_price_against_baseline(self, symbol: str):
        current_price = self.fetch_latest_price(symbol)
        if current_price is None:
            print(f"⚠️ {symbol} 현재 가격 가져오기 실패")
            return

        now = datetime.now()

        # 전일 종가 기준 비교
        prev_snapshot = self.snapshot_service.get_latest_snapshot(symbol)
        if prev_snapshot:
            diff = current_price - prev_snapshot.close
            percent = (diff / prev_snapshot.close) * 100
            print(f"📊 {symbol} 전일 종가 기준: 현재가 {current_price:.2f}, 변동률 {percent:.2f}%")

            if percent >= 3.0:
                send_price_rise_message(symbol, current_price, prev_snapshot.close, percent, now)
            elif percent <= -3.0:
                send_price_drop_message(symbol, current_price, prev_snapshot.close, percent, now)

        # 최고가 기준 비교
        high_record = self.high_service.get_latest_record(symbol)
        if high_record:
            diff = current_price - high_record.price
            percent = (diff / high_record.price) * 100
            print(f"🚨 {symbol} 최고가 기준: 현재가 {current_price:.2f}, 변동률 {percent:.2f}%")

            if current_price > high_record.price:
                send_new_high_message(symbol, current_price, now)
            elif percent <= -5.0:
                send_drop_from_high_message(symbol, current_price, high_record.price, percent, now)
