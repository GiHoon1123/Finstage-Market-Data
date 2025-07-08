from apscheduler.schedulers.background import BackgroundScheduler
from app.news_crawler.service.yahoo_company_news_crawler import YahooCompanyNewsCrawler
from app.news_crawler.service.yahoo_futures_news_crawler import YahooFuturesNewsCrawler
from app.news_crawler.service.yahoo_index_news_crawler import YahooIndexNewsCrawler
from app.news_crawler.service.investing_news_crawler import InvestingNewsCrawler
from app.news_crawler.service.news_processor import NewsProcessor
from app.news_crawler.service.dc_us_stock_crawler import DcUsStockGalleryCrawler
from app.news_crawler.service.dc_news_processor import DcNewsProcessor
from app.news_crawler.service.yahoo_news_crawler import YahooNewsCrawler
from app.market_price.service.price_high_record_service import PriceHighRecordService
from app.market_price.service.price_snapshot_service import PriceSnapshotService
from app.market_price.service.price_monitor_service import PriceMonitorService
from app.common.constants.symbol_names import INDEX_SYMBOLS, FUTURES_SYMBOLS, STOCK_SYMBOLS, SYMBOL_PRICE_MAP
from app.common.constants.rss_feeds import INVESTING_ECONOMIC_SYMBOLS, INVESTING_MARKET_SYMBOLS
from app.common.constants.yahoo_feeds import YAHOO_NEWS_SYMBOLS
import time
from concurrent.futures import ThreadPoolExecutor

# def run_dcinside_crawler():
#     print("📥 DC인사이드 미국주식 갤러리 크롤링 시작")

#     all_posts = []
#     for page in range(1, 2):  # 1~2페이지
#         crawler = DcUsStockGalleryCrawler(page=page)
#         posts = crawler.crawl()
#         all_posts.extend(posts)

#     processor = DcNewsProcessor(all_posts)
#     processor.run()

#     print("✅ DC인사이드 갤러리 처리 완료")

# def run_investing_news_crawlers():
#     print("📡 Investing.com 뉴스 크롤링 시작")

#     def crawl(symbol):
#         time.sleep(5)
#         crawler = InvestingRssNewsCrawler(symbol)
#         crawler.process_all()

#     with ThreadPoolExecutor(max_workers=3) as executor:
#         for symbol in INVESTING_RSS_FEEDS:
#             executor.submit(crawl, symbol)

#     print("✅ Investing.com 뉴스 크롤링 완료")

# def run_yahoo_news_crawlers():
#     print("🕒 Yahoo 뉴스 크롤링 시작")

#     def crawl(symbol):
#         time.sleep(5)
#         YahooNewsCrawler(symbol).process_all()

#     with ThreadPoolExecutor(max_workers=5) as executor:
#         for symbol in YAHOO_NEWS_SYMBOLS:
#             executor.submit(crawl, symbol)

#     print("✅ Yahoo 뉴스 크롤링 완료")



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


def run_realtime_price_monitor_job():
    print("📡 실시간 가격 모니터링 시작")
    service = PriceMonitorService()
    for symbol in SYMBOL_PRICE_MAP:
        time.sleep(5.0)
        service.check_price_against_baseline(symbol)
        
    print("✅ 실시간 가격 모니터링 완료")





def start_scheduler():
    scheduler = BackgroundScheduler()
    # scheduler.add_job(run_yahoo_news_crawlers, 'interval', minutes=10)
    # scheduler.add_job(run_investing_news_crawlers, 'interval', minutes=10)
    
    print("🔄 APScheduler 시작됨")
    # scheduler.add_job(run_investing_economic_news, 'interval', minutes=30)
    # scheduler.add_job(run_investing_market_news, 'interval', minutes=30)
    # scheduler.add_job(run_yahoo_futures_news, 'interval', minutes=10)
    # scheduler.add_job(run_yahoo_index_news, 'interval', minutes=30)
    # scheduler.add_job(run_yahoo_stock_news, 'interval', minutes=15)
    # scheduler.add_job(run_high_price_update_job, 'interval', hours=1)
    # scheduler.add_job(run_previous_close_snapshot_job, 'interval', hours=1)
    # scheduler.add_job(run_realtime_price_monitor_job, 'interval', minutes=1)
    # run_high_price_update_job()
    # run_previous_close_snapshot_job()
    run_realtime_price_monitor_job()
    scheduler.start()
    