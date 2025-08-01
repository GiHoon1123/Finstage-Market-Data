"""
병렬 처리 기능이 추가된 스케줄러 러너
"""

from apscheduler.schedulers.background import BackgroundScheduler
from app.common.utils.parallel_executor import ParallelExecutor, measure_execution_time
from app.common.utils.logging_config import get_logger
from app.common.exceptions.handlers import handle_scheduler_errors, safe_execute
from app.common.exceptions.base import SchedulerError, ErrorCode

logger = get_logger("parallel_scheduler")
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


# 병렬 실행기 인스턴스 생성 (max_workers 감소로 DB 연결 부하 감소)
executor = ParallelExecutor(max_workers=2)  # 3 → 2로 더 감소


@measure_execution_time
@handle_scheduler_errors(reraise=False, return_on_error=None)
def run_integrated_news_crawling_parallel():
    """통합 뉴스 크롤링 (경제 뉴스 + 지수 뉴스)"""
    from app.news_crawler.service.investing_news_crawler import InvestingNewsCrawler
    from app.news_crawler.service.yahoo_news_crawler import YahooNewsCrawler

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
def run_investing_market_news_parallel():
    """Investing 시장 뉴스 크롤링 (병렬)"""
    from app.news_crawler.service.investing_news_crawler import InvestingNewsCrawler

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
def run_yahoo_futures_news_parallel():
    """Yahoo 선물 뉴스 크롤링 (병렬)"""
    from app.news_crawler.service.yahoo_news_crawler import YahooNewsCrawler

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
def run_yahoo_stock_news_parallel():
    """Yahoo 종목 뉴스 크롤링 (병렬)"""
    from app.news_crawler.service.yahoo_news_crawler import YahooNewsCrawler

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
def run_high_price_update_job_parallel():
    """상장 후 최고가 갱신 (병렬)"""
    from app.market_price.service.price_high_record_service import (
        PriceHighRecordService,
    )

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
def run_previous_close_snapshot_job_parallel():
    """전일 종가 저장 (병렬)"""
    from app.market_price.service.price_snapshot_service import PriceSnapshotService

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
def run_previous_high_snapshot_job_parallel():
    """전일 고점 저장 (병렬)"""
    from app.market_price.service.price_snapshot_service import PriceSnapshotService

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
def run_previous_low_snapshot_job_parallel():
    """전일 저점 저장 (병렬)"""
    from app.market_price.service.price_snapshot_service import PriceSnapshotService

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
def run_realtime_price_monitor_job_parallel():
    """실시간 가격 모니터링 (병렬)"""
    from app.market_price.service.price_monitor_service import PriceMonitorService
    from app.common.utils.db_session_manager import session_scope

    logger.info("realtime_price_monitoring_started")

    def check_price(symbol):
        return safe_execute(
            lambda: _check_price_for_symbol(symbol),
            default_return=None,
            log_errors=True,
        )

    def _check_price_for_symbol(symbol):
        # 세션 컨텍스트 매니저 사용
        with session_scope() as session:
            service = PriceMonitorService()
            # 세션 명시적 전달 (가능한 경우)
            if hasattr(service, "set_session"):
                service.set_session(session)
            result = service.check_price_against_baseline(symbol)
            return result

    # 병렬 실행 (배치 크기 제한 및 지연 시간 증가)
    results = executor.run_symbol_tasks_parallel(
        check_price, list(SYMBOL_PRICE_MAP.keys()), delay=1.0  # 0.5 → 1.0으로 증가
    )

    success_count = sum(1 for r in results if r is not None)
    logger.info(
        "realtime_price_monitoring_completed",
        success_count=success_count,
        total_count=len(SYMBOL_PRICE_MAP),
        success_rate=success_count / len(SYMBOL_PRICE_MAP),
    )


def start_parallel_scheduler():
    """병렬 처리 기능이 추가된 스케줄러 시작"""
    scheduler = BackgroundScheduler()

    logger.info("parallel_scheduler_starting")

    # 🆕 통합 뉴스 크롤링 작업 (경제 뉴스 + 지수 뉴스)
    scheduler.add_job(
        run_integrated_news_crawling_parallel, "interval", minutes=90
    )  # 통합 뉴스 90분마다 (기존 60분×2 → 90분×1로 최적화)

    # 🆕 모든 종목 뉴스 크롤링 활성화 (데이터 흐름 확인용)
    scheduler.add_job(
        run_yahoo_futures_news_parallel, "interval", hours=2
    )  # 선물 뉴스 2시간마다
    scheduler.add_job(
        run_yahoo_stock_news_parallel, "interval", hours=3
    )  # 종목 뉴스 3시간마다
    scheduler.add_job(
        run_investing_market_news_parallel, "interval", hours=4
    )  # 시장 뉴스 4시간마다

    # 가격 관련 작업 (핵심만 유지) - 주요 지수만 모니터링
    scheduler.add_job(
        run_high_price_update_job_parallel,
        "interval",
        hours=4,  # 2시간 → 4시간으로 더 감소
    )

    # 실시간 모니터링 (핵심만) - 간격 더 증가
    scheduler.add_job(
        run_realtime_price_monitor_job_parallel, "interval", minutes=30
    )  # 10분 → 30분으로 대폭 감소

    # 스냅샷 작업들 제거 (일일 리포트에서 충분히 커버)
    # scheduler.add_job(run_previous_close_snapshot_job_parallel, ...)  # 제거
    # scheduler.add_job(run_previous_high_snapshot_job_parallel, ...)   # 제거
    # scheduler.add_job(run_previous_low_snapshot_job_parallel, ...)    # 제거

    # 기존 기술적 지표 모니터링 작업들은 그대로 유지
    from app.scheduler.scheduler_runner import (
        run_daily_index_analysis,
        run_outcome_tracking_update,
        initialize_recent_signals_tracking,
        run_pattern_discovery,
    )

    # 일일 지수 분석은 scheduler_runner.py에서 오전 7시에만 실행
    # scheduler.add_job(run_daily_index_analysis, "interval", hours=1)  # 제거됨
    scheduler.add_job(run_outcome_tracking_update, "interval", hours=1)
    scheduler.add_job(initialize_recent_signals_tracking, "interval", hours=6)

    # 🆕 패턴 발견 및 분석 (매일 오전 6시)
    scheduler.add_job(
        run_pattern_discovery, "cron", hour=6, minute=0, timezone="Asia/Seoul"
    )

    # 🆕 일일 종합 분석 리포트 (매일 오전 8시)
    scheduler.add_job(
        run_daily_comprehensive_report, "cron", hour=8, minute=0, timezone="Asia/Seoul"
    )

    logger.info("parallel_scheduler_started")
    scheduler.start()


@measure_execution_time
@handle_scheduler_errors(reraise=False, return_on_error=None)
def run_daily_comprehensive_report():
    """
    일일 종합 분석 리포트 생성 및 전송
    - 백테스팅 성과 분석
    - 패턴 분석 결과
    - 머신러닝 기반 분석
    - 투자 인사이트 제공
    """
    logger.info("daily_comprehensive_report_started")

    from app.technical_analysis.service.daily_comprehensive_report_service import (
        DailyComprehensiveReportService,
    )

    service = DailyComprehensiveReportService()
    result = service.generate_daily_report()

    if result and "error" in result:
        raise SchedulerError(
            message=f"일일 리포트 생성 실패: {result['error']}",
            error_code=ErrorCode.TASK_EXECUTION_ERROR,
            details={"service": "daily_comprehensive_report", "result": result},
        )
    else:
        logger.info("daily_comprehensive_report_completed")
