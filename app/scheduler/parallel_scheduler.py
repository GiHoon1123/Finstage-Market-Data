"""
병렬 처리 기능이 추가된 스케줄러 러너
"""

import asyncio
from apscheduler.schedulers.background import BackgroundScheduler

# 유틸리티 imports
from app.common.utils.parallel_executor import ParallelExecutor, measure_execution_time
from app.common.utils.logging_config import get_logger
from app.common.utils.memory_optimizer import memory_monitor, auto_memory_optimization
from app.common.utils.memory_utils import optimize_memory
from app.common.utils.db_session_manager import session_scope
from app.common.utils.task_queue import TaskQueue

# 예외 처리 imports
from app.common.exceptions.handlers import handle_scheduler_errors, safe_execute
from app.common.exceptions.base import SchedulerError, ErrorCode

# 상수 imports
from app.common.constants.symbol_names import (
    INDEX_SYMBOLS,
    FUTURES_SYMBOLS,
    STOCK_SYMBOLS,
    SYMBOL_PRICE_MAP,
)
from app.common.constants.rss_feeds import (
    INVESTING_ECONOMIC_SYMBOLS,
    INVESTING_MARKET_SYMBOLS,
)

# 서비스 imports
from app.news_crawler.service.investing_news_crawler import InvestingNewsCrawler
from app.news_crawler.service.yahoo_news_crawler import YahooNewsCrawler
from app.market_price.service.price_high_record_service import PriceHighRecordService
from app.market_price.service.price_snapshot_service import PriceSnapshotService
from app.market_price.service.price_monitor_service import PriceMonitorService
from app.technical_analysis.service.async_technical_indicator_service import (
    AsyncTechnicalIndicatorService,
)
from app.market_price.service.async_price_service import AsyncPriceService
from app.technical_analysis.service.daily_comprehensive_report_service import (
    DailyComprehensiveReportService,
)
from app.common.services.background_tasks import (
    run_daily_comprehensive_report_background,
    run_historical_data_collection_background,
    run_technical_analysis_batch_background,
)
from app.scheduler.scheduler_runner import (
    run_daily_index_analysis,
    run_outcome_tracking_update,
    initialize_recent_signals_tracking,
    run_pattern_discovery,
)

logger = get_logger("parallel_scheduler")


# 병렬 실행기 인스턴스 생성 (max_workers 감소로 DB 연결 부하 감소)
executor = ParallelExecutor(max_workers=2)  # 3 → 2로 더 감소


@measure_execution_time
@handle_scheduler_errors(reraise=False, return_on_error=None)
@auto_memory_optimization(threshold_percent=80.0)
@memory_monitor()
def run_integrated_news_crawling_parallel():
    """통합 뉴스 크롤링 (경제 뉴스 + 지수 뉴스)"""
    logger.info(
        "integrated_news_crawling_started",
        sources=["investing_economic", "yahoo_index"],
    )

    # 1. Investing 경제 뉴스 크롤링
    def process_investing_symbol(symbol):
        logger.debug("processing_symbol", source="investing_economic", symbol=symbol)
        crawler = InvestingNewsCrawler(symbol)
        result = crawler.process_all()
        return result

    investing_results = executor.run_symbol_tasks_parallel(
        process_investing_symbol, INVESTING_ECONOMIC_SYMBOLS, delay=0.5
    )

    investing_success = sum(1 for r in investing_results if r is not None)
    logger.info(
        "news_crawling_completed",
        source="investing_economic",
        success_count=investing_success,
        total_count=len(INVESTING_ECONOMIC_SYMBOLS),
        success_rate=investing_success / len(INVESTING_ECONOMIC_SYMBOLS),
    )

    # 2. Yahoo 지수 뉴스 크롤링
    def process_yahoo_symbol(symbol):
        logger.debug("processing_symbol", source="yahoo_index", symbol=symbol)
        crawler = YahooNewsCrawler(symbol)
        result = crawler.process_all()
        return result

    yahoo_results = executor.run_symbol_tasks_parallel(
        process_yahoo_symbol, INDEX_SYMBOLS, delay=0.5
    )

    yahoo_success = sum(1 for r in yahoo_results if r is not None)
    logger.info(
        "news_crawling_completed",
        source="yahoo_index",
        success_count=yahoo_success,
        total_count=len(INDEX_SYMBOLS),
        success_rate=yahoo_success / len(INDEX_SYMBOLS),
    )

    total_success = investing_success + yahoo_success
    total_symbols = len(INVESTING_ECONOMIC_SYMBOLS) + len(INDEX_SYMBOLS)
    logger.info(
        "integrated_news_crawling_completed",
        total_success=total_success,
        total_symbols=total_symbols,
        overall_success_rate=total_success / total_symbols,
    )


