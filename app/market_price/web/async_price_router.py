"""
비동기 가격 데이터 API 라우터

가격 데이터 조회 및 모니터링을 위한 최적화된 비동기 엔드포인트들
"""

from fastapi import APIRouter, Query, BackgroundTasks, Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.market_price.service.async_price_service import AsyncPriceService
from app.market_price.dto.price_response import (
    CurrentPriceResponse,
    BatchPriceResponse,
    PriceHistoryResponse,
    BackgroundTaskResponse,
)
from app.common.config.api_metadata import common_responses
from app.common.dto.api_response import ApiResponse
from app.common.utils.response_helper import (
    success_response,
    not_found_response,
    handle_service_error,
)
from app.market_price.service.price_monitor_service import PriceMonitorService
from app.market_price.service.price_snapshot_service import PriceSnapshotService
from app.market_price.service.price_high_record_service import PriceHighRecordService
from app.common.utils.async_executor import async_timed
from app.common.utils.logging_config import get_logger
from app.common.utils.memory_cache import cache_result, get_cache_stats
from app.common.utils.memory_optimizer import memory_monitor
from app.common.utils.task_queue import TaskQueue
from app.common.services.background_tasks import (
    run_historical_data_collection_background,
)
from app.common.constants.symbol_names import SYMBOL_PRICE_MAP

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v2/market-price", tags=["Async Market Price"])

# 서비스 인스턴스
price_service = AsyncPriceService(max_workers=5, max_concurrency=10)
monitor_service = PriceMonitorService()
snapshot_service = PriceSnapshotService()
high_record_service = PriceHighRecordService()


@router.get(
    "/current/{symbol}",
    response_model=ApiResponse,
    summary="실시간 주식 가격 조회",
    description="""
    지정된 심볼의 현재 주식 가격을 실시간으로 조회합니다.
    
    **주요 기능:**
    - 실시간 가격 데이터 제공
    - 비동기 처리로 빠른 응답
    - 선택적 상세 정보 포함
    - 캐싱을 통한 성능 최적화
    
    **상세 정보 포함 시:**
    - 가격 요약 (고가, 저가 등)
    - 스냅샷 요약 (거래량 등)
    - 최고가 기록 정보
    
    **사용 사례:**
    - 실시간 주식 모니터링
    - 포트폴리오 가격 추적
    - 거래 의사결정 지원
    """,
    tags=["Market Data"],
    responses={
        **common_responses,
        200: {
            "description": "현재 가격을 성공적으로 조회했습니다.",
            "content": {
                "application/json": {
                    "example": {
                        "status": 200,
                        "message": "AAPL 현재 가격 조회가 완료되었습니다",
                        "data": {
                            "symbol": "AAPL",
                            "current_price": 175.43,
                            "timestamp": "2025-08-13T13:30:00Z",
                            "details": {
                                "price_summary": {
                                    "high": 176.50,
                                    "low": 174.20,
                                    "volume": 45678900
                                },
                                "snapshot_summary": {
                                    "open": 175.10,
                                    "previous_close": 174.85,
                                    "change": 0.58
                                }
                            }
                        }
                    }
                }
            },
        },
    },
)
@async_timed()
@memory_monitor
async def get_current_price_async(
    symbol: str = Path(
        ...,
        example="AAPL",
        description="조회할 주식 심볼 (예: AAPL, MSFT, GOOGL)",
        min_length=1,
        max_length=10,
    ),
    include_details: bool = Query(
        False, description="상세 정보 포함 여부 (가격 요약, 스냅샷, 최고가 기록)"
    ),
) -> ApiResponse:
    """
    지정된 심볼의 실시간 주식 가격을 조회합니다.

    고성능 비동기 처리를 통해 빠른 응답을 제공하며,
    선택적으로 상세한 가격 분석 정보를 포함할 수 있습니다.
    """
    try:
        logger.info("current_price_query_started", symbol=symbol)

        async with price_service:
            current_price = await price_service.fetch_price_async(symbol)

        if current_price is None:
            not_found_response(f"심볼 {symbol}의 가격 데이터를 찾을 수 없습니다")

        details = None
        if include_details:
            # 상세 정보 추가 (캐싱된 데이터 활용)
            price_summary = monitor_service.get_price_summary(symbol)
            snapshot_summary = snapshot_service.get_snapshot_summary(symbol)
            high_record_summary = high_record_service.get_high_record_summary(symbol)

            details = {
                "price_summary": price_summary,
                "snapshot_summary": snapshot_summary,
                "high_record_summary": high_record_summary,
            }

        logger.info("current_price_query_completed", symbol=symbol, price=current_price)

        response_data = {
            "symbol": symbol,
            "current_price": current_price,
            "timestamp": datetime.now().isoformat(),
            "details": details,
        }

        return success_response(
            data=response_data,
            message=f"{symbol} 현재 가격 조회가 완료되었습니다"
        )

    except Exception as e:
        logger.error("current_price_query_failed", symbol=symbol, error=str(e))
        handle_service_error(e, f"{symbol} 가격 조회 실패")


