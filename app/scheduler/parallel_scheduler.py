"""
병렬 처리 기능이 추가된 스케줄러 러너
"""

from apscheduler.schedulers.background import BackgroundScheduler
from app.common.utils.parallel_executor import ParallelExecutor, measure_execution_time
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


# 병렬 실행기 인스턴스 생성
executor = ParallelExecutor(max_workers=10)


@measure_execution_time
def run_investing_economic_news_parallel():
    """Investing 경제 뉴스 크롤링 (병렬)"""
    from app.news_crawler.service.investing_news_crawler import InvestingNewsCrawler

    print("📡 Investing 경제 뉴스 크롤링 시작 (병렬)")

    def process_symbol(symbol):
        print(f"🔍 {symbol} 뉴스 처리 중...")
        crawler = InvestingNewsCrawler(symbol)
        result = crawler.process_all()
        return result

    # 병렬 실행 (API 제한 고려하여 약간의 지연 추가)
    results = executor.run_symbol_tasks_parallel(
        process_symbol, INVESTING_ECONOMIC_SYMBOLS, delay=0.5
    )

    success_count = sum(1 for r in results if r is not None)
    print(
        f"✅ Investing 경제 뉴스 크롤링 완료: {success_count}/{len(INVESTING_ECONOMIC_SYMBOLS)} 성공"
    )


@measure_execution_time
def run_investing_market_news_parallel():
    """Investing 시장 뉴스 크롤링 (병렬)"""
    from app.news_crawler.service.investing_news_crawler import InvestingNewsCrawler

    print("📡 Investing 시장 뉴스 크롤링 시작 (병렬)")

    def process_symbol(symbol):
        print(f"🔍 {symbol} 뉴스 처리 중...")
        crawler = InvestingNewsCrawler(symbol)
        result = crawler.process_all()
        return result

    # 병렬 실행 (API 제한 고려하여 약간의 지연 추가)
    results = executor.run_symbol_tasks_parallel(
        process_symbol, INVESTING_MARKET_SYMBOLS, delay=0.5
    )

    success_count = sum(1 for r in results if r is not None)
    print(
        f"✅ Investing 시장 뉴스 크롤링 완료: {success_count}/{len(INVESTING_MARKET_SYMBOLS)} 성공"
    )


@measure_execution_time
def run_yahoo_futures_news_parallel():
    """Yahoo 선물 뉴스 크롤링 (병렬)"""
    from app.news_crawler.service.yahoo_news_crawler import YahooNewsCrawler

    print("🕒 Yahoo 선물 뉴스 크롤링 시작 (병렬)")

    def process_symbol(symbol):
        print(f"🔍 {symbol} 뉴스 처리 중...")
        crawler = YahooNewsCrawler(symbol)
        result = crawler.process_all()
        return result

    # 병렬 실행 (API 제한 고려하여 약간의 지연 추가)
    results = executor.run_symbol_tasks_parallel(
        process_symbol, FUTURES_SYMBOLS, delay=0.5
    )

    success_count = sum(1 for r in results if r is not None)
    print(
        f"✅ Yahoo 선물 뉴스 크롤링 완료: {success_count}/{len(FUTURES_SYMBOLS)} 성공"
    )


@measure_execution_time
def run_yahoo_index_news_parallel():
    """Yahoo 지수 뉴스 크롤링 (병렬)"""
    from app.news_crawler.service.yahoo_news_crawler import YahooNewsCrawler

    print("🕒 Yahoo 지수 뉴스 크롤링 시작 (병렬)")

    def process_symbol(symbol):
        print(f"🔍 {symbol} 뉴스 처리 중...")
        crawler = YahooNewsCrawler(symbol)
        result = crawler.process_all()
        return result

    # 병렬 실행 (API 제한 고려하여 약간의 지연 추가)
    results = executor.run_symbol_tasks_parallel(
        process_symbol, INDEX_SYMBOLS, delay=0.5
    )

    success_count = sum(1 for r in results if r is not None)
    print(f"✅ Yahoo 지수 뉴스 크롤링 완료: {success_count}/{len(INDEX_SYMBOLS)} 성공")


@measure_execution_time
def run_yahoo_stock_news_parallel():
    """Yahoo 종목 뉴스 크롤링 (병렬)"""
    from app.news_crawler.service.yahoo_news_crawler import YahooNewsCrawler

    print("🕒 Yahoo 종목 뉴스 크롤링 시작 (병렬)")

    def process_symbol(symbol):
        print(f"🔍 {symbol} 뉴스 처리 중...")
        crawler = YahooNewsCrawler(symbol)
        result = crawler.process_all()
        return result

    # 병렬 실행 (API 제한 고려하여 약간의 지연 추가)
    results = executor.run_symbol_tasks_parallel(
        process_symbol, STOCK_SYMBOLS, delay=0.5
    )

    success_count = sum(1 for r in results if r is not None)
    print(f"✅ Yahoo 종목 뉴스 크롤링 완료: {success_count}/{len(STOCK_SYMBOLS)} 성공")


@measure_execution_time
def run_high_price_update_job_parallel():
    """상장 후 최고가 갱신 (병렬)"""
    from app.market_price.service.price_high_record_service import (
        PriceHighRecordService,
    )

    print("📈 상장 후 최고가 갱신 시작 (병렬)")

    def update_high_price(symbol):
        service = PriceHighRecordService()
        result = service.update_all_time_high(symbol)
        return result

    # 병렬 실행 (API 제한 고려하여 약간의 지연 추가)
    results = executor.run_symbol_tasks_parallel(
        update_high_price, list(SYMBOL_PRICE_MAP.keys()), delay=0.5
    )

    success_count = sum(1 for r in results if r is not None)
    print(f"✅ 최고가 갱신 완료: {success_count}/{len(SYMBOL_PRICE_MAP)} 성공")