@measure_execution_time
@handle_scheduler_errors(reraise=False, return_on_error=None)
@memory_monitor()
def run_investing_market_news_parallel():
    """Investing 시장 뉴스 크롤링 (병렬)"""
    logger.info("news_crawling_started", source="investing_market")

    def process_symbol(symbol):
        logger.debug("processing_symbol", source="investing_market", symbol=symbol)
        crawler = InvestingNewsCrawler(symbol)
        result = crawler.process_all()
        return result

    # 병렬 실행 (API 제한 고려하여 약간의 지연 추가)
    results = executor.run_symbol_tasks_parallel(
        process_symbol, INVESTING_MARKET_SYMBOLS, delay=0.5
    )

    success_count = sum(1 for r in results if r is not None)
    logger.info(
        "news_crawling_completed",
        source="investing_market",
        success_count=success_count,
        total_count=len(INVESTING_MARKET_SYMBOLS),
        success_rate=success_count / len(INVESTING_MARKET_SYMBOLS),
    )


@measure_execution_time
@handle_scheduler_errors(reraise=False, return_on_error=None)
@memory_monitor()
def run_yahoo_futures_news_parallel():
    """Yahoo 선물 뉴스 크롤링 (병렬)"""
    logger.info("news_crawling_started", source="yahoo_futures")

    def process_symbol(symbol):
        logger.debug("processing_symbol", source="yahoo_futures", symbol=symbol)
        crawler = YahooNewsCrawler(symbol)
        result = crawler.process_all()
        return result

    # 병렬 실행 (API 제한 고려하여 약간의 지연 추가)
    results = executor.run_symbol_tasks_parallel(
        process_symbol, FUTURES_SYMBOLS, delay=0.5
    )

    success_count = sum(1 for r in results if r is not None)
    logger.info(
        "news_crawling_completed",
        source="yahoo_futures",
        success_count=success_count,
        total_count=len(FUTURES_SYMBOLS),
        success_rate=success_count / len(FUTURES_SYMBOLS),
    )


# 기존 개별 뉴스 크롤링 함수들은 통합 함수로 대체됨
# run_investing_economic_news_parallel() -> run_integrated_news_crawling_parallel()
# run_yahoo_index_news_parallel() -> run_integrated_news_crawling_parallel()


@measure_execution_time
@handle_scheduler_errors(reraise=False, return_on_error=None)
@memory_monitor()
def run_yahoo_stock_news_parallel():
    """Yahoo 종목 뉴스 크롤링 (병렬)"""
    logger.info("news_crawling_started", source="yahoo_stocks")

    def process_symbol(symbol):
        logger.debug("processing_symbol", source="yahoo_stocks", symbol=symbol)
        crawler = YahooNewsCrawler(symbol)
        result = crawler.process_all()
        return result

    # 병렬 실행 (API 제한 고려하여 약간의 지연 추가)
    results = executor.run_symbol_tasks_parallel(
        process_symbol, STOCK_SYMBOLS, delay=0.5
    )

    success_count = sum(1 for r in results if r is not None)
    logger.info(
        "news_crawling_completed",
        source="yahoo_stocks",
        success_count=success_count,
        total_count=len(STOCK_SYMBOLS),
        success_rate=success_count / len(STOCK_SYMBOLS),
    )


