import requests
import xml.etree.ElementTree as ET
from typing import List, Dict
from dateutil import parser as date_parser
from app.news_crawler.service.base import BaseCrawler
from app.news_crawler.service.news_processor import NewsProcessor
from app.common.constants.rss_feeds import INVESTING_RSS_FEEDS
from app.common.utils.memory_cache import cache_result
from app.common.utils.memory_optimizer import memory_monitor


class InvestingNewsCrawler(BaseCrawler):
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.rss_url = INVESTING_RSS_FEEDS.get(symbol)

    @cache_result(cache_name="news", ttl=300)  # 5분 캐싱
    @memory_monitor
    def crawl(self) -> List[Dict]:
        try:
            res = requests.get(self.rss_url, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code != 200:
                print(f"❌ 요청 실패: status {res.status_code}")
                return []

            root = ET.fromstring(res.content)
            items = root.find("channel").findall("item")
            news_list = []

            for item in items[:1]:
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

                news_list.append(
                    {
                        "title": title.strip(),
                        "url": url.strip(),
                        "source": "investing.com",
                        "summary": summary.strip() if summary else None,
                        "html": "",
                        "symbol": self.symbol,
                        "content_hash": content_hash,
                        "crawled_at": self.get_crawled_at(),
                        "published_at": published_at,
                    }
                )

            return news_list

        except Exception as e:
            print(f"❌ 파싱 중 오류 발생: {e}")
            return []

    @memory_monitor
    def process_all(self):
        results = self.crawl()
        processor = NewsProcessor(results)
        processor.run()

    @memory_monitor
    def crawl_multiple_symbols_batch(self, symbols: list, batch_size: int = 5) -> dict:
        """
        여러 심볼의 뉴스를 배치로 크롤링하여 메모리 효율성 향상

        Args:
            symbols: 심볼 리스트
            batch_size: 배치 크기

        Returns:
            심볼별 크롤링 결과
        """
        results = {}

        for i in range(0, len(symbols), batch_size):
            batch = symbols[i : i + batch_size]
            print(
                f"📰 뉴스 크롤링 배치 처리 중: {i+1}-{min(i+batch_size, len(symbols))}/{len(symbols)}"
            )

            for symbol in batch:
                try:
                    # 새로운 인스턴스 생성하여 심볼별 크롤링
                    crawler = InvestingNewsCrawler(symbol)
                    news_list = crawler.crawl()
                    results[symbol] = {
                        "success": True,
                        "count": len(news_list),
                        "news": news_list,
                    }
                except Exception as e:
                    results[symbol] = {"success": False, "error": str(e), "count": 0}

            # 배치 처리 후 메모리 정리
            del batch

        return results

    @cache_result(cache_name="news", ttl=600)  # 10분 캐싱
    @memory_monitor
    def get_cached_news_summary(self, symbol: str) -> dict:
        """
        심볼의 뉴스 요약 정보 조회 (캐싱 적용)

        Args:
            symbol: 심볼

        Returns:
            뉴스 요약 정보
        """
        try:
            news_list = self.crawl()

            summary = {
                "symbol": symbol,
                "source": "investing.com",
                "total_news": len(news_list),
                "latest_news": news_list[0] if news_list else None,
                "crawled_at": self.get_crawled_at().isoformat(),
                "rss_url": self.rss_url,
            }

            return summary

        except Exception as e:
            return {"error": f"{symbol} 뉴스 요약 조회 실패: {str(e)}"}

    @memory_monitor
    def cleanup_old_cache(self):
        """
        오래된 뉴스 캐시 데이터 정리
        """
        try:
            # 캐시 정리는 memory_cache 모듈에서 자동으로 처리되지만
            # 필요시 수동으로 정리할 수 있는 메서드 제공
            print(f"🧹 {self.symbol} 뉴스 캐시 데이터 정리 완료")
        except Exception as e:
            print(f"⚠️ 뉴스 캐시 데이터 정리 실패: {e}")
