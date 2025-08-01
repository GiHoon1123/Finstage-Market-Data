"""
백그라운드 작업 서비스

무거운 작업들을 백그라운드에서 비동기로 처리하는 서비스들입니다.
작업 큐를 활용하여 시스템 성능에 영향을 주지 않고 처리합니다.
"""

import asyncio
import time
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.common.utils.task_queue import task, TaskPriority
from app.common.utils.logging_config import get_logger
from app.common.utils.memory_optimizer import optimize_dataframe_memory, memory_monitor

logger = get_logger(__name__)


# =============================================================================
# 데이터 처리 작업들
# =============================================================================


@task(priority=TaskPriority.HIGH, max_retries=2, timeout=300.0)
async def process_large_dataset(symbol: str, period: str = "1y") -> Dict[str, Any]:
    """
    대용량 데이터셋 처리 작업

    Args:
        symbol: 처리할 심볼
        period: 데이터 기간

    Returns:
        처리 결과
    """
    logger.info("large_dataset_processing_started", symbol=symbol, period=period)

    try:
        # 시뮬레이션: 대용량 데이터 생성
        import numpy as np

        # 1년치 일봉 데이터 시뮬레이션 (약 250개 데이터)
        dates = pd.date_range(start="2023-01-01", end="2023-12-31", freq="B")

        # 가격 데이터 생성 (랜덤 워크)
        np.random.seed(hash(symbol) % 1000)  # 심볼별 일관된 데이터
        returns = np.random.normal(0.001, 0.02, len(dates))  # 일일 수익률
        prices = 100 * np.exp(np.cumsum(returns))  # 누적 가격

        # DataFrame 생성
        df = pd.DataFrame(
            {
                "date": dates,
                "open": prices * np.random.uniform(0.99, 1.01, len(dates)),
                "high": prices * np.random.uniform(1.00, 1.05, len(dates)),
                "low": prices * np.random.uniform(0.95, 1.00, len(dates)),
                "close": prices,
                "volume": np.random.randint(1000000, 10000000, len(dates)),
            }
        )

        # 메모리 최적화 적용
        df = optimize_dataframe_memory(df)

        # 복잡한 계산 시뮬레이션
        await asyncio.sleep(2)  # 2초 처리 시간 시뮬레이션

        # 기술적 지표 계산
        df["sma_20"] = df["close"].rolling(20).mean()
        df["sma_50"] = df["close"].rolling(50).mean()
        df["rsi"] = calculate_rsi(df["close"])

        # 결과 통계
        result = {
            "symbol": symbol,
            "period": period,
            "data_points": len(df),
            "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
            "price_range": {
                "min": float(df["close"].min()),
                "max": float(df["close"].max()),
                "current": float(df["close"].iloc[-1]),
            },
            "technical_indicators": {
                "sma_20": (
                    float(df["sma_20"].iloc[-1])
                    if not df["sma_20"].isna().iloc[-1]
                    else None
                ),
                "sma_50": (
                    float(df["sma_50"].iloc[-1])
                    if not df["sma_50"].isna().iloc[-1]
                    else None
                ),
                "rsi": (
                    float(df["rsi"].iloc[-1]) if not df["rsi"].isna().iloc[-1] else None
                ),
            },
            "processed_at": datetime.now().isoformat(),
        }

        logger.info(
            "large_dataset_processing_completed",
            symbol=symbol,
            data_points=len(df),
            memory_usage_mb=result["memory_usage_mb"],
        )

        return result

    except Exception as e:
        logger.error("large_dataset_processing_failed", symbol=symbol, error=str(e))
        raise


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI 계산 (동기 함수)"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