@measure_execution_time
@handle_scheduler_errors(reraise=False, return_on_error=None)
@memory_monitor()
def run_high_price_update_job_parallel():
    """상장 후 최고가 갱신 (병렬)"""
    logger.info("high_price_update_started")

    def update_high_price(symbol):
        return safe_execute(
            lambda: _update_high_price_for_symbol(symbol),
            default_return=None,
            log_errors=True,
        )

    def _update_high_price_for_symbol(symbol):
        service = PriceHighRecordService()
        result = service.update_all_time_high(symbol)
        # 서비스 사용 후 세션 정리
        if hasattr(service, "__del__"):
            service.__del__()
        return result

    # 병렬 실행 (API 제한 고려하여 약간의 지연 추가)
    results = executor.run_symbol_tasks_parallel(
        update_high_price,
        list(SYMBOL_PRICE_MAP.keys()),
        delay=2.0,  # 0.5 → 2.0으로 증가
    )

    success_count = sum(1 for r in results if r is not None)
    logger.info(
        "high_price_update_completed",
        success_count=success_count,
        total_count=len(SYMBOL_PRICE_MAP),
        success_rate=success_count / len(SYMBOL_PRICE_MAP),
    )


@measure_execution_time
@handle_scheduler_errors(reraise=False, return_on_error=None)
@memory_monitor()
def run_previous_close_snapshot_job_parallel():
    """전일 종가 저장 (병렬)"""
    logger.info("previous_close_snapshot_started")

    def save_previous_close(symbol):
        service = PriceSnapshotService()
        result = service.save_previous_close_if_needed(symbol)
        return result

    # 병렬 실행 (API 제한 고려하여 약간의 지연 추가)
    results = executor.run_symbol_tasks_parallel(
        save_previous_close, list(SYMBOL_PRICE_MAP.keys()), delay=0.5
    )

    success_count = sum(1 for r in results if r is not None)
    logger.info(
        "previous_close_snapshot_completed",
        success_count=success_count,
        total_count=len(SYMBOL_PRICE_MAP),
        success_rate=success_count / len(SYMBOL_PRICE_MAP),
    )


@measure_execution_time
@handle_scheduler_errors(reraise=False, return_on_error=None)
@memory_monitor()
def run_previous_high_snapshot_job_parallel():
    """전일 고점 저장 (병렬)"""
    logger.info("previous_high_snapshot_started")

    def save_previous_high(symbol):
        service = PriceSnapshotService()
        result = service.save_previous_high_if_needed(symbol)
        return result

    # 병렬 실행 (API 제한 고려하여 약간의 지연 추가)
    results = executor.run_symbol_tasks_parallel(
        save_previous_high, list(SYMBOL_PRICE_MAP.keys()), delay=0.5
    )

    success_count = sum(1 for r in results if r is not None)
    logger.info(
        "previous_high_snapshot_completed",
        success_count=success_count,
        total_count=len(SYMBOL_PRICE_MAP),
        success_rate=success_count / len(SYMBOL_PRICE_MAP),
    )


@measure_execution_time
@handle_scheduler_errors(reraise=False, return_on_error=None)
@memory_monitor()
def run_previous_low_snapshot_job_parallel():
    """전일 저점 저장 (병렬)"""
    logger.info("previous_low_snapshot_started")

    def save_previous_low(symbol):
        service = PriceSnapshotService()
        result = service.save_previous_low_if_needed(symbol)
        return result

    # 병렬 실행 (API 제한 고려하여 약간의 지연 추가)
    results = executor.run_symbol_tasks_parallel(
        save_previous_low, list(SYMBOL_PRICE_MAP.keys()), delay=0.5
    )

    success_count = sum(1 for r in results if r is not None)
    logger.info(
        "previous_low_snapshot_completed",
        success_count=success_count,
        total_count=len(SYMBOL_PRICE_MAP),
        success_rate=success_count / len(SYMBOL_PRICE_MAP),
    )