@router.post("/batch/current", summary="배치 현재 가격 조회")
@async_timed()
@memory_monitor
async def get_batch_current_prices_async(
    symbols: List[str] = Query(..., description="조회할 심볼 리스트"),
    batch_size: int = Query(10, description="배치 크기"),
) -> ApiResponse:
    """
    여러 심볼의 현재 가격을 배치로 비동기 조회합니다.

    Args:
        symbols: 조회할 심볼 리스트
        batch_size: 배치 크기

    Returns:
        배치 가격 조회 결과
    """
    try:
        logger.info("batch_current_price_query_started", symbol_count=len(symbols))

        async with price_service:
            results = await price_service.fetch_multiple_prices_async(
                symbols, batch_size=batch_size
            )

        successful_count = sum(1 for r in results.values() if r is not None)

        logger.info(
            "batch_current_price_query_completed",
            symbol_count=len(symbols),
            successful_count=successful_count,
        )

        response_data = {
            "total_symbols": len(symbols),
            "successful_count": successful_count,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }

        return success_response(
            data=response_data,
            message=f"배치 가격 조회 완료 ({successful_count}/{len(symbols)} 성공)"
        )

    except Exception as e:
        logger.error("batch_current_price_query_failed", error=str(e))
        handle_service_error(e, "배치 가격 조회 실패")


