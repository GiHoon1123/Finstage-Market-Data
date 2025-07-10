from apscheduler.schedulers.background import BackgroundScheduler
from app.news_crawler.service.investing_news_crawler import InvestingNewsCrawler
from app.news_crawler.service.yahoo_news_crawler import YahooNewsCrawler
from app.market_price.service.price_high_record_service import PriceHighRecordService
from app.market_price.service.price_snapshot_service import PriceSnapshotService
from app.market_price.service.price_monitor_service import PriceMonitorService
from app.common.constants.symbol_names import INDEX_SYMBOLS, FUTURES_SYMBOLS, STOCK_SYMBOLS, SYMBOL_PRICE_MAP
from app.common.constants.rss_feeds import INVESTING_ECONOMIC_SYMBOLS, INVESTING_MARKET_SYMBOLS
import time


def run_investing_economic_news():
    print("📡 Investing 경제 뉴스 크롤링 시작")

    for symbol in INVESTING_ECONOMIC_SYMBOLS:
        print(f"🔍 {symbol} 뉴스 처리 중...")
        InvestingNewsCrawler(symbol).process_all()

    print("✅ Investing 경제 뉴스 크롤링 완료")


def run_investing_market_news():
    print("📡 Investing 시장 뉴스 크롤링 시작")

    for symbol in INVESTING_MARKET_SYMBOLS:
        print(f"🔍 {symbol} 뉴스 처리 중...")
        InvestingNewsCrawler(symbol).process_all()

    print("✅ Investing 시장 뉴스 크롤링 완료")


def run_yahoo_futures_news():
    print("🕒 Yahoo 선물 뉴스 크롤링 시작")
    for symbol in FUTURES_SYMBOLS:
        print(f"🔍 {symbol} 뉴스 처리 중...")
        YahooNewsCrawler(symbol).process_all()

    print("✅ Yahoo 선물 뉴스 크롤링 완료")


def run_yahoo_index_news():
    print("🕒 Yahoo 지수 뉴스 크롤링 시작")
    for symbol in INDEX_SYMBOLS:
        print(f"🔍 {symbol} 뉴스 처리 중...")
        YahooNewsCrawler(symbol).process_all()

    print("✅ Yahoo 지수 뉴스 크롤링 완료")


def run_yahoo_stock_news():
    print("🕒 Yahoo 종목 뉴스 크롤링 시작")
    for symbol in STOCK_SYMBOLS:
        print(f"🔍 {symbol} 뉴스 처리 중...")
        YahooNewsCrawler(symbol).process_all()

    print("✅ Yahoo 종목 뉴스 크롤링 완료")


def run_high_price_update_job():
    print("📈 상장 후 최고가 갱신 시작")
    service = PriceHighRecordService()
    for symbol in SYMBOL_PRICE_MAP:
        time.sleep(5.0)  
        service.update_all_time_high(symbol)
    
    print("✅ 최고가 갱신 완료")


def run_previous_close_snapshot_job():
    print("🕓 전일 종가 저장 시작")
    service = PriceSnapshotService()
    for symbol in SYMBOL_PRICE_MAP:
        time.sleep(5.0)
        service.save_previous_close_if_needed(symbol)

    print("✅ 전일 종가 저장 완료")

def run_previous_high_snapshot_job():
    print("🔺 전일 고점 저장 시작")
    service = PriceSnapshotService()
    for symbol in SYMBOL_PRICE_MAP:
        time.sleep(5.0)
        service.save_previous_high_if_needed(symbol)
    print("✅ 전일 고점 저장 완료")


def run_previous_low_snapshot_job():
    print("🔻 전일 저점 저장 시작")
    service = PriceSnapshotService()
    for symbol in SYMBOL_PRICE_MAP:
        time.sleep(5.0)
        service.save_previous_low_if_needed(symbol)
    print("✅ 전일 저점 저장 완료")


def run_realtime_price_monitor_job():
    print("📡 실시간 가격 모니터링 시작")
    service = PriceMonitorService()
    for symbol in SYMBOL_PRICE_MAP:
        time.sleep(5.0)
        service.check_price_against_baseline(symbol)
        
    print("✅ 실시간 가격 모니터링 완료")





def start_scheduler():
    scheduler = BackgroundScheduler()

    print("🔄 APScheduler 시작됨")
    # scheduler.add_job(run_investing_economic_news, 'interval', minutes=30)
    # scheduler.add_job(run_investing_market_news, 'interval', minutes=30)
    # scheduler.add_job(run_yahoo_futures_news, 'interval', minutes=10)
    # scheduler.add_job(run_yahoo_index_news, 'interval', minutes=30)
    # scheduler.add_job(run_yahoo_stock_news, 'interval', minutes=15)
    # scheduler.add_job(run_high_price_update_job, 'interval', hours=1)
    # scheduler.add_job(run_previous_close_snapshot_job, 'interval', hours=1)
    # scheduler.add_job(run_realtime_price_monitor_job, 'interval', minutes=1)
    # scheduler.add_job(run_previous_high_snapshot_job, 'interval', hours=1)
    # scheduler.add_job(run_previous_low_snapshot_job, 'interval', hours=1)
    # run_high_price_update_job()
    # run_previous_close_snapshot_job()
    # run_realtime_price_monitor_job()

    # run_previous_high_snapshot_job()
    # run_previous_low_snapshot_job()
    # run_realtime_price_monitor_job()
    
    scheduler.start()   
    