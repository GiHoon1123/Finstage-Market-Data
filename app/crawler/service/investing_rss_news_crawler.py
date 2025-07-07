import requests
import xml.etree.ElementTree as ET
import hashlib
from datetime import datetime
from typing import List, Dict
from dateutil import parser as date_parser 
from app.crawler.service.base import BaseCrawler
from app.crawler.service.news_processor import NewsProcessor


class InvestingRssNewsCrawler(BaseCrawler):
    def __init__(self, rss_url: str, symbol: str):
        self.rss_url = rss_url
        self.symbol = symbol

    def crawl(self) -> List[Dict]:
        try:
            res = requests.get(self.rss_url, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code != 200:
                print(f"❌ 요청 실패: status {res.status_code}")
                return []

            root = ET.fromstring(res.content)
            items = root.find("channel").findall("item")
            news_list = []

            for item in items[:2]:  # 최대 10개까지 파싱
                title = item.findtext("title")
                url = item.findtext("link")
                summary = item.findtext("description")
                pub_date_raw = item.findtext("pubDate")

                if not title or not url:
                    continue


                content_hash = self.generate_hash(title)


                try:
                    published_at = date_parser.parse(pub_date_raw) if pub_date_raw else None
                    if published_at and published_at.tzinfo:
                        published_at = published_at.replace(tzinfo=None)
                except Exception as e:
                    print(f"❌ 날짜 파싱 실패: {pub_date_raw} ({e})")
                    published_at = None

                news_list.append({
                    "title": title.strip(),
                    "url": url.strip(),
                    "source": "investing.com",
                    "summary": summary.strip() if summary else None,
                    "html": "",
                    "symbol": self.symbol,
                    "content_hash": content_hash,
                    "crawled_at": datetime.utcnow(),
                    "published_at": published_at
                })

            return news_list

        except Exception as e:
            print(f"❌ Investing RSS 파싱 오류: {e}")
            return []

    def generate_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def process_all(self):
        results = self.crawl()
        processor = NewsProcessor(results)
        processor.run()