@router.get("/history/{symbol}", summary="가격 히스토리 조회")
@async_timed()
@memory_monitor
async def get_price_history_async(
    symbol: str,
    period: str = Query("1mo", description="조회 기간"),
    interval: str = Query("1d", description="데이터 간격"),
) -> ApiResponse:
    """
    심볼의 가격 히스토리를 비동기로 조회합니다.

    Args:
        symbol: 조회할 심볼
        period: 조회 기간
        interval: 데이터 간격

    Returns:
        가격 히스토리 데이터
    """
    try:
        logger.info("price_history_query_started", symbol=symbol, period=period)

        async with price_service:
            history = await price_service.fetch_price_history_async(
                symbol, period=period, interval=interval
            )

        if not history or not history.get("timestamps"):
            not_found_response(f"심볼 {symbol}의 히스토리 데이터를 찾을 수 없습니다")

        result = {
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "data_points": len(history["timestamps"]),
            "history": history,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(
            "price_history_query_completed",
            symbol=symbol,
            data_points=len(history["timestamps"]),
        )
        
        return success_response(
            data=result,
            message=f"{symbol} 가격 히스토리 조회 완료 ({len(history['timestamps'])}개 데이터 포인트)"
        )

    except Exception as e:
        logger.error("price_history_query_failed", symbol=symbol, error=str(e))
        handle_service_error(e, f"{symbol} 가격 히스토리 조회 실패")


@router.post("/monitor/batch", summary="배치 가격 모니터링")
@async_timed()
@memory_monitor
async def monitor_batch_prices_async(
    symbols: List[str] = Query(..., description="모니터링할 심볼 리스트"),
    batch_size: int = Query(5, description="배치 크기"),
) -> Dict[str, Any]:
    """
    여러 심볼의 가격을 배치로 모니터링합니다.

    Args:
        symbols: 모니터링할 심볼 리스트
        batch_size: 배치 크기

    Returns:
        배치 모니터링 결과
    """
    try:
        logger.info("batch_price_monitoring_started", symbol_count=len(symbols))

        # 배치 모니터링 실행
        monitor_service.check_multiple_prices_batch(symbols, batch_size)

        # 모니터링 결과 요약
        results = {}
        for symbol in symbols:
            try:
                summary = monitor_service.get_price_summary(symbol)
                results[symbol] = summary
            except Exception as e:
                results[symbol] = {"error": str(e)}

        logger.info("batch_price_monitoring_completed", symbol_count=len(symbols))

        return {
            "monitored_symbols": len(symbols),
            "batch_size": batch_size,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("batch_price_monitoring_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"배치 가격 모니터링 실패: {str(e)}"
        )


@router.post("/data-collection/background", summary="백그라운드 데이터 수집")
@async_timed()
@memory_monitor
async def queue_background_data_collection(
    background_tasks: BackgroundTasks,
    symbols: List[str] = Query(..., description="수집할 심볼 리스트"),
    period: str = Query("1y", description="수집 기간"),
) -> Dict[str, Any]:
    """
    대량 히스토리컬 데이터 수집을 백그라운드 큐에 추가합니다.

    Args:
        symbols: 수집할 심볼 리스트
        period: 수집 기간

    Returns:
        작업 큐잉 결과
    """
    try:
        logger.info(
            "background_data_collection_queuing_started",
            symbol_count=len(symbols),
            period=period,
        )

        # 작업 큐에 백그라운드 데이터 수집 작업 추가
        task_queue = TaskQueue()
        task_id = await task_queue.enqueue_task(
            run_historical_data_collection_background, symbols=symbols, period=period
        )

        logger.info(
            "background_data_collection_queued",
            task_id=task_id,
            symbol_count=len(symbols),
        )

        return {
            "status": "queued",
            "task_id": task_id,
            "symbols": symbols,
            "period": period,
            "estimated_completion": "10-30 minutes",
            "queued_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("background_data_collection_queuing_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"백그라운드 데이터 수집 큐잉 실패: {str(e)}"
        )


@router.get("/snapshots/summary", summary="스냅샷 요약 조회")
@async_timed()
@memory_monitor
async def get_snapshots_summary_async(
    symbols: List[str] = Query(None, description="조회할 심볼 리스트"),
    batch_size: int = Query(20, description="배치 크기"),
) -> Dict[str, Any]:
    """
    스냅샷 데이터 요약을 배치로 조회합니다.

    Args:
        symbols: 조회할 심볼 리스트 (None이면 전체)
        batch_size: 배치 크기

    Returns:
        스냅샷 요약 정보
    """
    try:
        if not symbols:
            symbols = list(SYMBOL_PRICE_MAP.keys())[:10]  # 기본 10개

        logger.info("snapshots_summary_query_started", symbol_count=len(symbols))

        # 배치로 스냅샷 요약 조회
        results = snapshot_service.get_multiple_snapshots_batch(symbols, batch_size)

        logger.info("snapshots_summary_query_completed", symbol_count=len(symbols))

        return {
            "total_symbols": len(symbols),
            "batch_size": batch_size,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("snapshots_summary_query_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"스냅샷 요약 조회 실패: {str(e)}")


@router.get("/high-records/summary", summary="최고가 기록 요약 조회")
@async_timed()
@memory_monitor
async def get_high_records_summary_async(
    symbols: List[str] = Query(None, description="조회할 심볼 리스트"),
    batch_size: int = Query(20, description="배치 크기"),
) -> Dict[str, Any]:
    """
    최고가 기록 요약을 배치로 조회합니다.

    Args:
        symbols: 조회할 심볼 리스트 (None이면 전체)
        batch_size: 배치 크기

    Returns:
        최고가 기록 요약 정보
    """
    try:
        if not symbols:
            symbols = list(SYMBOL_PRICE_MAP.keys())[:10]  # 기본 10개

        logger.info("high_records_summary_query_started", symbol_count=len(symbols))

        # 배치로 최고가 기록 요약 조회
        results = high_record_service.get_multiple_high_records_batch(
            symbols, batch_size
        )

        logger.info("high_records_summary_query_completed", symbol_count=len(symbols))

        return {
            "total_symbols": len(symbols),
            "batch_size": batch_size,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("high_records_summary_query_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"최고가 기록 요약 조회 실패: {str(e)}"
        )


@router.get("/cache/stats", summary="가격 데이터 캐시 통계")
@memory_monitor
async def get_price_cache_statistics() -> Dict[str, Any]:
    """
    가격 데이터 관련 캐시 통계를 조회합니다.

    Returns:
        캐시 통계 정보
    """
    try:
        from app.common.utils.memory_cache import get_cache_stats

        # 가격 데이터 관련 캐시 통계 조회
        cache_stats = get_cache_stats("price_data")

        return {
            "cache_name": "price_data",
            "statistics": cache_stats,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("price_cache_statistics_query_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"가격 캐시 통계 조회 실패: {str(e)}"
        )
