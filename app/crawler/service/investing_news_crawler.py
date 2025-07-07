import requests
import xml.etree.ElementTree as ET
from typing import List, Dict
from dateutil import parser as date_parser 
from app.crawler.service.base import BaseCrawler
from app.crawler.service.news_processor import NewsProcessor
from app.common.constants.rss_feeds import INVESTING_RSS_FEEDS


class InvestingNewsCrawler(BaseCrawler):
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.rss_url = INVESTING_RSS_FEEDS.get(symbol)

    def crawl(self) -> List[Dict]:
        try:
            res = requests.get(self.rss_url, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code != 200:
                print(f"❌ 요청 실패: status {res.status_code}")
                return []

            root = ET.fromstring(res.content)
            items = root.find("channel").findall("item")
            news_list = []

            for item in items[:2]:  
                title = item.findtext("title")
                url = item.findtext("link")
                summary = item.findtext("description")
                pub_date_raw = item.findtext("pubDate")

                if not title or not url:
                    continue

                content_hash = self.generate_hash(title)
                published_at = date_parser.parse(pub_date_raw) if pub_date_raw else None
                if published_at and published_at.tzinfo:
                    published_at = published_at.replace(tzinfo=None)


                news_list.append({
                    "title": title.strip(),
                    "url": url.strip(),
                    "source": "investing.com",
                    "summary": summary.strip() if summary else None,
                    "html": "",
                    "symbol": self.symbol,
                    "content_hash": content_hash,
                    "crawled_at": self.get_crawled_at(),
                    "published_at": published_at
                })

            return news_list

        except Exception as e:
            print(f"❌ 파싱 중 오류 발생: {e}")
            return []

    def process_all(self):
        results = self.crawl()
        processor = NewsProcessor(results)
        processor.run()