@measure_execution_time
def run_previous_close_snapshot_job_parallel():
    """전일 종가 저장 (병렬)"""
    from app.market_price.service.price_snapshot_service import PriceSnapshotService

    print("🕓 전일 종가 저장 시작 (병렬)")

    def save_previous_close(symbol):
        service = PriceSnapshotService()
        result = service.save_previous_close_if_needed(symbol)
        return result

    # 병렬 실행 (API 제한 고려하여 약간의 지연 추가)
    results = executor.run_symbol_tasks_parallel(
        save_previous_close, list(SYMBOL_PRICE_MAP.keys()), delay=0.5
    )

    success_count = sum(1 for r in results if r is not None)
    print(f"✅ 전일 종가 저장 완료: {success_count}/{len(SYMBOL_PRICE_MAP)} 성공")


@measure_execution_time
def run_previous_high_snapshot_job_parallel():
    """전일 고점 저장 (병렬)"""
    from app.market_price.service.price_snapshot_service import PriceSnapshotService

    print("🔺 전일 고점 저장 시작 (병렬)")

    def save_previous_high(symbol):
        service = PriceSnapshotService()
        result = service.save_previous_high_if_needed(symbol)
        return result

    # 병렬 실행 (API 제한 고려하여 약간의 지연 추가)
    results = executor.run_symbol_tasks_parallel(
        save_previous_high, list(SYMBOL_PRICE_MAP.keys()), delay=0.5
    )

    success_count = sum(1 for r in results if r is not None)
    print(f"✅ 전일 고점 저장 완료: {success_count}/{len(SYMBOL_PRICE_MAP)} 성공")


@measure_execution_time
def run_previous_low_snapshot_job_parallel():
    """전일 저점 저장 (병렬)"""
    from app.market_price.service.price_snapshot_service import PriceSnapshotService

    print("🔻 전일 저점 저장 시작 (병렬)")

    def save_previous_low(symbol):
        service = PriceSnapshotService()
        result = service.save_previous_low_if_needed(symbol)
        return result

    # 병렬 실행 (API 제한 고려하여 약간의 지연 추가)
    results = executor.run_symbol_tasks_parallel(
        save_previous_low, list(SYMBOL_PRICE_MAP.keys()), delay=0.5
    )

    success_count = sum(1 for r in results if r is not None)
    print(f"✅ 전일 저점 저장 완료: {success_count}/{len(SYMBOL_PRICE_MAP)} 성공")


@measure_execution_time
def run_realtime_price_monitor_job_parallel():
    """실시간 가격 모니터링 (병렬)"""
    from app.market_price.service.price_monitor_service import PriceMonitorService

    print("📡 실시간 가격 모니터링 시작 (병렬)")

    def check_price(symbol):
        service = PriceMonitorService()
        result = service.check_price_against_baseline(symbol)
        return result

    # 병렬 실행 (API 제한 고려하여 약간의 지연 추가)
    results = executor.run_symbol_tasks_parallel(
        check_price, list(SYMBOL_PRICE_MAP.keys()), delay=0.5
    )

    success_count = sum(1 for r in results if r is not None)
    print(f"✅ 실시간 가격 모니터링 완료: {success_count}/{len(SYMBOL_PRICE_MAP)} 성공")


def start_parallel_scheduler():
    """병렬 처리 기능이 추가된 스케줄러 시작"""
    scheduler = BackgroundScheduler()

    print("🔄 병렬 처리 APScheduler 시작됨")

    # 뉴스 크롤링 작업 (병렬)
    scheduler.add_job(run_investing_economic_news_parallel, "interval", minutes=30)
    scheduler.add_job(run_investing_market_news_parallel, "interval", minutes=30)
    scheduler.add_job(run_yahoo_futures_news_parallel, "interval", minutes=10)
    scheduler.add_job(run_yahoo_index_news_parallel, "interval", minutes=30)
    scheduler.add_job(run_yahoo_stock_news_parallel, "interval", minutes=15)

    # 가격 관련 작업 (병렬)
    scheduler.add_job(run_high_price_update_job_parallel, "interval", hours=1)
    scheduler.add_job(run_previous_close_snapshot_job_parallel, "interval", hours=1)
    scheduler.add_job(run_previous_high_snapshot_job_parallel, "interval", hours=1)
    scheduler.add_job(run_previous_low_snapshot_job_parallel, "interval", hours=1)

    # 실시간 모니터링 (병렬)
    scheduler.add_job(run_realtime_price_monitor_job_parallel, "interval", minutes=1)

    # 기존 기술적 지표 모니터링 작업들은 그대로 유지
    from app.scheduler.scheduler_runner import (
        run_daily_index_analysis,
        run_outcome_tracking_update,
        initialize_recent_signals_tracking,
    )

    scheduler.add_job(run_daily_index_analysis, "interval", hours=1)
    scheduler.add_job(run_outcome_tracking_update, "interval", hours=1)
    scheduler.add_job(initialize_recent_signals_tracking, "interval", hours=6)

    print("✅ 병렬 처리 스케줄러 시작")
    scheduler.start()
