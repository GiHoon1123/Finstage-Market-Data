"""
비동기 기술적 분석 API 라우터

기존 동기 API를 비동기로 변환하여 성능을 향상시킨 엔드포인트들
"""

import asyncio
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

from app.technical_analysis.service.async_technical_indicator_service import (
    AsyncTechnicalIndicatorService,
)
from app.market_price.service.async_price_service import AsyncPriceService
from app.common.utils.async_executor import async_timed
from app.common.utils.logging_config import get_logger
from app.common.constants.symbol_names import SYMBOL_PRICE_MAP
from app.common.utils.memory_cache import cache_result, get_cache_stats
from app.common.utils.memory_optimizer import memory_monitor
from app.common.utils.task_queue import TaskQueue
from app.common.services.background_tasks import run_technical_analysis_batch_background
from app.common.utils.websocket_manager import WebSocketManager

logger = get_logger(__name__)
router = APIRouter(
    prefix="/api/v2/technical-analysis", tags=["Async Technical Analysis"]
)

# 서비스 인스턴스
technical_service = AsyncTechnicalIndicatorService(max_workers=4)
price_service = AsyncPriceService(max_workers=5, max_concurrency=10)
websocket_manager = WebSocketManager()


@router.get("/indicators/{symbol}", summary="비동기 기술적 지표 계산")
@async_timed()
@memory_monitor
async def calculate_technical_indicators_async(
    symbol: str,
    period: str = Query("1mo", description="데이터 기간 (1d, 5d, 1mo, 3mo, 6mo, 1y)"),
    indicators: str = Query(
        "all",
        description="계산할 지표 (all, sma, ema, rsi, macd, bollinger, stochastic)",
    ),
) -> Dict[str, Any]:
    """
    단일 심볼의 기술적 지표를 비동기로 계산합니다.

    Args:
        symbol: 분석할 심볼 (예: AAPL, GOOGL)
        period: 데이터 조회 기간
        indicators: 계산할 지표 종류

    Returns:
        계산된 기술적 지표들
    """
    try:
        logger.info("async_technical_analysis_started", symbol=symbol, period=period)

        # 가격 히스토리 조회
        async with price_service:
            price_history = await price_service.fetch_price_history_async(
                symbol, period=period, interval="1d"
            )

        if not price_history or not price_history.get("timestamps"):
            raise HTTPException(
                status_code=404,
                detail=f"심볼 {symbol}의 가격 데이터를 찾을 수 없습니다",
            )

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
            raise HTTPException(
                status_code=400, detail=f"심볼 {symbol}의 유효한 가격 데이터가 없습니다"
            )

        # 요청된 지표에 따라 계산
        result = {
            "symbol": symbol,
            "period": period,
            "data_points": len(df),
            "last_updated": datetime.now().isoformat(),
            "indicators": {},
        }

        if indicators == "all" or "sma" in indicators:
            sma_results = (
                await technical_service.calculate_multiple_moving_averages_async(
                    df["close"], [5, 10, 20, 50, 200], "SMA"
                )
            )
            result["indicators"]["sma"] = {
                period: values.iloc[-1] if not values.empty else None
                for period, values in sma_results.items()
            }

        if indicators == "all" or "ema" in indicators:
            ema_results = (
                await technical_service.calculate_multiple_moving_averages_async(
                    df["close"], [12, 26], "EMA"
                )
            )
            result["indicators"]["ema"] = {
                period: values.iloc[-1] if not values.empty else None
                for period, values in ema_results.items()
            }

        if indicators == "all" or "rsi" in indicators:
            rsi = await technical_service.calculate_rsi_async(df["close"])
            if not rsi.empty:
                result["indicators"]["rsi"] = {
                    "current": rsi.iloc[-1],
                    "previous": rsi.iloc[-2] if len(rsi) >= 2 else None,
                }

        if indicators == "all" or "macd" in indicators:
            macd_data = await technical_service.calculate_macd_async(df["close"])
            if macd_data:
                result["indicators"]["macd"] = {
                    "macd": macd_data["macd"].iloc[-1],
                    "signal": macd_data["signal"].iloc[-1],
                    "histogram": macd_data["histogram"].iloc[-1],
                }

        if indicators == "all" or "bollinger" in indicators:
            bb_data = await technical_service.calculate_bollinger_bands_async(
                df["close"]
            )
            if bb_data:
                result["indicators"]["bollinger"] = {
                    "upper": bb_data["upper"].iloc[-1],
                    "middle": bb_data["middle"].iloc[-1],
                    "lower": bb_data["lower"].iloc[-1],
                }

        if indicators == "all" or "stochastic" in indicators:
            stoch_data = await technical_service.calculate_stochastic_async(df)
            if stoch_data:
                result["indicators"]["stochastic"] = {
                    "k_percent": stoch_data["k_percent"].iloc[-1],
                    "d_percent": stoch_data["d_percent"].iloc[-1],
                }

        logger.info(
            "async_technical_analysis_completed",
            symbol=symbol,
            indicators_count=len(result["indicators"]),
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("async_technical_analysis_failed", symbol=symbol, error=str(e))
        raise HTTPException(status_code=500, detail=f"기술적 분석 실패: {str(e)}")


@router.post("/batch/indicators", summary="배치 기술적 지표 계산")
@async_timed()
@memory_monitor
async def calculate_batch_technical_indicators_async(
    symbols: List[str],
    period: str = Query("1mo", description="데이터 기간"),
    batch_size: int = Query(5, description="배치 크기", ge=1, le=20),
) -> Dict[str, Any]:
    """
    여러 심볼의 기술적 지표를 배치로 계산합니다.

    Args:
        symbols: 분석할 심볼 리스트
        period: 데이터 조회 기간
        batch_size: 동시 처리할 심볼 수

    Returns:
        심볼별 기술적 지표 결과
    """
    try:
        logger.info(
            "batch_technical_analysis_started",
            symbol_count=len(symbols),
            batch_size=batch_size,
        )

        # 가격 히스토리를 배치로 조회
        async with price_service:
            price_histories = await price_service.fetch_multiple_histories_async(
                symbols, period=period, interval="1d"
            )

        # DataFrame으로 변환
        symbol_data_map = {}
        for symbol, history in price_histories.items():
            if history and history.get("timestamps"):
                df = pd.DataFrame(
                    {
                        "timestamp": pd.to_datetime(history["timestamps"], unit="s"),
                        "open": history["open"],
                        "high": history["high"],
                        "low": history["low"],
                        "close": history["close"],
                        "volume": history["volume"],
                    }
                ).dropna()

                if not df.empty:
                    symbol_data_map[symbol] = df

        if not symbol_data_map:
            raise HTTPException(
                status_code=404, detail="유효한 가격 데이터를 가진 심볼이 없습니다"
            )

        # 배치로 기술적 분석 실행
        analysis_results = await technical_service.analyze_multiple_symbols_async(
            symbol_data_map, batch_size=batch_size
        )

        result = {
            "timestamp": datetime.now().isoformat(),
            "period": period,
            "requested_symbols": len(symbols),
            "analyzed_symbols": len(analysis_results),
            "batch_size": batch_size,
            "results": analysis_results,
        }

        logger.info(
            "batch_technical_analysis_completed",
            requested_count=len(symbols),
            analyzed_count=len(analysis_results),
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("batch_technical_analysis_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"배치 기술적 분석 실패: {str(e)}")


@router.get("/prices/monitor", summary="비동기 가격 모니터링")
@async_timed()
@memory_monitor
async def monitor_prices_async(
    symbols: Optional[str] = Query(
        None, description="모니터링할 심볼들 (쉼표 구분, 미지정시 전체)"
    ),
    alerts_only: bool = Query(False, description="알림이 있는 심볼만 반환"),
) -> Dict[str, Any]:
    """
    여러 심볼의 가격을 동시에 모니터링합니다.

    Args:
        symbols: 모니터링할 심볼들 (미지정시 전체)
        alerts_only: 알림이 있는 심볼만 반환할지 여부

    Returns:
        심볼별 가격 모니터링 결과
    """
    try:
        # 심볼 리스트 파싱
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(",")]
        else:
            symbol_list = list(SYMBOL_PRICE_MAP.keys())

        logger.info("async_price_monitoring_started", symbol_count=len(symbol_list))

        # 비동기 가격 모니터링 실행
        async with price_service:
            monitoring_results = await price_service.monitor_prices_async(symbol_list)

        # 알림만 필터링 (요청시)
        if alerts_only:
            monitoring_results = {
                symbol: result
                for symbol, result in monitoring_results.items()
                if result.get("alerts") and len(result["alerts"]) > 0
            }

        # 통계 계산
        total_alerts = sum(
            len(result.get("alerts", [])) for result in monitoring_results.values()
        )

        symbols_with_alerts = sum(
            1
            for result in monitoring_results.values()
            if result.get("alerts") and len(result["alerts"]) > 0
        )

        result = {
            "timestamp": datetime.now().isoformat(),
            "monitored_symbols": len(monitoring_results),
            "total_alerts": total_alerts,
            "symbols_with_alerts": symbols_with_alerts,
            "results": monitoring_results,
        }

        logger.info(
            "async_price_monitoring_completed",
            monitored_count=len(monitoring_results),
            alerts_count=total_alerts,
        )

        return result

    except Exception as e:
        logger.error("async_price_monitoring_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"가격 모니터링 실패: {str(e)}")


@router.get("/prices/batch", summary="배치 가격 조회")
@async_timed()
@memory_monitor
async def get_batch_prices_async(
    symbols: str = Query(..., description="조회할 심볼들 (쉼표 구분)"),
    include_history: bool = Query(False, description="가격 히스토리 포함 여부"),
) -> Dict[str, Any]:
    """
    여러 심볼의 현재 가격을 동시에 조회합니다.

    Args:
        symbols: 조회할 심볼들 (쉼표로 구분)
        include_history: 가격 히스토리도 함께 조회할지 여부

    Returns:
        심볼별 가격 정보
    """
    try:
        # 심볼 리스트 파싱
        symbol_list = [s.strip() for s in symbols.split(",")]

        logger.info(
            "batch_price_fetch_started",
            symbol_count=len(symbol_list),
            include_history=include_history,
        )

        async with price_service:
            if include_history:
                # 현재 가격과 히스토리를 동시에 조회
                current_prices_task = price_service.fetch_multiple_prices_async(
                    symbol_list
                )
                histories_task = price_service.fetch_multiple_histories_async(
                    symbol_list, period="5d", interval="1d"
                )

                current_prices, histories = await asyncio.gather(
                    current_prices_task, histories_task
                )

                # 결과 결합
                results = {}
                for symbol in symbol_list:
                    results[symbol] = {
                        "current_price": current_prices.get(symbol),
                        "history": histories.get(symbol),
                    }
            else:
                # 현재 가격만 조회
                current_prices = await price_service.fetch_multiple_prices_async(
                    symbol_list
                )
                results = {
                    symbol: {"current_price": price}
                    for symbol, price in current_prices.items()
                }

        successful_count = sum(
            1 for result in results.values() if result.get("current_price") is not None
        )

        response = {
            "timestamp": datetime.now().isoformat(),
            "requested_symbols": len(symbol_list),
            "successful_symbols": successful_count,
            "include_history": include_history,
            "results": results,
        }

        logger.info(
            "batch_price_fetch_completed",
            requested_count=len(symbol_list),
            successful_count=successful_count,
        )

        return response

    except Exception as e:
        logger.error("batch_price_fetch_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"배치 가격 조회 실패: {str(e)}")


@router.post("/analysis/comprehensive", summary="종합 비동기 분석")
@async_timed()
@memory_monitor
async def comprehensive_analysis_async(
    symbols: List[str],
    background_tasks: BackgroundTasks,
    period: str = Query("1mo", description="분석 기간"),
    save_results: bool = Query(False, description="결과 저장 여부"),
) -> Dict[str, Any]:
    """
    여러 심볼에 대한 종합적인 비동기 분석을 수행합니다.

    Args:
        symbols: 분석할 심볼 리스트
        background_tasks: 백그라운드 작업 (결과 저장용)
        period: 분석 기간
        save_results: 분석 결과를 데이터베이스에 저장할지 여부

    Returns:
        종합 분석 결과
    """
    try:
        logger.info(
            "comprehensive_async_analysis_started",
            symbol_count=len(symbols),
            period=period,
        )

        # 가격 데이터와 기술적 분석을 동시에 실행
        async with price_service:
            # 1. 현재 가격 모니터링
            monitoring_task = price_service.monitor_prices_async(symbols)

            # 2. 가격 히스토리 조회
            histories_task = price_service.fetch_multiple_histories_async(
                symbols, period=period, interval="1d"
            )

            monitoring_results, price_histories = await asyncio.gather(
                monitoring_task, histories_task
            )

        # 3. DataFrame 변환 및 기술적 분석
        symbol_data_map = {}
        for symbol, history in price_histories.items():
            if history and history.get("timestamps"):
                df = pd.DataFrame(
                    {
                        "timestamp": pd.to_datetime(history["timestamps"], unit="s"),
                        "open": history["open"],
                        "high": history["high"],
                        "low": history["low"],
                        "close": history["close"],
                        "volume": history["volume"],
                    }
                ).dropna()

                if not df.empty:
                    symbol_data_map[symbol] = df

        # 4. 기술적 분석 실행
        technical_results = await technical_service.analyze_multiple_symbols_async(
            symbol_data_map, batch_size=3
        )

        # 5. 결과 통합
        comprehensive_results = {}
        for symbol in symbols:
            comprehensive_results[symbol] = {
                "price_monitoring": monitoring_results.get(symbol, {}),
                "technical_analysis": technical_results.get(symbol, {}),
                "data_available": symbol in symbol_data_map,
            }

        result = {
            "timestamp": datetime.now().isoformat(),
            "analysis_period": period,
            "analyzed_symbols": len(comprehensive_results),
            "symbols_with_data": len(symbol_data_map),
            "total_alerts": sum(
                len(r.get("price_monitoring", {}).get("alerts", []))
                for r in comprehensive_results.values()
            ),
            "results": comprehensive_results,
        }

        # 백그라운드에서 결과 저장 (요청시)
        if save_results:
            background_tasks.add_task(_save_analysis_results_background, result)

        logger.info(
            "comprehensive_async_analysis_completed",
            analyzed_count=len(comprehensive_results),
            symbols_with_data=len(symbol_data_map),
        )

        return result

    except Exception as e:
        logger.error("comprehensive_async_analysis_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"종합 분석 실패: {str(e)}")


async def _save_analysis_results_background(results: Dict[str, Any]):
    """백그라운드에서 분석 결과 저장"""
    try:
        # 여기서 데이터베이스에 결과 저장
        # (실제 구현은 요구사항에 따라)
        logger.info(
            "analysis_results_saved_background",
            symbols_count=results["analyzed_symbols"],
        )
    except Exception as e:
        logger.error("background_save_failed", error=str(e))


# 서비스 정리를 위한 이벤트 핸들러
@router.on_event("shutdown")
async def shutdown_services():
    """서비스 리소스 정리"""
    try:
        await price_service._close_session()
        logger.info("async_services_shutdown_completed")
    except Exception as e:
        logger.error("async_services_shutdown_failed", error=str(e))


@router.post("/analysis/background", summary="백그라운드 분석 작업 큐잉")
@async_timed()
@memory_monitor
async def queue_background_analysis(
    background_tasks: BackgroundTasks,
    symbols: List[str] = Query(..., description="분석할 심볼 리스트"),
    analysis_types: List[str] = Query(
        ["indicators", "signals"], description="분석 타입"
    ),
) -> Dict[str, Any]:
    """
    무거운 기술적 분석 작업을 백그라운드 큐에 추가합니다.

    Args:
        symbols: 분석할 심볼 리스트
        analysis_types: 분석 타입 리스트

    Returns:
        작업 큐잉 결과
    """
    try:
        logger.info(
            "background_analysis_queuing_started",
            symbol_count=len(symbols),
            analysis_types=analysis_types,
        )

        # 작업 큐에 백그라운드 분석 작업 추가
        task_queue = TaskQueue()
        task_id = await task_queue.enqueue_task(
            run_technical_analysis_batch_background,
            symbols=symbols,
            analysis_types=analysis_types,
        )

        logger.info(
            "background_analysis_queued", task_id=task_id, symbol_count=len(symbols)
        )

        return {
            "status": "queued",
            "task_id": task_id,
            "symbols": symbols,
            "analysis_types": analysis_types,
            "estimated_completion": "5-10 minutes",
            "queued_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("background_analysis_queuing_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"백그라운드 분석 작업 큐잉 실패: {str(e)}"
        )


@router.get("/analysis/status/{task_id}", summary="백그라운드 분석 작업 상태 조회")
@async_timed()
@memory_monitor
async def get_background_analysis_status(task_id: str) -> Dict[str, Any]:
    """
    백그라운드 분석 작업의 상태를 조회합니다.

    Args:
        task_id: 작업 ID

    Returns:
        작업 상태 정보
    """
    try:
        task_queue = TaskQueue()
        status = await task_queue.get_task_status(task_id)

        return {
            "task_id": task_id,
            "status": status.get("status", "unknown"),
            "progress": status.get("progress", 0),
            "result": status.get("result"),
            "error": status.get("error"),
            "created_at": status.get("created_at"),
            "completed_at": status.get("completed_at"),
        }

    except Exception as e:
        logger.error(
            "background_analysis_status_query_failed", task_id=task_id, error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"작업 상태 조회 실패: {str(e)}")


@router.get("/cache/stats", summary="캐시 통계 조회")
@memory_monitor
async def get_cache_statistics() -> Dict[str, Any]:
    """
    기술적 분석 관련 캐시 통계를 조회합니다.

    Returns:
        캐시 통계 정보
    """
    try:
        from app.common.utils.memory_cache import get_cache_stats

        # 기술적 분석 관련 캐시 통계 조회
        cache_stats = get_cache_stats("technical_analysis")

        return {
            "cache_name": "technical_analysis",
            "statistics": cache_stats,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("cache_statistics_query_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"캐시 통계 조회 실패: {str(e)}")


@router.post("/streaming/start", summary="기술적 분석 실시간 스트리밍 시작")
@async_timed()
@memory_monitor
async def start_technical_analysis_streaming(
    symbols: List[str] = Query(..., description="스트리밍할 심볼 리스트"),
    indicators: List[str] = Query(
        ["rsi", "macd", "sma"], description="스트리밍할 지표들"
    ),
    interval_seconds: int = Query(30, description="업데이트 간격 (초)"),
) -> Dict[str, Any]:
    """
    기술적 분석 결과를 실시간으로 스트리밍 시작합니다.

    Args:
        symbols: 스트리밍할 심볼 리스트
        indicators: 스트리밍할 지표들
        interval_seconds: 업데이트 간격

    Returns:
        스트리밍 시작 결과
    """
    try:
        logger.info(
            "technical_analysis_streaming_started",
            symbol_count=len(symbols),
            indicators=indicators,
        )

        # 백그라운드에서 실시간 스트리밍 시작
        import asyncio

        asyncio.create_task(
            stream_technical_analysis_updates(symbols, indicators, interval_seconds)
        )

        return {
            "status": "streaming_started",
            "symbols": symbols,
            "indicators": indicators,
            "interval_seconds": interval_seconds,
            "started_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("technical_analysis_streaming_start_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"기술적 분석 스트리밍 시작 실패: {str(e)}"
        )


async def stream_technical_analysis_updates(
    symbols: List[str], indicators: List[str], interval_seconds: int
):
    """
    기술적 분석 결과를 실시간으로 스트리밍하는 백그라운드 작업
    """
    import asyncio

    while True:
        try:
            for symbol in symbols:
                try:
                    # 가격 데이터 조회
                    async with price_service:
                        price_history = await price_service.fetch_price_history_async(
                            symbol, period="1mo", interval="1d"
                        )

                    if not price_history or not price_history.get("timestamps"):
                        continue

                    # DataFrame 생성
                    df = pd.DataFrame(
                        {
                            "timestamp": pd.to_datetime(
                                price_history["timestamps"], unit="s"
                            ),
                            "open": price_history["open"],
                            "high": price_history["high"],
                            "low": price_history["low"],
                            "close": price_history["close"],
                            "volume": price_history["volume"],
                        }
                    ).dropna()

                    if df.empty:
                        continue

                    # 지표별 계산 및 브로드캐스트
                    analysis_results = {
                        "symbol": symbol,
                        "timestamp": datetime.now().isoformat(),
                        "indicators": {},
                    }

                    if "rsi" in indicators:
                        rsi = await technical_service.calculate_rsi_async(df["close"])
                        if not rsi.empty:
                            analysis_results["indicators"]["rsi"] = {
                                "current": float(rsi.iloc[-1]),
                                "previous": (
                                    float(rsi.iloc[-2]) if len(rsi) >= 2 else None
                                ),
                                "signal": (
                                    "overbought"
                                    if rsi.iloc[-1] > 70
                                    else "oversold" if rsi.iloc[-1] < 30 else "neutral"
                                ),
                            }

                    if "macd" in indicators:
                        macd_data = await technical_service.calculate_macd_async(
                            df["close"]
                        )
                        if macd_data:
                            analysis_results["indicators"]["macd"] = {
                                "macd": float(macd_data["macd"].iloc[-1]),
                                "signal": float(macd_data["signal"].iloc[-1]),
                                "histogram": float(macd_data["histogram"].iloc[-1]),
                                "trend": (
                                    "bullish"
                                    if macd_data["histogram"].iloc[-1] > 0
                                    else "bearish"
                                ),
                            }

                    if "sma" in indicators:
                        sma_results = await technical_service.calculate_multiple_moving_averages_async(
                            df["close"], [20, 50], "SMA"
                        )
                        analysis_results["indicators"]["sma"] = {
                            period: float(values.iloc[-1]) if not values.empty else None
                            for period, values in sma_results.items()
                        }

                        # 골든크로스/데드크로스 신호 감지
                        if 20 in sma_results and 50 in sma_results:
                            sma_20 = sma_results[20]
                            sma_50 = sma_results[50]
                            if len(sma_20) >= 2 and len(sma_50) >= 2:
                                current_20 = sma_20.iloc[-1]
                                current_50 = sma_50.iloc[-1]
                                prev_20 = sma_20.iloc[-2]
                                prev_50 = sma_50.iloc[-2]

                                if prev_20 <= prev_50 and current_20 > current_50:
                                    analysis_results["indicators"][
                                        "cross_signal"
                                    ] = "golden_cross"
                                elif prev_20 >= prev_50 and current_20 < current_50:
                                    analysis_results["indicators"][
                                        "cross_signal"
                                    ] = "death_cross"

                    # WebSocket으로 브로드캐스트
                    await websocket_manager.broadcast_technical_analysis(
                        {"type": "technical_analysis_update", "data": analysis_results}
                    )

                    logger.debug("technical_analysis_streamed", symbol=symbol)

                except Exception as e:
                    logger.error(
                        "symbol_technical_analysis_streaming_failed",
                        symbol=symbol,
                        error=str(e),
                    )

            await asyncio.sleep(interval_seconds)

        except Exception as e:
            logger.error("technical_analysis_streaming_failed", error=str(e))
            await asyncio.sleep(interval_seconds)


@router.post("/alerts/subscribe", summary="기술적 분석 알림 구독")
@async_timed()
@memory_monitor
async def subscribe_to_technical_alerts(
    symbols: List[str] = Query(..., description="구독할 심볼 리스트"),
    alert_types: List[str] = Query(
        ["rsi_overbought", "rsi_oversold", "golden_cross", "death_cross"],
        description="구독할 알림 타입들",
    ),
) -> Dict[str, Any]:
    """
    기술적 분석 알림을 구독합니다.

    Args:
        symbols: 구독할 심볼 리스트
        alert_types: 구독할 알림 타입들

    Returns:
        구독 결과
    """
    try:
        logger.info(
            "technical_alerts_subscription_started",
            symbol_count=len(symbols),
            alert_types=alert_types,
        )

        # 백그라운드에서 알림 모니터링 시작
        import asyncio

        asyncio.create_task(monitor_technical_alerts(symbols, alert_types))

        return {
            "status": "subscribed",
            "symbols": symbols,
            "alert_types": alert_types,
            "subscribed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("technical_alerts_subscription_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"기술적 분석 알림 구독 실패: {str(e)}"
        )


async def monitor_technical_alerts(symbols: List[str], alert_types: List[str]):
    """
    기술적 분석 알림을 모니터링하는 백그라운드 작업
    """
    import asyncio

    # 이전 상태 저장용
    previous_states = {}

    while True:
        try:
            for symbol in symbols:
                try:
                    # 현재 기술적 지표 계산
                    async with price_service:
                        price_history = await price_service.fetch_price_history_async(
                            symbol, period="1mo", interval="1d"
                        )

                    if not price_history or not price_history.get("timestamps"):
                        continue

                    df = pd.DataFrame(
                        {
                            "timestamp": pd.to_datetime(
                                price_history["timestamps"], unit="s"
                            ),
                            "close": price_history["close"],
                        }
                    ).dropna()

                    if df.empty:
                        continue

                    current_state = {}
                    alerts_to_send = []

                    # RSI 알림 체크
                    if any(
                        alert in alert_types
                        for alert in ["rsi_overbought", "rsi_oversold"]
                    ):
                        rsi = await technical_service.calculate_rsi_async(df["close"])
                        if not rsi.empty:
                            current_rsi = rsi.iloc[-1]
                            current_state["rsi"] = current_rsi

                            prev_state = previous_states.get(symbol, {})
                            prev_rsi = prev_state.get("rsi")

                            # RSI 과매수 알림
                            if (
                                "rsi_overbought" in alert_types
                                and current_rsi > 70
                                and (prev_rsi is None or prev_rsi <= 70)
                            ):
                                alerts_to_send.append(
                                    {
                                        "type": "rsi_overbought",
                                        "symbol": symbol,
                                        "rsi_value": current_rsi,
                                        "message": f"{symbol} RSI 과매수 구간 진입 (RSI: {current_rsi:.2f})",
                                    }
                                )

                            # RSI 과매도 알림
                            if (
                                "rsi_oversold" in alert_types
                                and current_rsi < 30
                                and (prev_rsi is None or prev_rsi >= 30)
                            ):
                                alerts_to_send.append(
                                    {
                                        "type": "rsi_oversold",
                                        "symbol": symbol,
                                        "rsi_value": current_rsi,
                                        "message": f"{symbol} RSI 과매도 구간 진입 (RSI: {current_rsi:.2f})",
                                    }
                                )

                    # 이동평균선 크로스 알림 체크
                    if any(
                        alert in alert_types
                        for alert in ["golden_cross", "death_cross"]
                    ):
                        sma_results = await technical_service.calculate_multiple_moving_averages_async(
                            df["close"], [20, 50], "SMA"
                        )

                        if 20 in sma_results and 50 in sma_results:
                            sma_20 = sma_results[20]
                            sma_50 = sma_results[50]

                            if len(sma_20) >= 2 and len(sma_50) >= 2:
                                current_20 = sma_20.iloc[-1]
                                current_50 = sma_50.iloc[-1]
                                prev_20 = sma_20.iloc[-2]
                                prev_50 = sma_50.iloc[-2]

                                # 골든크로스 알림
                                if (
                                    "golden_cross" in alert_types
                                    and prev_20 <= prev_50
                                    and current_20 > current_50
                                ):
                                    alerts_to_send.append(
                                        {
                                            "type": "golden_cross",
                                            "symbol": symbol,
                                            "sma_20": current_20,
                                            "sma_50": current_50,
                                            "message": f"{symbol} 골든크로스 발생 (SMA20: {current_20:.2f}, SMA50: {current_50:.2f})",
                                        }
                                    )

                                # 데드크로스 알림
                                if (
                                    "death_cross" in alert_types
                                    and prev_20 >= prev_50
                                    and current_20 < current_50
                                ):
                                    alerts_to_send.append(
                                        {
                                            "type": "death_cross",
                                            "symbol": symbol,
                                            "sma_20": current_20,
                                            "sma_50": current_50,
                                            "message": f"{symbol} 데드크로스 발생 (SMA20: {current_20:.2f}, SMA50: {current_50:.2f})",
                                        }
                                    )

                    # 알림 전송
                    for alert in alerts_to_send:
                        await websocket_manager.broadcast_technical_alert(
                            {
                                "type": "technical_alert",
                                "data": alert,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )

                        logger.info(
                            "technical_alert_sent",
                            symbol=symbol,
                            alert_type=alert["type"],
                        )

                    # 현재 상태 저장
                    previous_states[symbol] = current_state

                except Exception as e:
                    logger.error(
                        "symbol_technical_alert_monitoring_failed",
                        symbol=symbol,
                        error=str(e),
                    )

            await asyncio.sleep(60)  # 1분마다 체크

        except Exception as e:
            logger.error("technical_alert_monitoring_failed", error=str(e))
            await asyncio.sleep(60)