@task(priority=TaskPriority.NORMAL, max_retries=3, timeout=180.0)
def generate_daily_report(symbols: List[str], date: str = None) -> Dict[str, Any]:
    """
    일일 리포트 생성 작업 (동기 함수)

    Args:
        symbols: 리포트 생성할 심볼들
        date: 리포트 날짜 (기본값: 오늘)

    Returns:
        리포트 데이터
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    logger.info("daily_report_generation_started", symbol_count=len(symbols), date=date)

    try:
        report_data = {
            "report_date": date,
            "generated_at": datetime.now().isoformat(),
            "symbols": symbols,
            "summary": {"total_symbols": len(symbols), "processing_time_seconds": 0},
            "symbol_data": {},
        }

        start_time = time.time()

        # 각 심볼별 데이터 처리
        for symbol in symbols:
            # 시뮬레이션: 심볼별 데이터 생성
            import random

            random.seed(hash(f"{symbol}_{date}"))

            symbol_data = {
                "symbol": symbol,
                "current_price": round(random.uniform(50, 500), 2),
                "change_percent": round(random.uniform(-5, 5), 2),
                "volume": random.randint(1000000, 50000000),
                "market_cap": random.randint(1000000000, 1000000000000),
                "pe_ratio": round(random.uniform(10, 30), 2),
                "technical_score": random.randint(1, 100),
            }

            report_data["symbol_data"][symbol] = symbol_data

            # 처리 시간 시뮬레이션
            time.sleep(0.1)

        processing_time = time.time() - start_time
        report_data["summary"]["processing_time_seconds"] = round(processing_time, 2)

        logger.info(
            "daily_report_generation_completed",
            symbol_count=len(symbols),
            processing_time=processing_time,
        )

        return report_data

    except Exception as e:
        logger.error("daily_report_generation_failed", error=str(e))
        raise


# =============================================================================
# 알림 및 통신 작업들
# =============================================================================


@task(priority=TaskPriority.HIGH, max_retries=5, retry_delay=2.0)
async def send_bulk_notifications(
    notifications: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    대량 알림 전송 작업

    Args:
        notifications: 전송할 알림 리스트

    Returns:
        전송 결과
    """
    logger.info("bulk_notifications_started", notification_count=len(notifications))

    try:
        results = {
            "total_notifications": len(notifications),
            "successful_sends": 0,
            "failed_sends": 0,
            "send_details": [],
            "sent_at": datetime.now().isoformat(),
        }

        # 각 알림 전송 시뮬레이션
        for i, notification in enumerate(notifications):
            try:
                # 전송 시뮬레이션 (실제로는 텔레그램, 이메일 등)
                await asyncio.sleep(0.1)  # 네트워크 지연 시뮬레이션

                # 90% 성공률 시뮬레이션
                import random

                if random.random() < 0.9:
                    results["successful_sends"] += 1
                    results["send_details"].append(
                        {
                            "index": i,
                            "status": "success",
                            "recipient": notification.get("recipient", "unknown"),
                            "message_type": notification.get("type", "unknown"),
                        }
                    )
                else:
                    results["failed_sends"] += 1
                    results["send_details"].append(
                        {
                            "index": i,
                            "status": "failed",
                            "recipient": notification.get("recipient", "unknown"),
                            "error": "Network timeout",
                        }
                    )

            except Exception as e:
                results["failed_sends"] += 1
                results["send_details"].append(
                    {"index": i, "status": "error", "error": str(e)}
                )

        success_rate = (results["successful_sends"] / len(notifications)) * 100

        logger.info(
            "bulk_notifications_completed",
            total=len(notifications),
            successful=results["successful_sends"],
            failed=results["failed_sends"],
            success_rate=success_rate,
        )

        return results

    except Exception as e:
        logger.error("bulk_notifications_failed", error=str(e))
        raise


# =============================================================================
# 데이터 정리 및 유지보수 작업들
# =============================================================================


