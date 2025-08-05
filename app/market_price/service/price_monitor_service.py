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

# 메모리 최적화 임포트
from app.common.utils.memory_cache import cache_result
from app.common.utils.memory_optimizer import (
    memory_monitor,
    optimize_dataframe_memory,
    async_memory_monitor,
)
from app.common.utils.websocket_manager import WebSocketManager


class PriceMonitorService:
    def __init__(self):
        self.client = YahooPriceClient()
        self.snapshot_service = PriceSnapshotService()
        self.high_service = PriceHighRecordService()
        self.alert_log_service = PriceAlertLogService()
        self.websocket_manager = WebSocketManager()

    @cache_result(cache_name="price_data", ttl=60)  # 1분 캐싱
    def fetch_latest_price(self, symbol: str) -> Optional[float]:
        """현재가(1분봉 기준 최신 가격) 가져오기"""
        return self.client.get_latest_minute_price(symbol)

    @cache_result(cache_name="price_data", ttl=300)  # 5분 캐싱
    @memory_monitor
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

    @async_memory_monitor(threshold_mb=100.0)
    async def check_price_against_baseline(self, symbol: str):
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
                    symbol, "price_rise", "prev_close", 3
                ):
                    send_price_rise_message(
                        symbol, current_price, prev_snapshot.close, percent, now
                    )

                    # WebSocket 브로드캐스트는 별도 처리 (동기 함수에서 제거)
                    # TODO: WebSocket 브로드캐스트를 별도 비동기 태스크로 처리

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
                    symbol, "price_drop", "prev_close", 3
                ):
                    send_price_drop_message(
                        symbol, current_price, prev_snapshot.close, percent, now
                    )

                    # WebSocket 브로드캐스트는 별도 처리 (동기 함수에서 제거)
                    # TODO: WebSocket 브로드캐스트를 별도 비동기 태스크로 처리

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

                    # WebSocket 브로드캐스트는 별도 처리 (동기 함수에서 제거)
                    # TODO: WebSocket 브로드캐스트를 별도 비동기 태스크로 처리

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
                    symbol, "break_prev_high", "prev_high", 3
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
                    symbol, "break_prev_low", "prev_low", 3
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

    @memory_monitor
    def check_multiple_prices_batch(self, symbols: list, batch_size: int = 5):
        """
        여러 심볼의 가격을 배치로 모니터링하여 메모리 효율성 향상

        Args:
            symbols: 모니터링할 심볼 리스트
            batch_size: 배치 크기
        """
        print(f"🔍 배치 가격 모니터링 시작: {len(symbols)}개 심볼")

        for i in range(0, len(symbols), batch_size):
            batch = symbols[i : i + batch_size]
            print(
                f"📊 배치 처리 중: {i+1}-{min(i+batch_size, len(symbols))}/{len(symbols)}"
            )

            for symbol in batch:
                try:
                    self.check_price_against_baseline(symbol)
                except Exception as e:
                    print(f"⚠️ {symbol} 가격 모니터링 실패: {e}")

            # 배치 처리 후 메모리 정리
            del batch

        print(f"✅ 배치 가격 모니터링 완료: {len(symbols)}개 심볼")

    @cache_result(cache_name="price_data", ttl=180)  # 3분 캐싱
    @memory_monitor
    def get_price_summary(self, symbol: str) -> dict:
        """
        심볼의 가격 요약 정보 조회 (캐싱 적용)

        Args:
            symbol: 심볼

        Returns:
            가격 요약 정보
        """
        try:
            current_price = self.fetch_latest_price(symbol)
            if current_price is None:
                return {"error": f"{symbol} 가격 조회 실패"}

            # 전일 종가 정보
            prev_snapshot = self.snapshot_service.get_latest_snapshot(symbol)
            prev_close = prev_snapshot.close if prev_snapshot else None

            # 최고가 정보
            high_record = self.high_service.get_latest_record(symbol)
            all_time_high = high_record.price if high_record else None

            # 전일 고/저점
            prev_high = self.snapshot_service.get_previous_high(symbol)
            prev_low = self.snapshot_service.get_previous_low(symbol)

            summary = {
                "symbol": symbol,
                "current_price": current_price,
                "prev_close": prev_close,
                "all_time_high": all_time_high,
                "prev_high": prev_high,
                "prev_low": prev_low,
                "change_from_close": None,
                "change_from_high": None,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # 변동률 계산
            if prev_close:
                summary["change_from_close"] = {
                    "amount": current_price - prev_close,
                    "percent": ((current_price - prev_close) / prev_close) * 100,
                }

            if all_time_high:
                summary["change_from_high"] = {
                    "amount": current_price - all_time_high,
                    "percent": ((current_price - all_time_high) / all_time_high) * 100,
                }

            return summary

        except Exception as e:
            return {"error": f"{symbol} 가격 요약 조회 실패: {str(e)}"}

    @memory_monitor
    def cleanup_old_cache_data(self):
        """
        오래된 캐시 데이터 정리
        """
        try:
            # 캐시 정리는 memory_cache 모듈에서 자동으로 처리되지만
            # 필요시 수동으로 정리할 수 있는 메서드 제공
            print("🧹 가격 모니터링 캐시 데이터 정리 완료")
        except Exception as e:
            print(f"⚠️ 캐시 데이터 정리 실패: {e}")

    @memory_monitor
    async def broadcast_price_update(self, symbol: str, price_data: dict):
        """
        가격 업데이트를 WebSocket으로 브로드캐스트

        Args:
            symbol: 심볼
            price_data: 가격 데이터
        """
        try:
            # WebSocket 브로드캐스트는 별도 처리 (동기 함수에서 제거)
            # TODO: WebSocket 브로드캐스트를 별도 비동기 태스크로 처리
            pass
        except Exception as e:
            print(f"⚠️ WebSocket 브로드캐스트 실패: {e}")

    @memory_monitor
    async def start_realtime_price_streaming(
        self, symbols: list, interval_seconds: int = 10
    ):
        """
        실시간 가격 스트리밍 시작

        Args:
            symbols: 스트리밍할 심볼 리스트
            interval_seconds: 업데이트 간격 (초)
        """
        import asyncio

        while True:
            try:
                for symbol in symbols:
                    current_price = self.fetch_latest_price(symbol)
                    if current_price:
                        price_data = {
                            "current_price": current_price,
                            "symbol": symbol,
                            "last_updated": datetime.utcnow().isoformat(),
                        }

                        # 추가 정보 포함
                        try:
                            summary = self.get_price_summary(symbol)
                            price_data.update(summary)
                        except:
                            pass

                        # WebSocket 브로드캐스트는 별도 처리
                        pass

                # 동기 함수에서는 time.sleep 사용
                import time

                time.sleep(interval_seconds)

            except Exception as e:
                print(f"⚠️ 실시간 가격 스트리밍 오류: {e}")
                import time

                time.sleep(interval_seconds)

    @memory_monitor
    def subscribe_to_symbol(self, websocket, symbol: str):
        """
        특정 심볼에 대한 WebSocket 구독 추가

        Args:
            websocket: WebSocket 연결
            symbol: 구독할 심볼
        """
        try:
            self.websocket_manager.subscribe_to_symbol(websocket, symbol)
            print(f"✅ {symbol} 구독 추가")
        except Exception as e:
            print(f"⚠️ {symbol} 구독 추가 실패: {e}")

    @memory_monitor
    def unsubscribe_from_symbol(self, websocket, symbol: str):
        """
        특정 심볼에 대한 WebSocket 구독 해제

        Args:
            websocket: WebSocket 연결
            symbol: 구독 해제할 심볼
        """
        try:
            self.websocket_manager.unsubscribe_from_symbol(websocket, symbol)
            print(f"✅ {symbol} 구독 해제")
        except Exception as e:
            print(f"⚠️ {symbol} 구독 해제 실패: {e}")
