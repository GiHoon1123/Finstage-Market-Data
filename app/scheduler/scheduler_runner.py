from concurrent.futures import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from app.crawler.service.yahoo_company_news_crawler import YahooCompanyNewsCrawler
from app.crawler.service.yahoo_futures_news_crawler import YahooFuturesNewsCrawler
from app.crawler.service.yahoo_index_news_crawler import YahooIndexNewsCrawler
from app.crawler.service.investing_rss_news_crawler import InvestingRssNewsCrawler
from app.crawler.service.news_processor import NewsProcessor
from app.common.constants.symbol_names import YAHOO_INDEX_SYMBOLS, YAHOO_FUTURES_SYMBOLS, YAHOO_STOCK_SYMBOLS
from app.common.constants.rss_feeds import INVESTING_RSS_FEEDS
from app.crawler.service.dc_us_stock_crawler import DcUsStockGalleryCrawler
from app.crawler.service.dc_news_processor import DcNewsProcessor
import time

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

def run_investing_news_crawlers():
    print("📡 Investing.com 뉴스 크롤링 시작")

    for symbol, rss_url in INVESTING_RSS_FEEDS.items():
        print(f"🔍 {symbol} → {rss_url}")
        time.sleep(5)
        crawler = InvestingRssNewsCrawler(rss_url=rss_url, symbol=symbol)
        news_items = crawler.crawl()
        processor = NewsProcessor(news_items)
        processor.run()
        time.sleep(3)  # 요청 과부하 방지용

    print("✅ Investing.com 뉴스 크롤링 완료")


def run_yahoo_news_crawlers():
    print("🕒 [뉴스 크롤링] 시작")

    def crawl_company(symbol):
        time.sleep(5)
        YahooCompanyNewsCrawler(symbol).process_all()

    def crawl_futures(symbol):
        time.sleep(5)
        YahooFuturesNewsCrawler(symbol).process_all()

    def crawl_index(symbol):
        time.sleep(5)
        YahooIndexNewsCrawler(symbol).process_all()

    with ThreadPoolExecutor(max_workers=5) as executor:
        for symbol in YAHOO_STOCK_SYMBOLS:
            executor.submit(crawl_company, symbol)
            
        for symbol in YAHOO_FUTURES_SYMBOLS:
            executor.submit(crawl_futures, symbol)

        for symbol in YAHOO_INDEX_SYMBOLS:
            executor.submit(crawl_index, symbol)

        # future = executor.submit(run_dcinside_crawler)
        # future.result()  # 실행 보장


    print("✅ [뉴스 크롤링] 완료")


def start_scheduler():
    scheduler = BackgroundScheduler()
    # 예: 10분마다 실행
    scheduler.add_job(run_yahoo_news_crawlers, 'interval', minutes=10)
    scheduler.add_job(run_investing_news_crawlers, 'interval', minutes=10)
    scheduler.start()
    print("🔄 APScheduler 시작됨")

    run_yahoo_news_crawlers()
    run_investing_news_crawlers()
