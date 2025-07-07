import requests
import xml.etree.ElementTree as ET
from typing import List, Dict
from urllib.parse import quote

from app.crawler.service.base import BaseCrawler
from app.crawler.service.news_processor import NewsProcessor  # ✅ 추가된 부분
from email.utils import parsedate_to_datetime


class YahooCompanyNewsCrawler(BaseCrawler):
    def __init__(self, symbol: str):
        self.symbol = symbol
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

            for item in items[:20]:
                title = item.findtext("title")
                url = item.findtext("link")
                summary = item.findtext("description")
                pub_date = item.findtext("pubDate")


                if not title or not url:
                    continue

                content_hash = self.generate_hash(title)

                news_list.append({
                    "title": title.strip(),
                    "url": url.strip(),
                    "source": "yahoo.com",
                    "summary": summary.strip() if summary else None,
                    "html": "",
                    "symbol": self.symbol,
                    "content_hash": content_hash,
                    "crawled_at": self.get_crawled_at(),
                    "published_at": parsedate_to_datetime(pub_date) if pub_date else None
                })

            return news_list

        except Exception as e:
            print(f"❌ 파싱 중 오류 발생: {e}")
            return []

    def save_all(self):
        results = self.crawl()
        processor = NewsProcessor(results)
        processor.run()