@task(priority=TaskPriority.LOW, max_retries=1, timeout=600.0)
def cleanup_old_data(days_to_keep: int = 30) -> Dict[str, Any]:
    """
    오래된 데이터 정리 작업

    Args:
        days_to_keep: 보관할 일수

    Returns:
        정리 결과
    """
    logger.info("data_cleanup_started", days_to_keep=days_to_keep)

    try:
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        # 시뮬레이션: 데이터 정리
        cleanup_results = {
            "cutoff_date": cutoff_date.isoformat(),
            "cleaned_tables": [],
            "total_records_deleted": 0,
            "space_freed_mb": 0,
            "cleanup_time_seconds": 0,
        }

        start_time = time.time()

        # 테이블별 정리 시뮬레이션
        tables_to_clean = [
            "price_history",
            "technical_analysis",
            "alerts",
            "user_sessions",
            "api_logs",
        ]

        for table in tables_to_clean:
            # 정리 시뮬레이션
            import random

            records_deleted = random.randint(100, 10000)
            space_freed = random.randint(1, 100)

            cleanup_results["cleaned_tables"].append(
                {
                    "table_name": table,
                    "records_deleted": records_deleted,
                    "space_freed_mb": space_freed,
                }
            )

            cleanup_results["total_records_deleted"] += records_deleted
            cleanup_results["space_freed_mb"] += space_freed

            # 처리 시간 시뮬레이션
            time.sleep(0.5)

        cleanup_results["cleanup_time_seconds"] = round(time.time() - start_time, 2)

        logger.info(
            "data_cleanup_completed",
            records_deleted=cleanup_results["total_records_deleted"],
            space_freed_mb=cleanup_results["space_freed_mb"],
        )

        return cleanup_results

    except Exception as e:
        logger.error("data_cleanup_failed", error=str(e))
        raise


# =============================================================================
# 분석 및 ML 작업들
# =============================================================================


@task(priority=TaskPriority.NORMAL, max_retries=2, timeout=900.0)
async def run_market_analysis(analysis_type: str = "comprehensive") -> Dict[str, Any]:
    """
    시장 분석 작업

    Args:
        analysis_type: 분석 유형

    Returns:
        분석 결과
    """
    logger.info("market_analysis_started", analysis_type=analysis_type)

    try:
        analysis_results = {
            "analysis_type": analysis_type,
            "started_at": datetime.now().isoformat(),
            "market_sentiment": {},
            "sector_analysis": {},
            "predictions": {},
            "risk_assessment": {},
        }

        # 분석 단계별 처리
        stages = [
            ("market_sentiment", "시장 심리 분석"),
            ("sector_analysis", "섹터별 분석"),
            ("predictions", "예측 모델 실행"),
            ("risk_assessment", "리스크 평가"),
        ]

        for stage_key, stage_name in stages:
            logger.info("analysis_stage_started", stage=stage_name)

            # 각 단계별 처리 시뮬레이션
            await asyncio.sleep(2)  # 처리 시간 시뮬레이션

            # 결과 생성
            import random

            stage_result = {
                "stage": stage_name,
                "confidence_score": round(random.uniform(0.6, 0.95), 3),
                "key_findings": [
                    f"{stage_name} 주요 발견사항 1",
                    f"{stage_name} 주요 발견사항 2",
                ],
                "processed_at": datetime.now().isoformat(),
            }

            analysis_results[stage_key] = stage_result

            logger.info("analysis_stage_completed", stage=stage_name)

        analysis_results["completed_at"] = datetime.now().isoformat()
        analysis_results["total_processing_time"] = "약 8초"

        logger.info("market_analysis_completed", analysis_type=analysis_type)

        return analysis_results

    except Exception as e:
        logger.error("market_analysis_failed", error=str(e))
        raise


# =============================================================================
# 유틸리티 함수들
# =============================================================================


@memory_monitor(threshold_mb=100.0)
async def submit_background_task(
    task_name: str, *args, priority: TaskPriority = TaskPriority.NORMAL, **kwargs
) -> str:
    """
    백그라운드 작업 제출 헬퍼 함수

    Args:
        task_name: 작업 함수 이름
        priority: 작업 우선순위
        *args, **kwargs: 작업 함수 인자들

    Returns:
        작업 ID
    """
    from app.common.utils.task_queue import task_queue

    # 함수 이름 매핑
    function_mapping = {
        "process_dataset": "app.common.services.background_tasks.process_large_dataset",
        "generate_report": "app.common.services.background_tasks.generate_daily_report",
        "send_notifications": "app.common.services.background_tasks.send_bulk_notifications",
        "cleanup_data": "app.common.services.background_tasks.cleanup_old_data",
        "market_analysis": "app.common.services.background_tasks.run_market_analysis",
    }

    func_name = function_mapping.get(task_name)
    if not func_name:
        raise ValueError(f"알 수 없는 작업: {task_name}")

    task_id = await task_queue.submit_task(
        func_name, *args, priority=priority, **kwargs
    )

    logger.info(
        "background_task_submitted",
        task_name=task_name,
        task_id=task_id,
        priority=priority.name,
    )

    return task_id


