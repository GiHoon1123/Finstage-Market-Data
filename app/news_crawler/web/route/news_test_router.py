from fastapi import APIRouter
from app.news_crawler.service.yahoo_company_news_crawler import YahooCompanyNewsCrawler

router = APIRouter(prefix="/test/news", tags=["Test News Crawler"])

@router.post("/{symbol}")
def crawl_and_save_news(symbol: str):
    crawler = YahooCompanyNewsCrawler(symbol)
    crawler.save_all()
    return {"message": f"{symbol} 뉴스 저장 완료"}
