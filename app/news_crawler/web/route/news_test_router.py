from fastapi import APIRouter
from app.news_crawler.service.yahoo_news_crawler import YahooNewsCrawler

router = APIRouter(prefix="/test/news", tags=["Test News Crawler"])

@router.post("/{symbol}")
def crawl_and_save_news(symbol: str):
    crawler = YahooNewsCrawler(symbol)
    crawler.process_all()
    return {"message": f"{symbol} 뉴스 저장 완료"}