async def get_task_progress(task_id: str) -> Dict[str, Any]:
    """
    작업 진행 상황 조회

    Args:
        task_id: 작업 ID

    Returns:
        작업 상태 정보
    """
    from app.common.utils.task_queue import task_queue

    result = task_queue.get_task_result(task_id)

    if not result:
        return {"error": "작업을 찾을 수 없습니다"}

    progress_info = {
        "task_id": task_id,
        "status": result.status.value,
        "started_at": result.started_at.isoformat() if result.started_at else None,
        "completed_at": (
            result.completed_at.isoformat() if result.completed_at else None
        ),
        "execution_time": result.execution_time,
        "retry_count": result.retry_count,
        "worker_id": result.worker_id,
        "has_result": result.result is not None,
        "has_error": result.error is not None,
    }

    # 에러 정보 포함 (있는 경우)
    if result.error:
        progress_info["error"] = result.error

    return progress_info


# =============================================================================
# 스케줄러 작업들을 백그라운드로 이전
# =============================================================================


@task(priority=TaskPriority.NORMAL, max_retries=1, timeout=600.0)
@memory_monitor
async def run_daily_comprehensive_report_background(
    symbols: List[str] = None,
) -> Dict[str, Any]:
    """
    일일 종합 리포트 생성을 백그라운드 작업으로 처리

    Args:
        symbols: 분석할 심볼 리스트

    Returns:
        리포트 생성 결과
    """
    logger.info(
        "daily_comprehensive_report_background_started",
        symbol_count=len(symbols) if symbols else 0,
    )

    try:
        # 실제 리포트 생성 로직 (기존 서비스 활용)
        from app.technical_analysis.service.daily_comprehensive_report_service import (
            DailyComprehensiveReportService,
        )

        service = DailyComprehensiveReportService()

        if not symbols:
            symbols = ["^IXIC", "^GSPC", "^DJI"]  # 기본 지수들

        results = {}
        for symbol in symbols:
            try:
                result = service.generate_comprehensive_report(symbol)
                results[symbol] = {"success": True, "data": result}
                logger.info("symbol_report_completed", symbol=symbol)
            except Exception as e:
                results[symbol] = {"success": False, "error": str(e)}
                logger.error("symbol_report_failed", symbol=symbol, error=str(e))

        logger.info(
            "daily_comprehensive_report_background_completed",
            results_count=len(results),
        )
        return {
            "task": "daily_comprehensive_report",
            "status": "completed",
            "results": results,
            "processed_symbols": len(symbols),
            "completed_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("daily_comprehensive_report_background_failed", error=str(e))
        return {
            "task": "daily_comprehensive_report",
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat(),
        }


@task(priority=TaskPriority.LOW, max_retries=1, timeout=1800.0)
@memory_monitor
async def run_historical_data_collection_background(
    symbols: List[str], period: str = "1y"
) -> Dict[str, Any]:
    """
    대량 히스토리컬 데이터 수집을 백그라운드 작업으로 처리

    Args:
        symbols: 수집할 심볼 리스트
        period: 데이터 기간

    Returns:
        데이터 수집 결과
    """
    logger.info(
        "historical_data_collection_background_started",
        symbol_count=len(symbols),
        period=period,
    )

    try:
        from app.common.infra.client.yahoo_price_client import YahooPriceClient

        client = YahooPriceClient()
        results = {}

        # 배치 처리로 메모리 효율성 향상
        batch_size = 10
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i : i + batch_size]

            for symbol in batch:
                try:
                    # 히스토리컬 데이터 수집
                    data = client.get_daily_data(symbol, period=period)

                    if data is not None and not data.empty:
                        # DataFrame 메모리 최적화
                        data = optimize_dataframe_memory(data)

                        results[symbol] = {
                            "success": True,
                            "data_points": len(data),
                            "date_range": {
                                "start": data.index.min().isoformat(),
                                "end": data.index.max().isoformat(),
                            },
                        }
                    else:
                        results[symbol] = {
                            "success": False,
                            "error": "No data available",
                        }

                    logger.info(
                        "symbol_data_collected",
                        symbol=symbol,
                        data_points=len(data) if data is not None else 0,
                    )

                except Exception as e:
                    results[symbol] = {"success": False, "error": str(e)}
                    logger.error(
                        "symbol_data_collection_failed", symbol=symbol, error=str(e)
                    )

            # 배치 처리 후 메모리 정리
            del batch

            # 배치 간 잠시 대기 (API 레이트 리밋 고려)
            await asyncio.sleep(1)

        logger.info(
            "historical_data_collection_background_completed",
            processed_symbols=len(symbols),
        )

        return {
            "task": "historical_data_collection",
            "status": "completed",
            "results": results,
            "processed_symbols": len(symbols),
            "period": period,
            "completed_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("historical_data_collection_background_failed", error=str(e))
        return {
            "task": "historical_data_collection",
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat(),
        }


@task(priority=TaskPriority.NORMAL, max_retries=2, timeout=900.0)
@memory_monitor
async def run_technical_analysis_batch_background(
    symbols: List[str], analysis_types: List[str] = None
) -> Dict[str, Any]:
    """
    기술적 분석 배치 작업을 백그라운드로 처리

    Args:
        symbols: 분석할 심볼 리스트
        analysis_types: 분석 타입 리스트 (기본값: 모든 분석)

    Returns:
        분석 결과
    """
    logger.info(
        "technical_analysis_batch_background_started", symbol_count=len(symbols)
    )

    try:
        from app.technical_analysis.service.technical_indicator_service import (
            TechnicalIndicatorService,
        )
        from app.technical_analysis.service.signal_generator_service import (
            SignalGeneratorService,
        )

        indicator_service = TechnicalIndicatorService()
        signal_service = SignalGeneratorService()

        if not analysis_types:
            analysis_types = ["indicators", "signals"]

        results = {}

        # 우선순위 기반 처리 (중요한 지수부터)
        priority_symbols = ["^IXIC", "^GSPC", "^DJI"]
        other_symbols = [s for s in symbols if s not in priority_symbols]
        ordered_symbols = priority_symbols + other_symbols

        for symbol in ordered_symbols:
            try:
                symbol_results = {}

                # 기술적 지표 분석
                if "indicators" in analysis_types:
                    indicators = indicator_service.get_all_indicators(symbol)
                    symbol_results["indicators"] = {"success": True, "data": indicators}

                # 신호 생성 분석
                if "signals" in analysis_types:
                    from datetime import date, timedelta

                    end_date = date.today()
                    start_date = end_date - timedelta(days=30)  # 최근 30일

                    signals = signal_service.generate_symbol_signals(
                        symbol, start_date, end_date
                    )
                    symbol_results["signals"] = {"success": True, "data": signals}

                results[symbol] = symbol_results
                logger.info("symbol_technical_analysis_completed", symbol=symbol)

            except Exception as e:
                results[symbol] = {"success": False, "error": str(e)}
                logger.error(
                    "symbol_technical_analysis_failed", symbol=symbol, error=str(e)
                )

        logger.info(
            "technical_analysis_batch_background_completed",
            processed_symbols=len(symbols),
        )

        return {
            "task": "technical_analysis_batch",
            "status": "completed",
            "results": results,
            "processed_symbols": len(symbols),
            "analysis_types": analysis_types,
            "completed_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("technical_analysis_batch_background_failed", error=str(e))
        return {
            "task": "technical_analysis_batch",
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat(),
        }
