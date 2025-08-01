"""
비동기 가격 데이터 서비스

가격 조회, 모니터링, 알림 등을 비동기로 처리하여
여러 심볼의 가격을 동시에 효율적으로 처리합니다.
"""

import asyncio
import aiohttp
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor
import functools

from app.common.utils.async_executor import AsyncExecutor, async_timed
from app.common.utils.memory_cache import cache_result
from app.common.utils.memory_optimizer import memory_monitor
from app.common.utils.logging_config import get_logger
from app.common.constants.symbol_names import SYMBOL_PRICE_MAP
from app.common.constants.thresholds import CATEGORY_THRESHOLDS, SYMBOL_THRESHOLDS

logger = get_logger(__name__)


class AsyncPriceService:
    """비동기 가격 데이터 서비스"""

    def __init__(self, max_workers: int = 5, max_concurrency: int = 10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.async_executor = AsyncExecutor(max_concurrency=max_concurrency)
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit_delay = 0.2  # API 요청 간격

    async def _ensure_session(self):
        """HTTP 세션 확보"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.session = aiohttp.ClientSession(timeout=timeout)

    async def _close_session(self):
        """HTTP 세션 종료"""
        if self.session and not self.session.closed:
            await self.session.close()

    def _run_in_executor(self, func, *args, **kwargs):
        """CPU 집약적 작업을 별도 스레드에서 실행"""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(
            self.executor, functools.partial(func, *args, **kwargs)
        )

    # =========================================================================
    # 비동기 가격 조회
    # =========================================================================

    @async_timed()
    async def fetch_price_async(self, symbol: str) -> Optional[float]:
        """
        단일 심볼의 현재 가격을 비동기로 조회

        Args:
            symbol: 조회할 심볼

        Returns:
            현재 가격 또는 None
        """
        await self._ensure_session()

        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            params = {"interval": "1m", "range": "1d", "includePrePost": "true"}

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    if (
                        data.get("chart")
                        and data["chart"].get("result")
                        and len(data["chart"]["result"]) > 0
                    ):

                        result = data["chart"]["result"][0]
                        meta = result.get("meta", {})
                        price = meta.get("regularMarketPrice")

                        if price:
                            logger.debug("price_fetched", symbol=symbol, price=price)
                            return float(price)

                logger.warning(
                    "price_fetch_failed", symbol=symbol, status=response.status
                )
                return None

        except Exception as e:
            logger.error("price_fetch_error", symbol=symbol, error=str(e))
            return None

    @async_timed()
    async def fetch_multiple_prices_async(
        self, symbols: List[str], batch_size: int = 5
    ) -> Dict[str, Optional[float]]:
        """
        여러 심볼의 가격을 동시에 조회

        Args:
            symbols: 조회할 심볼 리스트
            batch_size: 배치 크기

        Returns:
            심볼별 가격 딕셔너리
        """
        logger.info(
            "batch_price_fetch_started",
            symbol_count=len(symbols),
            batch_size=batch_size,
        )

        # 가격 조회 작업들을 배치로 처리
        results = await self.async_executor.process_batch(
            items=symbols,
            processor=self.fetch_price_async,
            batch_size=batch_size,
            batch_delay=self.rate_limit_delay,
        )

        # 결과를 딕셔너리로 변환
        price_data = {}
        for i, price in enumerate(results):
            symbol = symbols[i]
            price_data[symbol] = price

        successful_count = sum(1 for p in price_data.values() if p is not None)
        logger.info(
            "batch_price_fetch_completed",
            successful_count=successful_count,
            total_count=len(symbols),
        )

        return price_data

    # =========================================================================
    # 비동기 가격 모니터링
    # =========================================================================

    @async_timed()
    @memory_monitor(threshold_mb=150.0)
    async def monitor_prices_async(
        self, symbols: List[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        여러 심볼의 가격을 모니터링하고 알림 조건 확인

        Args:
            symbols: 모니터링할 심볼 리스트 (기본값: 전체)

        Returns:
            심볼별 모니터링 결과
        """
        if symbols is None:
            symbols = list(SYMBOL_PRICE_MAP.keys())

        logger.info("price_monitoring_started", symbol_count=len(symbols))

        # 현재 가격들을 동시에 조회
        current_prices = await self.fetch_multiple_prices_async(symbols, batch_size=3)

        # 각 심볼별로 모니터링 로직 실행
        monitoring_tasks = [
            self._monitor_single_symbol_async(symbol, price)
            for symbol, price in current_prices.items()
            if price is not None
        ]

        monitoring_results = await self.async_executor.gather_with_concurrency(
            monitoring_tasks
        )

        # 결과 정리
        results = {}
        for result in monitoring_results:
            if result and "symbol" in result:
                results[result["symbol"]] = result

        logger.info(
            "price_monitoring_completed",
            monitored_count=len(results),
            alerts_generated=sum(1 for r in results.values() if r.get("alerts")),
        )

        return results

    async def _monitor_single_symbol_async(
        self, symbol: str, current_price: float
    ) -> Dict[str, Any]:
        """
        단일 심볼의 가격 모니터링

        Args:
            symbol: 심볼
            current_price: 현재 가격

        Returns:
            모니터링 결과
        """

        def _get_monitoring_data():
            # 기존 동기 로직을 스레드에서 실행
            # (데이터베이스 조회 등)
            from app.market_price.service.price_snapshot_service import (
                PriceSnapshotService,
            )
            from app.market_price.service.price_high_record_service import (
                PriceHighRecordService,
            )

            snapshot_service = PriceSnapshotService()
            high_service = PriceHighRecordService()

            # 전일 종가 조회
            prev_snapshot = snapshot_service.get_latest_snapshot(symbol)

            # 상장 후 최고가 조회
            high_record = high_service.get_latest_record(symbol)

            return {
                "prev_close": prev_snapshot.close if prev_snapshot else None,
                "all_time_high": high_record.price if high_record else None,
                "high_record_date": high_record.recorded_at if high_record else None,
            }

        try:
            # 기준 데이터 조회
            base_data = await self._run_in_executor(_get_monitoring_data)

            result = {
                "symbol": symbol,
                "current_price": current_price,
                "timestamp": datetime.utcnow(),
                "alerts": [],
                "analysis": {},
            }

            # 전일 종가 기준 분석
            if base_data["prev_close"]:
                prev_close = base_data["prev_close"]
                change_pct = ((current_price - prev_close) / prev_close) * 100

                result["analysis"]["prev_close"] = {
                    "base_price": prev_close,
                    "change_amount": current_price - prev_close,
                    "change_percent": change_pct,
                }

                # 알림 조건 확인
                alerts = await self._check_alert_conditions_async(
                    symbol, current_price, prev_close, change_pct, "prev_close"
                )
                result["alerts"].extend(alerts)

            # 최고가 기준 분석
            if base_data["all_time_high"]:
                all_time_high = base_data["all_time_high"]
                change_pct = ((current_price - all_time_high) / all_time_high) * 100

                result["analysis"]["all_time_high"] = {
                    "base_price": all_time_high,
                    "change_amount": current_price - all_time_high,
                    "change_percent": change_pct,
                    "record_date": base_data["high_record_date"],
                }

                # 최고가 갱신 또는 하락 알림
                if current_price > all_time_high:
                    result["alerts"].append(
                        {
                            "type": "new_high",
                            "message": f"{symbol} 신고가 달성: {current_price:.2f}",
                            "severity": "info",
                        }
                    )
                elif change_pct <= -10:  # 10% 이상 하락
                    result["alerts"].append(
                        {
                            "type": "drop_from_high",
                            "message": f"{symbol} 최고가 대비 {abs(change_pct):.1f}% 하락",
                            "severity": "warning",
                        }
                    )

            return result

        except Exception as e:
            logger.error("single_symbol_monitoring_failed", symbol=symbol, error=str(e))
            return {"symbol": symbol, "error": str(e), "timestamp": datetime.utcnow()}

    async def _check_alert_conditions_async(
        self,
        symbol: str,
        current_price: float,
        base_price: float,
        change_pct: float,
        base_type: str,
    ) -> List[Dict[str, Any]]:
        """
        알림 조건 확인

        Args:
            symbol: 심볼
            current_price: 현재 가격
            base_price: 기준 가격
            change_pct: 변화율
            base_type: 기준 타입

        Returns:
            알림 리스트
        """

        def _get_thresholds():
            # 심볼별 임계값 조회
            if symbol in SYMBOL_THRESHOLDS:
                return SYMBOL_THRESHOLDS[symbol]

            # 카테고리별 임계값 조회
            from app.common.constants.symbol_names import SYMBOL_MONITORING_CATEGORY_MAP

            category = SYMBOL_MONITORING_CATEGORY_MAP.get(symbol)
            if category and category in CATEGORY_THRESHOLDS:
                return CATEGORY_THRESHOLDS[category]

            return {}

        thresholds = await self._run_in_executor(_get_thresholds)
        alerts = []

        # 상승 알림
        rise_threshold = thresholds.get("price_rise")
        if rise_threshold and change_pct >= rise_threshold:
            alerts.append(
                {
                    "type": "price_rise",
                    "message": f"{symbol} {base_type} 대비 {change_pct:.1f}% 상승",
                    "severity": "info",
                    "threshold": rise_threshold,
                    "actual": change_pct,
                }
            )

        # 하락 알림
        drop_threshold = thresholds.get("price_drop")
        if drop_threshold and change_pct <= drop_threshold:
            alerts.append(
                {
                    "type": "price_drop",
                    "message": f"{symbol} {base_type} 대비 {abs(change_pct):.1f}% 하락",
                    "severity": "warning",
                    "threshold": abs(drop_threshold),
                    "actual": abs(change_pct),
                }
            )

        return alerts

    # =========================================================================
    # 비동기 가격 히스토리 조회
    # =========================================================================

    @async_timed()
    async def fetch_price_history_async(
        self, symbol: str, period: str = "1mo", interval: str = "1d"
    ) -> Optional[Dict[str, Any]]:
        """
        심볼의 가격 히스토리를 비동기로 조회

        Args:
            symbol: 심볼
            period: 조회 기간 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: 데이터 간격 (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            가격 히스토리 데이터
        """
        await self._ensure_session()

        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            params = {
                "period1": "0",
                "period2": str(int(time.time())),
                "interval": interval,
                "range": period,
                "includePrePost": "true",
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    if (
                        data.get("chart")
                        and data["chart"].get("result")
                        and len(data["chart"]["result"]) > 0
                    ):

                        result = data["chart"]["result"][0]

                        # 타임스탬프와 가격 데이터 추출
                        timestamps = result.get("timestamp", [])
                        indicators = result.get("indicators", {})
                        quote = (
                            indicators.get("quote", [{}])[0]
                            if indicators.get("quote")
                            else {}
                        )

                        history_data = {
                            "symbol": symbol,
                            "period": period,
                            "interval": interval,
                            "timestamps": timestamps,
                            "open": quote.get("open", []),
                            "high": quote.get("high", []),
                            "low": quote.get("low", []),
                            "close": quote.get("close", []),
                            "volume": quote.get("volume", []),
                            "data_points": len(timestamps),
                        }

                        logger.debug(
                            "price_history_fetched",
                            symbol=symbol,
                            period=period,
                            data_points=len(timestamps),
                        )

                        return history_data

                logger.warning(
                    "price_history_fetch_failed", symbol=symbol, status=response.status
                )
                return None

        except Exception as e:
            logger.error("price_history_fetch_error", symbol=symbol, error=str(e))
            return None

    # =========================================================================
    # 배치 히스토리 조회
    # =========================================================================

    async def fetch_multiple_histories_async(
        self, symbols: List[str], period: str = "1mo", interval: str = "1d"
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        여러 심볼의 가격 히스토리를 동시에 조회

        Args:
            symbols: 심볼 리스트
            period: 조회 기간
            interval: 데이터 간격

        Returns:
            심볼별 히스토리 데이터
        """
        logger.info(
            "batch_history_fetch_started",
            symbol_count=len(symbols),
            period=period,
            interval=interval,
        )

        # 히스토리 조회 작업들을 배치로 처리
        tasks = [
            self.fetch_price_history_async(symbol, period, interval)
            for symbol in symbols
        ]

        results = await self.async_executor.gather_with_concurrency(tasks)

        # 결과를 딕셔너리로 변환
        history_data = {}
        for i, history in enumerate(results):
            symbol = symbols[i]
            history_data[symbol] = history

        successful_count = sum(1 for h in history_data.values() if h is not None)
        logger.info(
            "batch_history_fetch_completed",
            successful_count=successful_count,
            total_count=len(symbols),
        )

        return history_data

    # =========================================================================
    # 리소스 관리
    # =========================================================================

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self._close_session()
        if hasattr(self, "executor"):
            self.executor.shutdown(wait=True)

    def __del__(self):
        """리소스 정리"""
        if hasattr(self, "executor"):
            self.executor.shutdown(wait=True)
