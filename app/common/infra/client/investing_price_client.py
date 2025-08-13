"""
Investing.com 가격 데이터 클라이언트
브라우저 시뮬레이션을 적용하여 API 제한을 우회
"""

import requests
import random
import time
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from bs4 import BeautifulSoup


class InvestingPriceClient:
    """Investing.com 가격 데이터 클라이언트"""
    
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
        "application/json, text/plain, */*",
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
        "https://www.investing.com/indices/",
        "https://www.investing.com/currencies/",
        "https://www.investing.com/commodities/",
        "https://www.google.com/",
        "https://www.bing.com/",
    ]

    def __init__(self):
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

    def _get_random_headers(self, symbol: str = None) -> Dict[str, str]:
        """요청마다 랜덤 헤더 생성"""
        headers = {}
        
        # User-Agent 랜덤 변경
        headers["User-Agent"] = random.choice(self.USER_AGENTS)
        
        # Accept 헤더 랜덤 변경
        headers["Accept"] = random.choice(self.ACCEPT_HEADERS)
        
        # Accept-Language 랜덤 변경
        headers["Accept-Language"] = random.choice(self.ACCEPT_LANGUAGES)
        
        # Referer 설정 (Investing.com 관련 페이지로)
        if symbol:
            referer = f"https://www.investing.com/indices/{symbol.lower()}"
        else:
            referer = random.choice(self.REFERERS)
        headers["Referer"] = referer
        
        return headers

    def _rate_limit_delay(self):
        """요청 간 랜덤 지연 (API 제한 방지)"""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        # 최소 1초, 최대 3초 랜덤 지연 (Investing.com은 더 신중하게)
        min_delay = 1.0
        max_delay = 3.0
        
        if time_since_last < min_delay:
            delay = random.uniform(min_delay - time_since_last, max_delay)
            time.sleep(delay)
        
        self._last_request_time = time.time()

    def _make_request(self, url: str, symbol: str = None) -> Optional[requests.Response]:
        """브라우저 시뮬레이션 요청 수행"""
        try:
            # 요청 간 지연
            self._rate_limit_delay()
            
            # 랜덤 헤더 설정
            headers = self._get_random_headers(symbol)
            
            # 요청 수행
            response = self.session.get(url, headers=headers, timeout=15)
            
            # 429 에러 시 재시도 (최대 3회)
            retry_count = 0
            while response.status_code == 429 and retry_count < 3:
                print(f"⚠️ {symbol} Investing API 제한 감지, {retry_count + 1}회 재시도 중...")
                time.sleep(random.uniform(3, 8))  # 더 긴 지연
                headers = self._get_random_headers(symbol)  # 헤더 재설정
                response = self.session.get(url, headers=headers, timeout=15)
                retry_count += 1
            
            return response
            
        except Exception as e:
            print(f"❌ {symbol} Investing 요청 실패: {e}")
            return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        """현재 가격 조회"""
        try:
            # Investing.com 심볼 URL 생성
            url = f"https://www.investing.com/indices/{symbol.lower()}"
            
            res = self._make_request(url, symbol)
            if not res:
                return None
                
            if res.status_code != 200:
                print(f"❌ {symbol} Investing 가격 조회 실패: status {res.status_code}")
                return None

            soup = BeautifulSoup(res.content, 'html.parser')
            
            # 가격 요소 찾기 (Investing.com의 실제 구조에 맞게 수정 필요)
            price_element = soup.find('span', {'data-test': 'instrument-price-last'})
            if price_element:
                price_text = price_element.get_text().strip()
                # 쉼표 제거하고 숫자만 추출
                price = float(price_text.replace(',', ''))
                print(f"📊 {symbol} Investing 현재가: {price}")
                return price
            else:
                print(f"❌ {symbol} Investing 가격 요소를 찾을 수 없음")
                return None

        except Exception as e:
            print(f"❌ {symbol} Investing 가격 파싱 실패: {e}")
            return None

    def get_historical_data(self, symbol: str, period: str = "1mo") -> Optional[pd.DataFrame]:
        """과거 데이터 조회 (Investing.com API 사용)"""
        try:
            # Investing.com API URL (실제 API 엔드포인트에 맞게 수정 필요)
            url = f"https://api.investing.com/api/financialdata/historical/{symbol}"
            
            res = self._make_request(url, symbol)
            if not res:
                return None
                
            if res.status_code != 200:
                print(f"❌ {symbol} Investing 과거 데이터 조회 실패: status {res.status_code}")
                return None

            data = res.json()
            
            # Investing.com API 응답 구조에 맞게 파싱 (실제 구조에 맞게 수정 필요)
            if 'data' in data and 'prices' in data['data']:
                prices = data['data']['prices']
                df = pd.DataFrame(prices)
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
                df.set_index('datetime', inplace=True)
                
                print(f"📊 {symbol} Investing 과거 데이터 수집: {len(df)}개")
                return df
            else:
                print(f"❌ {symbol} Investing 과거 데이터 형식 오류")
                return None

        except Exception as e:
            print(f"❌ {symbol} Investing 과거 데이터 파싱 실패: {e}")
            return None

    def get_market_overview(self) -> Optional[Dict[str, Any]]:
        """시장 개요 데이터 조회"""
        try:
            url = "https://www.investing.com/markets/overview"
            
            res = self._make_request(url)
            if not res:
                return None
                
            if res.status_code != 200:
                print(f"❌ Investing 시장 개요 조회 실패: status {res.status_code}")
                return None

            soup = BeautifulSoup(res.content, 'html.parser')
            
            # 시장 지수들 추출 (실제 구조에 맞게 수정 필요)
            market_data = {}
            
            # 주요 지수들 찾기
            indices = soup.find_all('div', class_='market-index')
            for index in indices:
                name = index.find('span', class_='name')
                value = index.find('span', class_='value')
                if name and value:
                    market_data[name.get_text().strip()] = value.get_text().strip()
            
            print(f"📊 Investing 시장 개요 데이터 수집: {len(market_data)}개 지수")
            return market_data

        except Exception as e:
            print(f"❌ Investing 시장 개요 파싱 실패: {e}")
            return None
