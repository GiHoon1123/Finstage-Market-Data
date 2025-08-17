import requests
import xml.etree.ElementTree as ET
import random
import time
from typing import List, Dict, Optional
from dateutil import parser as date_parser
from app.news_crawler.service.base import BaseCrawler
from app.news_crawler.service.news_processor import NewsProcessor
from app.common.constants.investing_config import INVESTING_RSS_FEEDS
from app.common.utils.memory_cache import cache_result
from app.common.utils.memory_optimizer import memory_monitor


class InvestingNewsCrawler(BaseCrawler):
    # 다양한 브라우저 User-Agent (더 현실적인 시뮬레이션)
    USER_AGENTS = [
        # Chrome (Windows)
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        
        # Chrome (Mac)
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        
        # Firefox (Windows)
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
        
        # Firefox (Mac)
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:119.0) Gecko/20100101 Firefox/119.0",
        
        # Safari (Mac)
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        
        # Edge (Windows)
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    ]
    
    # 브라우저가 보내는 Accept 헤더들
    ACCEPT_HEADERS = [
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "application/rss+xml, application/xml, text/xml, */*",
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    ]
    
    # 언어 설정
    ACCEPT_LANGUAGES = [
        "en-US,en;q=0.9",
        "en-GB,en;q=0.9",
        "en-CA,en;q=0.9",
        "ko-KR,ko;q=0.9,en;q=0.8",
        "ja-JP,ja;q=0.9,en;q=0.8",
    ]
    
    # Referer 헤더 (Investing.com 관련 페이지들)
    REFERERS = [
        "https://www.investing.com/",
        "https://www.investing.com/news/",
        "https://www.investing.com/economic-calendar/",
        "https://www.investing.com/markets/",
        "https://www.google.com/",
        "https://www.bing.com/",
    ]

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.rss_url = INVESTING_RSS_FEEDS.get(symbol)
        self.session = requests.Session()
        self._last_request_time = 0
        self._setup_session()

    def _setup_session(self):
        """세션을 브라우저처럼 설정"""
        # 랜덤 User-Agent 설정
        user_agent = random.choice(self.USER_AGENTS)
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": random.choice(self.ACCEPT_HEADERS),
            "Accept-Language": random.choice(self.ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        })

    def _get_random_headers(self) -> Dict[str, str]:
        """요청마다 랜덤 헤더 생성"""
        headers = {}
        
        # User-Agent 랜덤 변경
        headers["User-Agent"] = random.choice(self.USER_AGENTS)
        
        # Accept 헤더 랜덤 변경
        headers["Accept"] = random.choice(self.ACCEPT_HEADERS)
        
        # Accept-Language 랜덤 변경
        headers["Accept-Language"] = random.choice(self.ACCEPT_LANGUAGES)
        
        # Referer 설정 (Investing.com 관련 페이지로)
        referer = random.choice(self.REFERERS)
        headers["Referer"] = referer
        
        return headers

    def _rate_limit_delay(self):
        """요청 간 랜덤 지연 (API 제한 방지)"""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        # 최소 1초, 최대 3초 랜덤 지연 (뉴스 크롤링은 더 신중하게)
        min_delay = 1.0
        max_delay = 3.0
        
        if time_since_last < min_delay:
            delay = random.uniform(min_delay - time_since_last, max_delay)
            time.sleep(delay)
        
        self._last_request_time = time.time()

    def _make_request(self, url: str) -> Optional[requests.Response]:
        """브라우저 시뮬레이션 요청 수행"""
        try:
            # 요청 간 지연
            self._rate_limit_delay()
            
            # 랜덤 헤더 설정
            headers = self._get_random_headers()
            
            # 요청 수행
            response = self.session.get(url, headers=headers, timeout=15)
            
            # 429 에러 시 재시도 (최대 3회)
            retry_count = 0
            while response.status_code == 429 and retry_count < 3:
                print(f"⚠️ {self.symbol} 뉴스 API 제한 감지, {retry_count + 1}회 재시도 중...")
                time.sleep(random.uniform(3, 8))  # 더 긴 지연
                headers = self._get_random_headers()  # 헤더 재설정
                response = self.session.get(url, headers=headers, timeout=15)
                retry_count += 1
            
            return response
            
        except Exception as e:
            print(f"❌ {self.symbol} 뉴스 요청 실패: {e}")
            return None

    @cache_result(cache_name="news", ttl=300)  # 5분 캐싱
    @memory_monitor
    def crawl(self) -> List[Dict]:
        try:
            res = self._make_request(self.rss_url)
            if not res:
                return []
                
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
    def process_all(self, telegram_enabled: bool = False):
        results = self.crawl()
        processor = NewsProcessor(results, telegram_enabled=telegram_enabled)
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
