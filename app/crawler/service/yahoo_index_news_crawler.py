import requests
import xml.etree.ElementTree as ET
import hashlib
from datetime import datetime
from typing import List, Dict
from urllib.parse import quote

from app.crawler.service.base import BaseCrawler
from app.crawler.service.news_processor import NewsProcessor  # ✅ 추가


class YahooIndexNewsCrawler(BaseCrawler):
    def __init__(self, symbol: str):
        self.symbol = symbol  # 예: "^IXIC", "^GSPC", "^DJI"
        self.base_url = (
            "https://feeds.finance.yahoo.com/rss/2.0/headline"
            f"?s={quote(self.symbol)}&region=US&lang=en-US"
        )

    def crawl(self) -> List[Dict]:
        try:
            res = requests.get(self.base_url, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code != 200:
                print(f"❌ 요청 실패: status {res.status_code}")
                return []

            root = ET.fromstring(res.content)
            items = root.find("channel").findall("item")

            news_list = []

            for item in items[:20]:  # 최신 20개만
                title = item.findtext("title")
                url = item.findtext("link")
                summary = item.findtext("description")
                pub_date = item.findtext("pubDate")

                if not title or not url:
                    continue

                news_list.append({
                    "title": title.strip(),
                    "url": url.strip(),
                    "source": "yahoo.com",
                    "summary": summary.strip() if summary else None,
                    "html": "",  # 상세 HTML은 미포함
                    "symbol": self.symbol,
                    "content_hash": self.generate_hash(title + url),
                    "crawled_at": self.get_crawled_at(),
                    "published_at": pub_date.strip() if pub_date else None
                })

            return news_list

        except Exception as e:
            print(f"❌ 파싱 중 오류 발생: {e}")
            return []

    def save_all(self):
        results = self.crawl()
        processor = NewsProcessor(results)
        processor.run()


if __name__ == "__main__":
    index_symbols = {
        "NASDAQ": "^IXIC",
        "S&P500": "^GSPC",
        "DOWJONES": "^DJI"
    }

    for name, symbol in index_symbols.items():
        print(f"\n=== {name} 뉴스 저장 시작 ===")
        crawler = YahooIndexNewsCrawler(symbol=symbol)
        crawler.save_all()
