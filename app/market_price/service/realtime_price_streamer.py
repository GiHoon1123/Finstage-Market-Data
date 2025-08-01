"""
실시간 가격 스트리밍 서비스

WebSocket을 통해 실시간 가격 데이터를 클라이언트에게 스트리밍합니다.
가격 변동 감지, 알림 생성, 브로드캐스팅을 담당합니다.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass

from app.common.utils.websocket_manager import (
    websocket_manager,
    MessageType,
    SubscriptionType,
)
from app.market_price.service.async_price_service import AsyncPriceService
from app.common.utils.async_executor import AsyncExecutor, async_timed
from app.common.utils.memory_optimizer import memory_monitor
from app.common.utils.logging_config import get_logger
from app.common.constants.symbol_names import SYMBOL_PRICE_MAP
from app.common.constants.thresholds import CATEGORY_THRESHOLDS, SYMBOL_THRESHOLDS

logger = get_logger(__name__)


@dataclass
class PriceUpdate:
    """가격 업데이트 데이터"""

    symbol: str
    current_price: float
    previous_price: Optional[float]
    change_amount: Optional[float]
    change_percent: Optional[float]
    volume: Optional[int]
    timestamp: datetime
    market_status: str = "open"


@dataclass
class PriceAlert:
    """가격 알림 데이터"""

    symbol: str
    alert_type: str
    message: str
    current_price: float
    threshold_value: Optional[float]
    severity: str
    timestamp: datetime


class RealtimePriceStreamer:
    """실시간 가격 스트리밍 서비스"""

    def __init__(self, update_interval: int = 10):
        self.update_interval = update_interval  # 초
        self.price_service = AsyncPriceService(max_workers=3, max_concurrency=8)
        self.async_executor = AsyncExecutor(max_concurrency=15)

        # 가격 데이터 저장
        self.current_prices: Dict[str, float] = {}
        self.previous_prices: Dict[str, float] = {}
        self.price_history: Dict[str, List[PriceUpdate]] = {}

        # 스트리밍 상태
        self.is_streaming = False
        self.streaming_task: Optional[asyncio.Task] = None
        self.monitored_symbols: Set[str] = set()

        # 통계
        self.total_updates_sent = 0
        self.total_alerts_sent = 0
        self.last_update_time: Optional[datetime] = None

    async def start_streaming(self, symbols: List[str] = None):
        """실시간 스트리밍 시작"""
        if self.is_streaming:
            logger.warning("realtime_streaming_already_active")
            return

        # 모니터링할 심볼 설정
        if symbols:
            self.monitored_symbols = set(symbols)
        else:
            self.monitored_symbols = set(SYMBOL_PRICE_MAP.keys())

        self.is_streaming = True
        self.streaming_task = asyncio.create_task(self._streaming_loop())

        logger.info(
            "realtime_streaming_started",
            symbol_count=len(self.monitored_symbols),
            update_interval=self.update_interval,
        )

    async def stop_streaming(self):
        """실시간 스트리밍 중지"""
        if not self.is_streaming:
            return

        self.is_streaming = False

        if self.streaming_task:
            self.streaming_task.cancel()
            try:
                await self.streaming_task
            except asyncio.CancelledError:
                pass
            self.streaming_task = None

        # 리소스 정리
        await self.price_service._close_session()

        logger.info("realtime_streaming_stopped")

    async def add_symbol(self, symbol: str):
        """모니터링 심볼 추가"""
        self.monitored_symbols.add(symbol)
        logger.info("symbol_added_to_streaming", symbol=symbol)

    async def remove_symbol(self, symbol: str):
        """모니터링 심볼 제거"""
        self.monitored_symbols.discard(symbol)

        # 관련 데이터 정리
        self.current_prices.pop(symbol, None)
        self.previous_prices.pop(symbol, None)
        self.price_history.pop(symbol, None)

        logger.info("symbol_removed_from_streaming", symbol=symbol)

    @async_timed()
    @memory_monitor(threshold_mb=200.0)
    async def _streaming_loop(self):
        """스트리밍 메인 루프"""
        logger.info("streaming_loop_started")

        while self.is_streaming:
            try:
                start_time = time.time()

                # 현재 가격들을 배치로 조회
                try:
                    async with self.price_service:
                        current_prices = (
                            await self.price_service.fetch_multiple_prices_async(
                                list(self.monitored_symbols), batch_size=5
                            )
                        )
                except Exception as e:
                    logger.error("price_fetch_failed_in_streaming", error=str(e))
                    current_prices = {}  # 빈 딕셔너리로 계속 진행

                # 가격 업데이트 처리 (빈 딕셔너리 처리)
                if current_prices:
                    updates = await self._process_price_updates(current_prices)
                    # 알림 생성
                    alerts = await self._generate_alerts(updates)
                else:
                    updates = []
                    alerts = []
                    logger.debug("no_price_data_received_skipping_updates")

                # WebSocket으로 브로드캐스트
                try:
                    await self._broadcast_updates(updates)
                    await self._broadcast_alerts(alerts)
                except Exception as e:
                    logger.error("broadcast_failed_in_streaming", error=str(e))

                # 통계 업데이트
                self.total_updates_sent += len(updates)
                self.total_alerts_sent += len(alerts)
                self.last_update_time = datetime.now()

                # 실행 시간 로깅
                execution_time = time.time() - start_time
                logger.debug(
                    "streaming_cycle_completed",
                    symbols_processed=len(current_prices),
                    updates_sent=len(updates),
                    alerts_sent=len(alerts),
                    execution_time=execution_time,
                )

                # 다음 업데이트까지 대기
                sleep_time = max(0, self.update_interval - execution_time)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("streaming_loop_error", error=str(e))
                await asyncio.sleep(5)  # 에러 시 5초 대기

        logger.info("streaming_loop_ended")

    async def _process_price_updates(
        self, current_prices: Dict[str, Optional[float]]
    ) -> List[PriceUpdate]:
        """가격 업데이트 처리"""
        updates = []

        for symbol, current_price in current_prices.items():
            if current_price is None:
                continue

            # 이전 가격과 비교
            previous_price = self.current_prices.get(symbol)

            # 가격 변동이 있는 경우만 업데이트
            if previous_price is None or abs(current_price - previous_price) > 0.001:

                # 변동량 계산
                change_amount = None
                change_percent = None

                if previous_price is not None:
                    change_amount = current_price - previous_price
                    change_percent = (change_amount / previous_price) * 100

                # 업데이트 객체 생성
                update = PriceUpdate(
                    symbol=symbol,
                    current_price=current_price,
                    previous_price=previous_price,
                    change_amount=change_amount,
                    change_percent=change_percent,
                    volume=None,  # 볼륨 정보는 별도 API에서
                    timestamp=datetime.now(),
                    market_status=self._get_market_status(),
                )

                updates.append(update)

                # 가격 히스토리 업데이트
                self._update_price_history(symbol, update)

        # 현재 가격 저장
        for symbol, price in current_prices.items():
            if price is not None:
                self.previous_prices[symbol] = self.current_prices.get(symbol, price)
                self.current_prices[symbol] = price

        return updates

    async def _generate_alerts(self, updates: List[PriceUpdate]) -> List[PriceAlert]:
        """가격 알림 생성"""
        alerts = []

        for update in updates:
            symbol = update.symbol
            current_price = update.current_price
            change_percent = update.change_percent

            if change_percent is None:
                continue

            # 임계값 조회
            thresholds = self._get_symbol_thresholds(symbol)

            # 상승 알림
            rise_threshold = thresholds.get("price_rise")
            if rise_threshold and change_percent >= rise_threshold:
                alert = PriceAlert(
                    symbol=symbol,
                    alert_type="price_rise",
                    message=f"{symbol} {change_percent:.1f}% 상승 (${current_price:.2f})",
                    current_price=current_price,
                    threshold_value=rise_threshold,
                    severity="info",
                    timestamp=update.timestamp,
                )
                alerts.append(alert)

            # 하락 알림
            drop_threshold = thresholds.get("price_drop")
            if drop_threshold and change_percent <= drop_threshold:
                alert = PriceAlert(
                    symbol=symbol,
                    alert_type="price_drop",
                    message=f"{symbol} {abs(change_percent):.1f}% 하락 (${current_price:.2f})",
                    current_price=current_price,
                    threshold_value=abs(drop_threshold),
                    severity="warning",
                    timestamp=update.timestamp,
                )
                alerts.append(alert)

            # 급등/급락 알림 (5% 이상)
            if abs(change_percent) >= 5.0:
                alert_type = "surge" if change_percent > 0 else "plunge"
                severity = "high" if abs(change_percent) >= 10.0 else "medium"

                alert = PriceAlert(
                    symbol=symbol,
                    alert_type=alert_type,
                    message=f"{symbol} 급{'등' if change_percent > 0 else '락'} {abs(change_percent):.1f}%",
                    current_price=current_price,
                    threshold_value=5.0,
                    severity=severity,
                    timestamp=update.timestamp,
                )
                alerts.append(alert)

        return alerts

    async def _broadcast_updates(self, updates: List[PriceUpdate]):
        """가격 업데이트 브로드캐스트"""
        for update in updates:
            message = {
                "symbol": update.symbol,
                "current_price": update.current_price,
                "previous_price": update.previous_price,
                "change_amount": update.change_amount,
                "change_percent": update.change_percent,
                "volume": update.volume,
                "market_status": update.market_status,
                "timestamp": update.timestamp.isoformat(),
            }

            await websocket_manager.broadcast_to_symbol_subscribers(
                update.symbol, message, MessageType.PRICE_UPDATE
            )

    async def _broadcast_alerts(self, alerts: List[PriceAlert]):
        """알림 브로드캐스트"""
        for alert in alerts:
            message = {
                "symbol": alert.symbol,
                "alert_type": alert.alert_type,
                "message": alert.message,
                "current_price": alert.current_price,
                "threshold_value": alert.threshold_value,
                "severity": alert.severity,
                "timestamp": alert.timestamp.isoformat(),
            }

            # 알림은 모든 구독자에게 전송
            await websocket_manager.broadcast_to_type_subscribers(
                SubscriptionType.ALERTS, message, MessageType.ALERT
            )

    def _update_price_history(self, symbol: str, update: PriceUpdate):
        """가격 히스토리 업데이트"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []

        self.price_history[symbol].append(update)

        # 최근 100개 기록만 유지
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol] = self.price_history[symbol][-100:]

    def _get_symbol_thresholds(self, symbol: str) -> Dict[str, float]:
        """심볼별 임계값 조회"""
        # 심볼별 임계값 우선
        if symbol in SYMBOL_THRESHOLDS:
            return SYMBOL_THRESHOLDS[symbol]

        # 카테고리별 임계값
        from app.common.constants.symbol_names import SYMBOL_MONITORING_CATEGORY_MAP

        category = SYMBOL_MONITORING_CATEGORY_MAP.get(symbol)
        if category and category in CATEGORY_THRESHOLDS:
            return CATEGORY_THRESHOLDS[category]

        # 기본값
        return {"price_rise": 3.0, "price_drop": -3.0}

    def _get_market_status(self) -> str:
        """시장 상태 확인"""
        # 간단한 시장 시간 확인 (실제로는 더 정교한 로직 필요)
        now = datetime.now()
        hour = now.hour

        # 미국 시장 기준 (EST)
        if 9 <= hour <= 16:
            return "open"
        elif 4 <= hour <= 9:
            return "pre_market"
        elif 16 <= hour <= 20:
            return "after_market"
        else:
            return "closed"

    def get_current_prices(self) -> Dict[str, float]:
        """현재 가격 조회"""
        return self.current_prices.copy()

    def get_price_history(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """가격 히스토리 조회"""
        if symbol not in self.price_history:
            return []

        history = self.price_history[symbol][-limit:]

        return [
            {
                "symbol": update.symbol,
                "price": update.current_price,
                "change_amount": update.change_amount,
                "change_percent": update.change_percent,
                "timestamp": update.timestamp.isoformat(),
            }
            for update in history
        ]

    def get_stats(self) -> Dict[str, Any]:
        """스트리밍 통계"""
        return {
            "timestamp": datetime.now().isoformat(),
            "is_streaming": self.is_streaming,
            "monitored_symbols": len(self.monitored_symbols),
            "symbols_with_prices": len(self.current_prices),
            "total_updates_sent": self.total_updates_sent,
            "total_alerts_sent": self.total_alerts_sent,
            "last_update_time": (
                self.last_update_time.isoformat() if self.last_update_time else None
            ),
            "update_interval_seconds": self.update_interval,
            "price_history_size": sum(
                len(history) for history in self.price_history.values()
            ),
        }


# 전역 실시간 가격 스트리머
realtime_price_streamer = RealtimePriceStreamer(update_interval=10)
