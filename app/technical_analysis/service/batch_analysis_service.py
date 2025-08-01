"""
기술적 분석 배치 처리 서비스

여러 심볼의 기술적 분석을 효율적으로 배치 처리하는 서비스입니다.
작업 큐를 통해 백그라운드에서 우선순위 기반으로 처리됩니다.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
import pandas as pd
import asyncio

from app.technical_analysis.service.technical_indicator_service import (
    TechnicalIndicatorService,
)
from app.technical_analysis.service.signal_generator_service import (
    SignalGeneratorService,
)
from app.technical_analysis.service.pattern_analysis_service import (
    PatternAnalysisService,
)
from app.technical_analysis.service.async_technical_indicator_service import (
    AsyncTechnicalIndicatorService,
)
from app.market_price.service.async_price_service import AsyncPriceService
from app.common.utils.logging_config import get_logger
from app.common.utils.memory_optimizer import memory_monitor, optimize_dataframe_memory
from app.common.utils.memory_cache import cache_result
from app.common.utils.task_queue import task, TaskPriority

logger = get_logger(__name__)


class BatchAnalysisService:
    """기술적 분석 배치 처리 서비스"""

    def __init__(self):
        # 동기 서비스들
        self.technical_service = TechnicalIndicatorService()
        self.signal_service = SignalGeneratorService()
        self.pattern_service = PatternAnalysisService()

        # 비동기 서비스들
        self.async_technical_service = AsyncTechnicalIndicatorService(max_workers=4)
        self.async_price_service = AsyncPriceService(max_workers=5, max_concurrency=10)

    @memory_monitor
    def analyze_symbol_batch(
        self, symbol: str, analysis_types: List[str] = None, period: str = "1mo"
    ) -> Dict[str, Any]:
        """
        단일 심볼의 배치 기술적 분석

        Args:
            symbol: 분석할 심볼
            analysis_types: 분석 타입 리스트
            period: 분석 기간

        Returns:
            분석 결과
        """
        if analysis_types is None:
            analysis_types = ["indicators", "signals", "patterns"]

        logger.info(
            "symbol_batch_analysis_started",
            symbol=symbol,
            analysis_types=analysis_types,
            period=period,
        )

        try:
            result = {
                "symbol": symbol,
                "period": period,
                "analysis_types": analysis_types,
                "results": {},
                "status": "success",
                "analyzed_at": datetime.now().isoformat(),
            }

            # 기술적 지표 분석
            if "indicators" in analysis_types:
                try:
                    indicators = self.technical_service.get_all_indicators(symbol)
                    result["results"]["indicators"] = {
                        "status": "success",
                        "data": indicators,
                    }
                    logger.debug("indicators_analysis_completed", symbol=symbol)
                except Exception as e:
                    result["results"]["indicators"] = {
                        "status": "failed",
                        "error": str(e),
                    }
                    logger.error(
                        "indicators_analysis_failed", symbol=symbol, error=str(e)
                    )

            # 신호 분석
            if "signals" in analysis_types:
                try:
                    end_date = date.today()
                    start_date = end_date - timedelta(days=30)  # 최근 30일

                    signals = self.signal_service.generate_symbol_signals(
                        symbol, start_date, end_date
                    )
                    result["results"]["signals"] = {
                        "status": "success",
                        "data": signals,
                        "period": {
                            "start": start_date.isoformat(),
                            "end": end_date.isoformat(),
                        },
                    }
                    logger.debug("signals_analysis_completed", symbol=symbol)
                except Exception as e:
                    result["results"]["signals"] = {"status": "failed", "error": str(e)}
                    logger.error("signals_analysis_failed", symbol=symbol, error=str(e))

            # 패턴 분석
            if "patterns" in analysis_types:
                try:
                    patterns = self.pattern_service.discover_patterns(symbol, "1day")
                    successful_patterns = self.pattern_service.find_successful_patterns(
                        symbol=symbol, success_threshold=0.6, min_occurrences=2
                    )

                    result["results"]["patterns"] = {
                        "status": "success",
                        "data": {
                            "discovery": patterns,
                            "successful_patterns": successful_patterns,
                        },
                    }
                    logger.debug("patterns_analysis_completed", symbol=symbol)
                except Exception as e:
                    result["results"]["patterns"] = {
                        "status": "failed",
                        "error": str(e),
                    }
                    logger.error(
                        "patterns_analysis_failed", symbol=symbol, error=str(e)
                    )

            logger.info("symbol_batch_analysis_completed", symbol=symbol)
            return result

        except Exception as e:
            logger.error("symbol_batch_analysis_failed", symbol=symbol, error=str(e))
            return {
                "symbol": symbol,
                "status": "failed",
                "error": str(e),
                "analyzed_at": datetime.now().isoformat(),
            }

    @memory_monitor
    async def analyze_symbol_batch_async(
        self, symbol: str, analysis_types: List[str] = None, period: str = "1mo"
    ) -> Dict[str, Any]:
        """
        단일 심볼의 비동기 배치 기술적 분석

        Args:
            symbol: 분석할 심볼
            analysis_types: 분석 타입 리스트
            period: 분석 기간

        Returns:
            분석 결과
        """
        if analysis_types is None:
            analysis_types = ["indicators", "signals"]

        logger.info(
            "async_symbol_batch_analysis_started",
            symbol=symbol,
            analysis_types=analysis_types,
            period=period,
        )

        try:
            result = {
                "symbol": symbol,
                "period": period,
                "analysis_types": analysis_types,
                "results": {},
                "status": "success",
                "analyzed_at": datetime.now().isoformat(),
            }

            # 가격 데이터 조회
            async with self.async_price_service:
                price_history = (
                    await self.async_price_service.fetch_price_history_async(
                        symbol, period=period, interval="1d"
                    )
                )

            if not price_history or not price_history.get("timestamps"):
                return {
                    "symbol": symbol,
                    "status": "failed",
                    "error": "No price data available",
                    "analyzed_at": datetime.now().isoformat(),
                }

            # DataFrame 생성
            df = pd.DataFrame(
                {
                    "timestamp": pd.to_datetime(price_history["timestamps"], unit="s"),
                    "open": price_history["open"],
                    "high": price_history["high"],
                    "low": price_history["low"],
                    "close": price_history["close"],
                    "volume": price_history["volume"],
                }
            ).dropna()

            if df.empty:
                return {
                    "symbol": symbol,
                    "status": "failed",
                    "error": "Empty price data",
                    "analyzed_at": datetime.now().isoformat(),
                }

            # DataFrame 메모리 최적화
            df = optimize_dataframe_memory(df)

            # 비동기 기술적 지표 분석
            if "indicators" in analysis_types:
                try:
                    indicators_data = {}

                    # RSI 계산
                    rsi = await self.async_technical_service.calculate_rsi_async(
                        df["close"]
                    )
                    if not rsi.empty:
                        indicators_data["rsi"] = {
                            "current": float(rsi.iloc[-1]),
                            "previous": float(rsi.iloc[-2]) if len(rsi) >= 2 else None,
                        }

                    # MACD 계산
                    macd_data = await self.async_technical_service.calculate_macd_async(
                        df["close"]
                    )
                    if macd_data:
                        indicators_data["macd"] = {
                            "macd": float(macd_data["macd"].iloc[-1]),
                            "signal": float(macd_data["signal"].iloc[-1]),
                            "histogram": float(macd_data["histogram"].iloc[-1]),
                        }

                    # 이동평균선 계산
                    sma_results = await self.async_technical_service.calculate_multiple_moving_averages_async(
                        df["close"], [5, 10, 20, 50, 200], "SMA"
                    )
                    indicators_data["sma"] = {
                        period: float(values.iloc[-1]) if not values.empty else None
                        for period, values in sma_results.items()
                    }

                    # 볼린저 밴드 계산
                    bb_data = await self.async_technical_service.calculate_bollinger_bands_async(
                        df["close"]
                    )
                    if bb_data:
                        indicators_data["bollinger"] = {
                            "upper": float(bb_data["upper"].iloc[-1]),
                            "middle": float(bb_data["middle"].iloc[-1]),
                            "lower": float(bb_data["lower"].iloc[-1]),
                        }

                    result["results"]["indicators"] = {
                        "status": "success",
                        "data": indicators_data,
                    }
                    logger.debug("async_indicators_analysis_completed", symbol=symbol)

                except Exception as e:
                    result["results"]["indicators"] = {
                        "status": "failed",
                        "error": str(e),
                    }
                    logger.error(
                        "async_indicators_analysis_failed", symbol=symbol, error=str(e)
                    )

            # 신호 분석 (동기 방식 사용)
            if "signals" in analysis_types:
                try:
                    end_date = date.today()
                    start_date = end_date - timedelta(days=30)

                    signals = self.signal_service.generate_symbol_signals(
                        symbol, start_date, end_date
                    )
                    result["results"]["signals"] = {
                        "status": "success",
                        "data": signals,
                        "period": {
                            "start": start_date.isoformat(),
                            "end": end_date.isoformat(),
                        },
                    }
                    logger.debug("async_signals_analysis_completed", symbol=symbol)
                except Exception as e:
                    result["results"]["signals"] = {"status": "failed", "error": str(e)}
                    logger.error(
                        "async_signals_analysis_failed", symbol=symbol, error=str(e)
                    )

            logger.info("async_symbol_batch_analysis_completed", symbol=symbol)
            return result

        except Exception as e:
            logger.error(
                "async_symbol_batch_analysis_failed", symbol=symbol, error=str(e)
            )
            return {
                "symbol": symbol,
                "status": "failed",
                "error": str(e),
                "analyzed_at": datetime.now().isoformat(),
            }

    @memory_monitor
    def analyze_multiple_symbols_batch(
        self,
        symbols: List[str],
        analysis_types: List[str] = None,
        priority_symbols: List[str] = None,
        batch_size: int = 5,
    ) -> Dict[str, Any]:
        """
        여러 심볼의 배치 기술적 분석 (우선순위 기반)

        Args:
            symbols: 분석할 심볼 리스트
            analysis_types: 분석 타입 리스트
            priority_symbols: 우선순위 심볼 리스트
            batch_size: 배치 크기

        Returns:
            배치 분석 결과
        """
        if analysis_types is None:
            analysis_types = ["indicators", "signals"]

        if priority_symbols is None:
            priority_symbols = ["^IXIC", "^GSPC", "^DJI"]  # 기본 우선순위 지수들

        logger.info(
            "multiple_symbols_batch_analysis_started",
            symbol_count=len(symbols),
            analysis_types=analysis_types,
        )

        try:
            # 우선순위 기반 심볼 정렬
            priority_set = set(priority_symbols)
            priority_symbols_filtered = [s for s in symbols if s in priority_set]
            other_symbols = [s for s in symbols if s not in priority_set]
            ordered_symbols = priority_symbols_filtered + other_symbols

            results = {}
            successful_count = 0

            # 배치 단위로 처리
            for i in range(0, len(ordered_symbols), batch_size):
                batch_symbols = ordered_symbols[i : i + batch_size]
                logger.info(
                    "processing_analysis_batch",
                    batch_start=i + 1,
                    batch_end=min(i + batch_size, len(ordered_symbols)),
                )

                for symbol in batch_symbols:
                    try:
                        result = self.analyze_symbol_batch(symbol, analysis_types)
                        results[symbol] = result

                        if result["status"] == "success":
                            successful_count += 1

                        logger.debug("symbol_analysis_completed", symbol=symbol)

                    except Exception as e:
                        results[symbol] = {
                            "symbol": symbol,
                            "status": "failed",
                            "error": str(e),
                        }
                        logger.error(
                            "symbol_analysis_failed", symbol=symbol, error=str(e)
                        )

                # 배치 간 잠시 대기
                import time

                time.sleep(0.5)

                # 배치 처리 후 메모리 정리
                del batch_symbols

            batch_result = {
                "total_symbols": len(symbols),
                "successful_count": successful_count,
                "failed_count": len(symbols) - successful_count,
                "analysis_types": analysis_types,
                "priority_symbols": priority_symbols_filtered,
                "batch_size": batch_size,
                "results": results,
                "completed_at": datetime.now().isoformat(),
            }

            logger.info(
                "multiple_symbols_batch_analysis_completed",
                total_symbols=len(symbols),
                successful_count=successful_count,
            )

            return batch_result

        except Exception as e:
            logger.error("multiple_symbols_batch_analysis_failed", error=str(e))
            return {
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.now().isoformat(),
            }

    @memory_monitor
    async def analyze_multiple_symbols_batch_async(
        self,
        symbols: List[str],
        analysis_types: List[str] = None,
        priority_symbols: List[str] = None,
        concurrency_limit: int = 3,
    ) -> Dict[str, Any]:
        """
        여러 심볼의 비동기 배치 기술적 분석

        Args:
            symbols: 분석할 심볼 리스트
            analysis_types: 분석 타입 리스트
            priority_symbols: 우선순위 심볼 리스트
            concurrency_limit: 동시 처리 제한

        Returns:
            비동기 배치 분석 결과
        """
        if analysis_types is None:
            analysis_types = ["indicators", "signals"]

        if priority_symbols is None:
            priority_symbols = ["^IXIC", "^GSPC", "^DJI"]

        logger.info(
            "async_multiple_symbols_batch_analysis_started",
            symbol_count=len(symbols),
            analysis_types=analysis_types,
        )

        try:
            # 우선순위 기반 심볼 정렬
            priority_set = set(priority_symbols)
            priority_symbols_filtered = [s for s in symbols if s in priority_set]
            other_symbols = [s for s in symbols if s not in priority_set]
            ordered_symbols = priority_symbols_filtered + other_symbols

            # 세마포어로 동시 처리 제한
            semaphore = asyncio.Semaphore(concurrency_limit)

            async def analyze_with_semaphore(symbol):
                async with semaphore:
                    return await self.analyze_symbol_batch_async(symbol, analysis_types)

            # 모든 심볼을 비동기로 처리
            tasks = [analyze_with_semaphore(symbol) for symbol in ordered_symbols]
            analysis_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 결과 정리
            results = {}
            successful_count = 0

            for symbol, result in zip(ordered_symbols, analysis_results):
                if isinstance(result, Exception):
                    results[symbol] = {
                        "symbol": symbol,
                        "status": "failed",
                        "error": str(result),
                    }
                    logger.error(
                        "async_symbol_analysis_failed", symbol=symbol, error=str(result)
                    )
                else:
                    results[symbol] = result
                    if result.get("status") == "success":
                        successful_count += 1

            batch_result = {
                "total_symbols": len(symbols),
                "successful_count": successful_count,
                "failed_count": len(symbols) - successful_count,
                "analysis_types": analysis_types,
                "priority_symbols": priority_symbols_filtered,
                "concurrency_limit": concurrency_limit,
                "results": results,
                "completed_at": datetime.now().isoformat(),
            }

            logger.info(
                "async_multiple_symbols_batch_analysis_completed",
                total_symbols=len(symbols),
                successful_count=successful_count,
            )

            return batch_result

        except Exception as e:
            logger.error("async_multiple_symbols_batch_analysis_failed", error=str(e))
            return {
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.now().isoformat(),
            }

    @cache_result(cache_name="technical_analysis", ttl=1800)  # 30분 캐싱
    @memory_monitor
    def get_batch_analysis_stats(self, symbols: List[str] = None) -> Dict[str, Any]:
        """
        배치 분석 통계 조회 (캐싱 적용)

        Args:
            symbols: 통계를 조회할 심볼 리스트

        Returns:
            배치 분석 통계
        """
        try:
            if symbols is None:
                from app.common.constants.symbol_names import SYMBOL_PRICE_MAP

                symbols = list(SYMBOL_PRICE_MAP.keys())[:10]

            stats = {
                "total_symbols": len(symbols),
                "analysis_coverage": {},
                "average_analysis_time": 0.0,
                "success_rate": 0.0,
                "last_analysis_dates": {},
            }

            # 간단한 통계 계산 (실제로는 데이터베이스에서 조회)
            successful_analyses = 0

            for symbol in symbols:
                try:
                    # 간단한 지표 계산으로 분석 가능 여부 확인
                    indicators = self.technical_service.get_all_indicators(symbol)
                    if indicators:
                        successful_analyses += 1
                        stats["last_analysis_dates"][
                            symbol
                        ] = datetime.now().isoformat()
                except:
                    pass

            stats["success_rate"] = (
                (successful_analyses / len(symbols)) * 100 if symbols else 0
            )
            stats["analysis_coverage"]["indicators"] = successful_analyses
            stats["analysis_coverage"]["signals"] = successful_analyses  # 간소화
            stats["analysis_coverage"]["patterns"] = successful_analyses  # 간소화

            stats["generated_at"] = datetime.now().isoformat()

            return stats

        except Exception as e:
            logger.error("batch_analysis_stats_failed", error=str(e))
            return {"error": str(e), "generated_at": datetime.now().isoformat()}


# 작업 큐용 백그라운드 작업들
@task(priority=TaskPriority.NORMAL, max_retries=2, timeout=900.0)
@memory_monitor
async def analyze_symbols_batch_background(
    symbols: List[str], analysis_types: List[str] = None, use_async: bool = True
) -> Dict[str, Any]:
    """
    심볼들의 배치 기술적 분석을 백그라운드 작업으로 처리
    """
    logger.info(
        "background_batch_analysis_started",
        symbol_count=len(symbols),
        analysis_types=analysis_types,
    )

    try:
        service = BatchAnalysisService()

        if use_async:
            result = await service.analyze_multiple_symbols_batch_async(
                symbols, analysis_types, concurrency_limit=3
            )
        else:
            result = service.analyze_multiple_symbols_batch(
                symbols, analysis_types, batch_size=5
            )

        logger.info("background_batch_analysis_completed", symbol_count=len(symbols))

        return {
            "task": "batch_technical_analysis",
            "status": "completed",
            "result": result,
            "completed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("background_batch_analysis_failed", error=str(e))
        return {
            "task": "batch_technical_analysis",
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat(),
        }


@task(priority=TaskPriority.HIGH, max_retries=1, timeout=300.0)
@memory_monitor
async def analyze_priority_symbols_background(
    priority_symbols: List[str] = None,
) -> Dict[str, Any]:
    """
    우선순위 심볼들의 기술적 분석을 백그라운드 작업으로 처리
    """
    if priority_symbols is None:
        priority_symbols = ["^IXIC", "^GSPC", "^DJI"]

    logger.info(
        "background_priority_analysis_started", symbol_count=len(priority_symbols)
    )

    try:
        service = BatchAnalysisService()
        result = await service.analyze_multiple_symbols_batch_async(
            priority_symbols,
            analysis_types=["indicators", "signals"],
            concurrency_limit=2,
        )

        logger.info(
            "background_priority_analysis_completed", symbol_count=len(priority_symbols)
        )

        return {
            "task": "priority_technical_analysis",
            "status": "completed",
            "result": result,
            "completed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("background_priority_analysis_failed", error=str(e))
        return {
            "task": "priority_technical_analysis",
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat(),
        }