@measure_execution_time
@handle_scheduler_errors(reraise=False, return_on_error=None)
@memory_monitor(threshold_mb=150.0)
def run_realtime_price_monitor_job_parallel():
    """실시간 가격 모니터링 (병렬)"""
    logger.info("realtime_price_monitoring_started")

    async def run_async_price_monitoring():
        """비동기 가격 모니터링 실행"""
        import asyncio

        async def check_price_async(symbol):
            try:
                with session_scope() as session:
                    service = PriceMonitorService()
                    if hasattr(service, "set_session"):
                        service.set_session(session)

                    result = await service.check_price_against_baseline(symbol)
                    return result
            except Exception as e:
                logger.error(f"price_monitoring_failed", symbol=symbol, error=str(e))
                return None

        # 심볼들을 배치로 나누어 처리 (동시성 제한)
        symbols = list(SYMBOL_PRICE_MAP.keys())
        batch_size = 5  # 동시 처리할 심볼 수 제한
        results = []

        for i in range(0, len(symbols), batch_size):
            batch = symbols[i : i + batch_size]

            # 배치 내 심볼들을 동시에 처리
            batch_tasks = [check_price_async(symbol) for symbol in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend(batch_results)

            # 배치 간 지연 (API 제한 고려)
            await asyncio.sleep(1.0)

        return results

    # 비동기 함수 실행
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        results = loop.run_until_complete(run_async_price_monitoring())
    finally:
        # 새로 생성된 루프만 닫기
        if not loop.is_running():
            loop.close()

    success_count = sum(
        1 for r in results if r is not None and not isinstance(r, Exception)
    )
    logger.info(
        "realtime_price_monitoring_completed",
        success_count=success_count,
        total_count=len(SYMBOL_PRICE_MAP),
        success_rate=success_count / len(SYMBOL_PRICE_MAP),
    )


@memory_monitor()
def start_parallel_scheduler():
    """병렬 처리 기능이 추가된 스케줄러 시작"""
    scheduler = BackgroundScheduler()

    logger.info("parallel_scheduler_starting")

    # 🔧 테스트용: 모든 작업을 3분 간격으로 실행 (데이터 흐름 확인용)
    scheduler.add_job(
        run_integrated_news_crawling_parallel, "interval", minutes=3
    )  # 통합 뉴스 3분마다

    scheduler.add_job(
        run_yahoo_futures_news_parallel, "interval", minutes=3
    )  # 선물 뉴스 3분마다
    scheduler.add_job(
        run_yahoo_stock_news_parallel, "interval", minutes=3
    )  # 종목 뉴스 3분마다
    scheduler.add_job(
        run_investing_market_news_parallel, "interval", minutes=3
    )  # 시장 뉴스 3분마다

    # 가격 관련 작업도 3분마다
    scheduler.add_job(
        run_high_price_update_job_parallel, "interval", minutes=3
    )  # 최고가 갱신 3분마다

    # 실시간 모니터링도 3분마다
    scheduler.add_job(
        run_realtime_price_monitor_job_parallel, "interval", minutes=3
    )  # 가격 모니터링 3분마다

    # 스냅샷 작업들도 3분마다 활성화
    scheduler.add_job(
        run_previous_close_snapshot_job_parallel, "interval", minutes=3
    )  # 전일 종가 스냅샷 3분마다
    scheduler.add_job(
        run_previous_high_snapshot_job_parallel, "interval", minutes=3
    )  # 전일 고점 스냅샷 3분마다
    scheduler.add_job(
        run_previous_low_snapshot_job_parallel, "interval", minutes=3
    )  # 전일 저점 스냅샷 3분마다

    # 백그라운드 작업들도 3분마다 테스트
    task_queue = TaskQueue()

    # 일일 종합 리포트를 백그라운드로 3분마다 스케줄링
    scheduler.add_job(
        lambda: task_queue.enqueue_task(
            run_daily_comprehensive_report_background,
            symbols=["^IXIC", "^GSPC", "^DJI"],
        ),
        "interval",
        minutes=3,
    )

    # 히스토리컬 데이터 수집도 3분마다
    scheduler.add_job(
        lambda: task_queue.enqueue_task(
            run_historical_data_collection_background,
            symbols=list(SYMBOL_PRICE_MAP.keys()),
            period="3mo",
        ),
        "interval",
        minutes=3,
    )

    # 기술적 분석 배치도 3분마다
    scheduler.add_job(
        lambda: task_queue.enqueue_task(
            run_technical_analysis_batch_background,
            symbols=["^IXIC", "^GSPC", "^DJI", "AAPL", "MSFT"],
            analysis_types=["indicators", "signals"],
        ),
        "interval",
        minutes=3,
    )

    # 기존 기술적 지표 모니터링 작업들도 3분마다
    scheduler.add_job(run_daily_index_analysis, "interval", minutes=3)
    scheduler.add_job(run_outcome_tracking_update, "interval", minutes=3)
    scheduler.add_job(initialize_recent_signals_tracking, "interval", minutes=3)

    # 패턴 발견 및 분석도 3분마다
    scheduler.add_job(run_pattern_discovery, "interval", minutes=3)

    # 일일 종합 분석 리포트도 3분마다
    scheduler.add_job(run_daily_comprehensive_report, "interval", minutes=3)

    # 메모리 최적화 작업도 3분마다
    scheduler.add_job(run_memory_optimization_job, "interval", minutes=3)

    # 비동기 기술적 분석 작업도 3분마다
    scheduler.add_job(run_async_technical_analysis_job, "interval", minutes=3)

    logger.info("parallel_scheduler_started")
    scheduler.start()


@measure_execution_time
@handle_scheduler_errors(reraise=False, return_on_error=None)
def run_memory_optimization_job():
    """
    정기적인 메모리 최적화 작업
    - 가비지 컬렉션 실행
    - 캐시 정리
    - 메모리 상태 모니터링
    """
    logger.info("memory_optimization_job_started")

    try:
        # 메모리 최적화 실행
        result = optimize_memory(aggressive=False)

        logger.info(
            "memory_optimization_completed",
            memory_freed_mb=result.get("memory_freed_mb", 0),
            optimization_success=result.get("success", False),
        )

        # 메모리 사용률이 높으면 공격적 최적화
        if result.get("final_state", {}).get("memory_percent", 0) > 85:
            logger.warning("high_memory_usage_detected_running_aggressive_optimization")
            aggressive_result = optimize_memory(aggressive=True)

            logger.info(
                "aggressive_memory_optimization_completed",
                memory_freed_mb=aggressive_result.get("memory_freed_mb", 0),
            )

    except Exception as e:
        logger.error("memory_optimization_job_failed", error=str(e))
        raise SchedulerError(
            message=f"메모리 최적화 작업 실패: {str(e)}",
            error_code=ErrorCode.TASK_EXECUTION_ERROR,
            details={"service": "memory_optimization", "error": str(e)},
        )


@measure_execution_time
@handle_scheduler_errors(reraise=False, return_on_error=None)
def run_async_technical_analysis_job():
    """
    비동기 기술적 분석 작업
    - 주요 심볼들의 기술적 지표를 비동기로 계산
    - 성능 향상된 병렬 처리
    """
    logger.info("async_technical_analysis_job_started")

    try:

        async def run_async_analysis():
            # 주요 심볼들 선택 (전체 대신 주요 지수만)
            major_symbols = [
                "^IXIC",
                "^GSPC",
                "^DJI",
                "AAPL",
                "GOOGL",
                "MSFT",
                "TSLA",
                "AMZN",
            ]

            technical_service = AsyncTechnicalIndicatorService(max_workers=3)
            price_service = AsyncPriceService(max_workers=4, max_concurrency=8)

            try:
                async with price_service:
                    # 가격 히스토리 조회
                    price_histories = (
                        await price_service.fetch_multiple_histories_async(
                            major_symbols, period="1mo", interval="1d"
                        )
                    )

                    # DataFrame 변환
                    import pandas as pd

                    symbol_data_map = {}
                    for symbol, history in price_histories.items():
                        if history and history.get("timestamps"):
                            df = pd.DataFrame(
                                {
                                    "timestamp": pd.to_datetime(
                                        history["timestamps"], unit="s"
                                    ),
                                    "open": history["open"],
                                    "high": history["high"],
                                    "low": history["low"],
                                    "close": history["close"],
                                    "volume": history["volume"],
                                }
                            ).dropna()

                            if not df.empty:
                                symbol_data_map[symbol] = df

                    # 비동기 기술적 분석 실행
                    if symbol_data_map:
                        analysis_results = (
                            await technical_service.analyze_multiple_symbols_async(
                                symbol_data_map, batch_size=3
                            )
                        )

                        logger.info(
                            "async_technical_analysis_completed",
                            analyzed_symbols=len(analysis_results),
                            total_symbols=len(major_symbols),
                        )

                        return analysis_results
                    else:
                        logger.warning("no_valid_price_data_for_analysis")
                        return {}

            finally:
                # 리소스 정리
                if hasattr(technical_service, "__del__"):
                    technical_service.__del__()

        # 비동기 작업 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(run_async_analysis())
            logger.info(
                "async_technical_analysis_job_completed",
                results_count=len(result) if result else 0,
            )
        finally:
            loop.close()

    except Exception as e:
        logger.error("async_technical_analysis_job_failed", error=str(e))
        raise SchedulerError(
            message=f"비동기 기술적 분석 작업 실패: {str(e)}",
            error_code=ErrorCode.TASK_EXECUTION_ERROR,
            details={"service": "async_technical_analysis", "error": str(e)},
        )


@measure_execution_time
@handle_scheduler_errors(reraise=False, return_on_error=None)
def run_daily_comprehensive_report():
    """
    일일 종합 분석 리포트 생성 및 텔레그램 전송
    - 백테스팅 성과 분석
    - 패턴 분석 결과
    - 머신러닝 기반 분석
    - 투자 인사이트 제공
    """
    logger.info("daily_comprehensive_report_started")

    service = DailyComprehensiveReportService()
    # 실제 텔레그램 전송을 하는 메서드 호출
    result = service.generate_daily_report()

    if result and result.get("status") == "error":
        raise SchedulerError(
            message=f"일일 리포트 생성 실패: {result.get('error', 'Unknown error')}",
            error_code=ErrorCode.TASK_EXECUTION_ERROR,
            details={"service": "daily_comprehensive_report", "result": result},
        )
    else:
        logger.info(
            "daily_comprehensive_report_completed",
            message_length=result.get("report_length", 0),
        )


@memory_monitor()
def cleanup_scheduler_memory():
    """
    스케줄러 메모리 정리 작업
    """
    try:
        # 메모리 최적화 실행
        optimize_memory()
        logger.info("scheduler_memory_cleanup_completed")
    except Exception as e:
        logger.error("scheduler_memory_cleanup_failed", error=str(e))


@memory_monitor()
def monitor_scheduler_performance():
    """
    스케줄러 성능 모니터링
    """
    try:
        import psutil
        import os

        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent()

        logger.info(
            "scheduler_performance_metrics",
            memory_mb=memory_info.rss / 1024 / 1024,
            cpu_percent=cpu_percent,
            threads=process.num_threads(),
        )
    except Exception as e:
        logger.error("scheduler_performance_monitoring_failed", error=str(e))
