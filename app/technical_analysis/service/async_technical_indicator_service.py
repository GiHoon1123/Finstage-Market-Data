"""
비동기 기술적 지표 계산 서비스

기존 TechnicalIndicatorService를 비동기로 변환하여
I/O 블로킹 없이 여러 지표를 동시에 계산할 수 있습니다.
"""

import asyncio
import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import functools

from app.common.constants.technical_settings import MA_PERIODS
from app.common.utils.memory_cache import cache_technical_analysis
from app.common.utils.memory_optimizer import optimize_dataframe_memory, memory_monitor
from app.common.utils.async_executor import AsyncExecutor, async_timed
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class AsyncTechnicalIndicatorService:
    """비동기 기술적 지표 계산 서비스"""

    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.async_executor = AsyncExecutor(max_concurrency=10)
        self._cache_key_func = (
            lambda symbol, period, ma_type="SMA": f"{symbol}_{period}_{ma_type}"
        )

    def _run_in_executor(self, func, *args, **kwargs):
        """CPU 집약적 작업을 별도 스레드에서 실행"""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(
            self.executor, functools.partial(func, *args, **kwargs)
        )

    # =========================================================================
    # 비동기 이동평균선 계산
    # =========================================================================

    @async_timed()
    async def calculate_moving_average_async(
        self, prices: pd.Series, period: int, ma_type: str = "SMA"
    ) -> pd.Series:
        """
        비동기 이동평균선 계산

        Args:
            prices: 가격 데이터
            period: 계산 기간
            ma_type: 이동평균 유형 ("SMA", "EMA")

        Returns:
            이동평균값들의 시리즈
        """

        def _calculate_ma():
            try:
                if ma_type == "SMA":
                    ma = prices.rolling(window=period, min_periods=period).mean()
                elif ma_type == "EMA":
                    ma = prices.ewm(span=period, adjust=False).mean()
                else:
                    raise ValueError(f"지원하지 않는 이동평균 유형: {ma_type}")

                logger.debug(
                    "moving_average_calculated",
                    ma_type=ma_type,
                    period=period,
                    data_points=len(ma.dropna()),
                )
                return ma

            except Exception as e:
                logger.error(
                    "moving_average_calculation_failed",
                    ma_type=ma_type,
                    period=period,
                    error=str(e),
                )
                return pd.Series()

        return await self._run_in_executor(_calculate_ma)

    async def calculate_multiple_moving_averages_async(
        self, prices: pd.Series, periods: List[int], ma_type: str = "SMA"
    ) -> Dict[int, pd.Series]:
        """
        여러 기간의 이동평균을 동시에 계산

        Args:
            prices: 가격 데이터
            periods: 계산할 기간들 [5, 10, 20, 50, 200]
            ma_type: 이동평균 유형

        Returns:
            기간별 이동평균 딕셔너리
        """
        tasks = [
            self.calculate_moving_average_async(prices, period, ma_type)
            for period in periods
        ]

        results = await self.async_executor.gather_with_concurrency(tasks)

        return {
            period: result
            for period, result in zip(periods, results)
            if not result.empty
        }

    # =========================================================================
    # 비동기 RSI 계산
    # =========================================================================

    @async_timed()
    async def calculate_rsi_async(
        self, prices: pd.Series, period: int = 14
    ) -> pd.Series:
        """
        비동기 RSI 계산

        Args:
            prices: 가격 데이터
            period: RSI 계산 기간

        Returns:
            RSI 값들의 시리즈
        """

        def _calculate_rsi():
            try:
                # 가격 변화량 계산
                delta = prices.diff()

                # 상승분과 하락분 분리
                gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

                # RS (Relative Strength) 계산
                rs = gain / loss

                # RSI 계산
                rsi = 100 - (100 / (1 + rs))

                logger.debug(
                    "rsi_calculated", period=period, data_points=len(rsi.dropna())
                )
                return rsi

            except Exception as e:
                logger.error("rsi_calculation_failed", period=period, error=str(e))
                return pd.Series()

        return await self._run_in_executor(_calculate_rsi)

    # =========================================================================
    # 비동기 MACD 계산
    # =========================================================================

    @async_timed()
    async def calculate_macd_async(
        self,
        prices: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> Dict[str, pd.Series]:
        """
        비동기 MACD 계산

        Args:
            prices: 가격 데이터
            fast_period: 빠른 EMA 기간
            slow_period: 느린 EMA 기간
            signal_period: 시그널 라인 기간

        Returns:
            MACD, Signal, Histogram 딕셔너리
        """

        def _calculate_macd():
            try:
                # 빠른 EMA와 느린 EMA 계산
                fast_ema = prices.ewm(span=fast_period).mean()
                slow_ema = prices.ewm(span=slow_period).mean()

                # MACD 라인 계산
                macd_line = fast_ema - slow_ema

                # 시그널 라인 계산
                signal_line = macd_line.ewm(span=signal_period).mean()

                # 히스토그램 계산
                histogram = macd_line - signal_line

                result = {
                    "macd": macd_line,
                    "signal": signal_line,
                    "histogram": histogram,
                }

                logger.debug(
                    "macd_calculated",
                    fast_period=fast_period,
                    slow_period=slow_period,
                    signal_period=signal_period,
                )
                return result

            except Exception as e:
                logger.error("macd_calculation_failed", error=str(e))
                return {}

        return await self._run_in_executor(_calculate_macd)

    # =========================================================================
    # 비동기 볼린저 밴드 계산
    # =========================================================================

    @async_timed()
    async def calculate_bollinger_bands_async(
        self, prices: pd.Series, period: int = 20, std_dev: float = 2
    ) -> Dict[str, pd.Series]:
        """
        비동기 볼린저 밴드 계산

        Args:
            prices: 가격 데이터
            period: 이동평균 계산 기간
            std_dev: 표준편차 배수

        Returns:
            상단밴드, 중간선, 하단밴드 딕셔너리
        """

        def _calculate_bollinger():
            try:
                # 중간선 (이동평균선) 계산
                middle_band = prices.rolling(window=period).mean()

                # 표준편차 계산
                std = prices.rolling(window=period).std()

                # 상단 밴드와 하단 밴드 계산
                upper_band = middle_band + (std * std_dev)
                lower_band = middle_band - (std * std_dev)

                result = {
                    "upper": upper_band,
                    "middle": middle_band,
                    "lower": lower_band,
                }

                logger.debug(
                    "bollinger_bands_calculated", period=period, std_dev=std_dev
                )
                return result

            except Exception as e:
                logger.error("bollinger_bands_calculation_failed", error=str(e))
                return {}

        return await self._run_in_executor(_calculate_bollinger)

    # =========================================================================
    # 비동기 스토캐스틱 계산
    # =========================================================================

    @async_timed()
    async def calculate_stochastic_async(
        self, df: pd.DataFrame, k_period: int = 14, d_period: int = 3
    ) -> Dict[str, pd.Series]:
        """
        비동기 스토캐스틱 계산

        Args:
            df: OHLC 데이터프레임
            k_period: %K 계산 기간
            d_period: %D 계산 기간

        Returns:
            %K, %D 딕셔너리
        """

        def _calculate_stochastic():
            try:
                # 필요한 컬럼 확인
                required_columns = ["high", "low", "close"]
                missing_columns = [
                    col for col in required_columns if col not in df.columns
                ]

                if missing_columns:
                    logger.error(
                        "stochastic_missing_columns", missing_columns=missing_columns
                    )
                    return {}

                # 최고가와 최저가의 rolling 계산
                highest_high = df["high"].rolling(window=k_period).max()
                lowest_low = df["low"].rolling(window=k_period).min()

                # %K 계산
                k_percent = (
                    (df["close"] - lowest_low) / (highest_high - lowest_low)
                ) * 100

                # %D 계산 (%K의 이동평균)
                d_percent = k_percent.rolling(window=d_period).mean()

                result = {
                    "k_percent": k_percent,
                    "d_percent": d_percent,
                }

                logger.debug(
                    "stochastic_calculated", k_period=k_period, d_period=d_period
                )
                return result

            except Exception as e:
                logger.error("stochastic_calculation_failed", error=str(e))
                return {}

        return await self._run_in_executor(_calculate_stochastic)

    # =========================================================================
    # 비동기 종합 기술적 분석
    # =========================================================================

    @async_timed()
    @memory_monitor(threshold_mb=300.0)
    async def analyze_comprehensive_signals_async(
        self, df: pd.DataFrame, symbol: str = None
    ) -> Dict[str, Any]:
        """
        비동기 종합 기술적 분석

        Args:
            df: OHLCV 데이터프레임
            symbol: 심볼 (로깅용)

        Returns:
            모든 지표의 분석 결과
        """
        try:
            logger.info("comprehensive_analysis_started", symbol=symbol)

            results = {
                "timestamp": datetime.now(),
                "symbol": symbol,
                "current_price": df["close"].iloc[-1],
                "price_change_pct": (
                    (df["close"].iloc[-1] - df["close"].iloc[-2]) / df["close"].iloc[-2]
                )
                * 100,
                "signals": {},
                "indicators": {},
            }

            # 모든 지표를 동시에 계산
            tasks = [
                # 이동평균선들
                self.calculate_multiple_moving_averages_async(
                    df["close"], [5, 10, 20, 50, 200], "SMA"
                ),
                self.calculate_multiple_moving_averages_async(
                    df["close"], [12, 26], "EMA"
                ),
                # 기술적 지표들
                self.calculate_rsi_async(df["close"]),
                self.calculate_macd_async(df["close"]),
                self.calculate_bollinger_bands_async(df["close"]),
                self.calculate_stochastic_async(df),
            ]

            # 모든 계산을 병렬로 실행
            (sma_results, ema_results, rsi, macd_data, bb_data, stoch_data) = (
                await self.async_executor.gather_with_concurrency(tasks)
            )

            # 결과 정리
            results["indicators"]["sma"] = sma_results
            results["indicators"]["ema"] = ema_results

            if not rsi.empty:
                results["indicators"]["rsi"] = {
                    "current": rsi.iloc[-1],
                    "previous": rsi.iloc[-2] if len(rsi) >= 2 else None,
                }

            if macd_data:
                results["indicators"]["macd"] = {
                    "current_macd": macd_data["macd"].iloc[-1],
                    "current_signal": macd_data["signal"].iloc[-1],
                    "current_histogram": macd_data["histogram"].iloc[-1],
                }

            if bb_data:
                results["indicators"]["bollinger"] = {
                    "upper": bb_data["upper"].iloc[-1],
                    "middle": bb_data["middle"].iloc[-1],
                    "lower": bb_data["lower"].iloc[-1],
                }

            if stoch_data:
                results["indicators"]["stochastic"] = {
                    "k_percent": stoch_data["k_percent"].iloc[-1],
                    "d_percent": stoch_data["d_percent"].iloc[-1],
                }

            # 신호 감지 (동기 함수들 사용)
            await self._detect_signals_async(results)

            logger.info(
                "comprehensive_analysis_completed",
                symbol=symbol,
                signals_count=len(results["signals"]),
            )

            return results

        except Exception as e:
            logger.error("comprehensive_analysis_failed", symbol=symbol, error=str(e))
            return {"error": str(e), "symbol": symbol}

    async def _detect_signals_async(self, results: Dict[str, Any]):
        """비동기 신호 감지"""

        def _detect_signals():
            # 기존 동기 신호 감지 로직을 여기서 실행
            # (신호 감지는 CPU 집약적이지 않으므로 간단하게 처리)
            signals = {}

            # RSI 신호
            if "rsi" in results["indicators"]:
                rsi_data = results["indicators"]["rsi"]
                if rsi_data["current"] and rsi_data["previous"]:
                    if rsi_data["previous"] < 70 and rsi_data["current"] >= 70:
                        signals["rsi"] = "overbought"
                    elif rsi_data["previous"] > 30 and rsi_data["current"] <= 30:
                        signals["rsi"] = "oversold"

            # MACD 신호
            if "macd" in results["indicators"]:
                macd_data = results["indicators"]["macd"]
                if (
                    macd_data["current_macd"] > macd_data["current_signal"]
                    and macd_data["current_histogram"] > 0
                ):
                    signals["macd"] = "bullish"
                elif (
                    macd_data["current_macd"] < macd_data["current_signal"]
                    and macd_data["current_histogram"] < 0
                ):
                    signals["macd"] = "bearish"

            return signals

        signals = await self._run_in_executor(_detect_signals)
        results["signals"].update(signals)

    # =========================================================================
    # 배치 처리
    # =========================================================================

    async def analyze_multiple_symbols_async(
        self, symbol_data_map: Dict[str, pd.DataFrame], batch_size: int = 5
    ) -> Dict[str, Dict[str, Any]]:
        """
        여러 심볼의 기술적 분석을 배치로 처리

        Args:
            symbol_data_map: 심볼별 데이터프레임 딕셔너리
            batch_size: 배치 크기

        Returns:
            심볼별 분석 결과
        """
        logger.info(
            "batch_analysis_started",
            symbol_count=len(symbol_data_map),
            batch_size=batch_size,
        )

        async def analyze_symbol(symbol_data):
            symbol, df = symbol_data
            return symbol, await self.analyze_comprehensive_signals_async(df, symbol)

        # 심볼-데이터 쌍을 배치로 처리
        symbol_items = list(symbol_data_map.items())

        results = await self.async_executor.process_batch(
            items=symbol_items,
            processor=analyze_symbol,
            batch_size=batch_size,
            batch_delay=0.5,  # 배치 간 0.5초 지연
        )

        # 결과를 딕셔너리로 변환
        analysis_results = {}
        for symbol, result in results:
            if result and "error" not in result:
                analysis_results[symbol] = result
            else:
                logger.warning("symbol_analysis_failed", symbol=symbol)

        logger.info(
            "batch_analysis_completed",
            successful_count=len(analysis_results),
            total_count=len(symbol_data_map),
        )

        return analysis_results

    def __del__(self):
        """리소스 정리"""
        if hasattr(self, "executor"):
            self.executor.shutdown(wait=True)
