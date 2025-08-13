import requests
import random
import pandas as pd
import time
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta


class YahooPriceClient:
    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/"
    
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
    
    # Referer 헤더 (Yahoo Finance 관련 페이지들)
    REFERERS = [
        "https://finance.yahoo.com/",
        "https://finance.yahoo.com/quote/",
        "https://finance.yahoo.com/chart/",
        "https://finance.yahoo.com/portfolio/",
        "https://www.google.com/",
        "https://www.bing.com/",
    ]

    def __init__(self):
        self.session = requests.Session()
        self._setup_session()
        # 캐시 추가 - 동일한 요청에 대한 중복 호출 방지
        self._cache: Dict[str, Any] = {}
        self._last_request_time = 0

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
        
        # Referer 설정 (심볼이 있으면 해당 심볼 페이지로)
        if symbol:
            referer = f"https://finance.yahoo.com/quote/{symbol}"
        else:
            referer = random.choice(self.REFERERS)
        headers["Referer"] = referer
        
        return headers

    def _rate_limit_delay(self):
        """요청 간 랜덤 지연 (API 제한 방지)"""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        # 최소 0.5초, 최대 2초 랜덤 지연
        min_delay = 0.5
        max_delay = 2.0
        
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
            response = self.session.get(url, headers=headers, timeout=10)
            
            # 429 에러 시 재시도 (최대 3회)
            retry_count = 0
            while response.status_code == 429 and retry_count < 3:
                print(f"⚠️ {symbol} API 제한 감지, {retry_count + 1}회 재시도 중...")
                time.sleep(random.uniform(2, 5))  # 더 긴 지연
                headers = self._get_random_headers(symbol)  # 헤더 재설정
                response = self.session.get(url, headers=headers, timeout=10)
                retry_count += 1
            
            return response
            
        except Exception as e:
            print(f"❌ {symbol} 요청 실패: {e}")
            return None

    def get_all_time_high(
        self, symbol: str
    ) -> Tuple[Optional[float], Optional[datetime]]:
        url = f"{self.BASE_URL}{symbol}?range=max&interval=1d"
        try:
            res = self._make_request(url, symbol)
            if not res:
                return None, None
                
            res.raise_for_status()
            data = res.json()

            # 데이터 유효성 검사 추가
            if (
                not data.get("chart")
                or not data["chart"].get("result")
                or not data["chart"]["result"][0].get("indicators")
            ):
                print(f"❌ {symbol} 최고가 데이터 형식 오류")
                return None, None

            timestamps = data["chart"]["result"][0]["timestamp"]
            highs = data["chart"]["result"][0]["indicators"]["quote"][0]["high"]

            df = pd.DataFrame({"timestamp": timestamps, "high": highs}).dropna()

            if df.empty:
                return None, None

            idxmax = df["high"].idxmax()
            return df.loc[idxmax, "high"], datetime.fromtimestamp(
                df.loc[idxmax, "timestamp"]
            )
        except Exception as e:
            print(f"❌ {symbol} 최고가 요청 실패: {e}")
            return None, None

    def get_previous_close(
        self, symbol: str
    ) -> Tuple[Optional[float], Optional[datetime]]:
        url = f"{self.BASE_URL}{symbol}?range=5d&interval=1d"
        try:
            res = self._make_request(url, symbol)
            if not res:
                return None, None
                
            res.raise_for_status()
            data = res.json()

            # 데이터 유효성 검사 추가
            if (
                not data.get("chart")
                or not data["chart"].get("result")
                or not data["chart"]["result"][0].get("indicators")
            ):
                print(f"❌ {symbol} 전일 종가 데이터 형식 오류")
                return None, None

            timestamps = data["chart"]["result"][0]["timestamp"]
            closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]

            df = pd.DataFrame({"timestamp": timestamps, "close": closes}).dropna()

            if len(df) < 2:
                return None, None

            prev_row = df.iloc[-2]
            return prev_row["close"], datetime.fromtimestamp(prev_row["timestamp"])
        except Exception as e:
            print(f"❌ {symbol} 전일 종가 요청 실패: {e}")
            return None, None

    def get_previous_low(
        self, symbol: str
    ) -> Tuple[Optional[float], Optional[datetime]]:
        url = f"{self.BASE_URL}{symbol}?range=5d&interval=1d"
        try:
            res = self._make_request(url, symbol)
            if not res:
                return None, None
                
            res.raise_for_status()
            data = res.json()

            # 데이터 유효성 검사 추가
            if (
                not data.get("chart")
                or not data["chart"].get("result")
                or not data["chart"]["result"][0].get("indicators")
            ):
                print(f"❌ {symbol} 전일 저점 데이터 형식 오류")
                return None, None

            timestamps = data["chart"]["result"][0]["timestamp"]
            lows = data["chart"]["result"][0]["indicators"]["quote"][0]["low"]

            df = pd.DataFrame({"timestamp": timestamps, "low": lows}).dropna()

            if len(df) < 2:
                return None, None

            prev_row = df.iloc[-2]
            return prev_row["low"], datetime.fromtimestamp(prev_row["timestamp"])
        except Exception as e:
            print(f"❌ {symbol} 전일 저점 요청 실패: {e}")
            return None, None

    def get_previous_high(
        self, symbol: str
    ) -> Tuple[Optional[float], Optional[datetime]]:
        url = f"{self.BASE_URL}{symbol}?range=5d&interval=1d"
        try:
            res = self._make_request(url, symbol)
            if not res:
                return None, None
                
            res.raise_for_status()
            data = res.json()

            # 데이터 유효성 검사 추가
            if (
                not data.get("chart")
                or not data["chart"].get("result")
                or not data["chart"]["result"][0].get("indicators")
            ):
                print(f"❌ {symbol} 전일 고점 데이터 형식 오류")
                return None, None

            timestamps = data["chart"]["result"][0]["timestamp"]
            highs = data["chart"]["result"][0]["indicators"]["quote"][0]["high"]

            df = pd.DataFrame({"timestamp": timestamps, "high": highs}).dropna()

            if len(df) < 2:
                return None, None

            prev_row = df.iloc[-2]
            return prev_row["high"], datetime.fromtimestamp(prev_row["timestamp"])

        except Exception as e:
            print(f"❌ {symbol} 전일 고점 요청 실패: {e}")
            return None, None

    def get_latest_minute_price(
        self, symbol: str, ignore_cache: bool = False
    ) -> Optional[float]:
        # 캐시 키 생성
        cache_key = f"latest_minute_{symbol}"

        # 캐시 무시 플래그가 False일 때만 캐시 확인
        if not ignore_cache and cache_key in self._cache:
            cached_data = self._cache[cache_key]
            cache_time = cached_data.get("timestamp", 0)
            if (datetime.now().timestamp() - cache_time) < 30:
                print(f"📊 {symbol} 캐시된 1분봉 사용: {cached_data['price']}")
                return cached_data["price"]

        url = f"{self.BASE_URL}{symbol}?range=1d&interval=1m"
        try:
            res = self._make_request(url, symbol)
            if not res:
                return None
                
            res.raise_for_status()
            data = res.json()

            # 데이터 유효성 검사 추가
            if (
                not data.get("chart")
                or not data["chart"].get("result")
                or not data["chart"]["result"][0].get("indicators")
            ):
                print(f"❌ {symbol} 1분봉 데이터 형식 오류")
                return None

            timestamps = data["chart"]["result"][0]["timestamp"]
            quotes = data["chart"]["result"][0]["indicators"]["quote"][0]

            # close 데이터가 없는 경우 처리
            if "close" not in quotes:
                print(f"❌ {symbol} 1분봉 종가 데이터 없음")
                return None

            closes = quotes["close"]

            df = pd.DataFrame({"timestamp": timestamps, "close": closes}).dropna()

            if df.empty:
                print(f"❌ {symbol} 1분봉 데이터 없음")
                return None

            latest = df.iloc[-1]
            price = latest["close"]
            timestamp = datetime.fromtimestamp(latest["timestamp"])
            print(f"📉 {symbol} 최근 1분봉: {price} @ {timestamp}")

            # 캐시에 저장
            self._cache[cache_key] = {
                "price": price,
                "timestamp": datetime.now().timestamp(),
            }

            return price
        except Exception as e:
            print(f"❌ {symbol} 1분봉 수집 실패: {e}")
            return None

    def get_minute_data(
        self, symbol: str, period: str = "5d"
    ) -> Optional[pd.DataFrame]:
        """1분봉 데이터 수집 (기술적 지표 계산용)"""
        url = f"{self.BASE_URL}{symbol}?range={period}&interval=1m"
        try:
            res = self._make_request(url, symbol)
            if not res:
                return None
                
            res.raise_for_status()
            data = res.json()

            # 데이터 유효성 검사 추가
            if (
                not data.get("chart")
                or not data["chart"].get("result")
                or not data["chart"]["result"][0].get("indicators")
            ):
                print(f"❌ {symbol} 1분봉 데이터 형식 오류")
                return None

            timestamps = data["chart"]["result"][0]["timestamp"]
            quotes = data["chart"]["result"][0]["indicators"]["quote"][0]

            # 필수 필드 확인
            required_fields = ["open", "high", "low", "close", "volume"]
            for field in required_fields:
                if field not in quotes:
                    print(f"❌ {symbol} 1분봉 데이터 필드 누락: {field}")
                    return None

            df = pd.DataFrame(
                {
                    "timestamp": timestamps,
                    "open": quotes["open"],
                    "high": quotes["high"],
                    "low": quotes["low"],
                    "close": quotes["close"],
                    "volume": quotes["volume"],
                }
            ).dropna()

            if df.empty:
                print(f"❌ {symbol} 1분봉 데이터 없음")
                return None

            # 데이터 포인트가 너무 적으면 경고
            if len(df) < 10:
                print(
                    f"⚠️ {symbol} 1분봉 데이터 부족: {len(df)}개 (시장 시간 확인 필요)"
                )

            df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
            print(f"📊 {symbol} 1분봉 데이터 수집: {len(df)}개")
            return df
        except Exception as e:
            print(f"❌ {symbol} 1분봉 데이터 수집 실패: {e}")
            return None

    def get_15minute_data(
        self, symbol: str, period: str = "5d"
    ) -> Optional[pd.DataFrame]:
        """15분봉 데이터 수집 (기술적 지표 계산용)"""
        url = f"{self.BASE_URL}{symbol}?range={period}&interval=15m"
        try:
            res = self._make_request(url, symbol)
            if not res:
                return None
                
            res.raise_for_status()
            data = res.json()

            # 데이터 유효성 검사 추가
            if (
                not data.get("chart")
                or not data["chart"].get("result")
                or not data["chart"]["result"][0].get("indicators")
            ):
                print(f"❌ {symbol} 15분봉 데이터 형식 오류")
                return None

            timestamps = data["chart"]["result"][0]["timestamp"]
            quotes = data["chart"]["result"][0]["indicators"]["quote"][0]

            # 필수 필드 확인
            required_fields = ["open", "high", "low", "close", "volume"]
            for field in required_fields:
                if field not in quotes:
                    print(f"❌ {symbol} 15분봉 데이터 필드 누락: {field}")
                    return None

            df = pd.DataFrame(
                {
                    "timestamp": timestamps,
                    "open": quotes["open"],
                    "high": quotes["high"],
                    "low": quotes["low"],
                    "close": quotes["close"],
                    "volume": quotes["volume"],
                }
            ).dropna()

            if df.empty:
                print(f"❌ {symbol} 15분봉 데이터 없음")
                return None

            df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
            print(f"📊 {symbol} 15분봉 데이터 수집: {len(df)}개")
            return df
        except Exception as e:
            print(f"❌ {symbol} 15분봉 데이터 수집 실패: {e}")
            return None

    def get_daily_data(
        self, symbol: str, period: str = "max"
    ) -> Optional[pd.DataFrame]:
        """일봉 데이터 수집 (기술적 지표 계산용)"""

        # 10년치 데이터를 확실히 받기 위해 기간별로 분할 수집
        if period == "max":
            return self._get_historical_daily_data(symbol)

        url = f"{self.BASE_URL}{symbol}?range={period}&interval=1d"
        try:
            res = self._make_request(url, symbol)
            if not res:
                return None
                
            res.raise_for_status()
            data = res.json()

            # 데이터 유효성 검사 추가
            if (
                not data.get("chart")
                or not data["chart"].get("result")
                or not data["chart"]["result"][0].get("indicators")
            ):
                print(f"❌ {symbol} 일봉 데이터 형식 오류")
                return None

            timestamps = data["chart"]["result"][0]["timestamp"]
            quotes = data["chart"]["result"][0]["indicators"]["quote"][0]

            # 필수 필드 확인
            required_fields = ["open", "high", "low", "close", "volume"]
            for field in required_fields:
                if field not in quotes:
                    print(f"❌ {symbol} 일봉 데이터 필드 누락: {field}")
                    return None

            df = pd.DataFrame(
                {
                    "timestamp": timestamps,
                    "open": quotes["open"],
                    "high": quotes["high"],
                    "low": quotes["low"],
                    "close": quotes["close"],
                    "volume": quotes["volume"],
                }
            ).dropna()

            if df.empty:
                print(f"❌ {symbol} 일봉 데이터 없음")
                return None

            df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")

            # 인덱스를 날짜로 설정 (기존 코드와 호환성 위해)
            df.set_index("datetime", inplace=True)

            # 컬럼명을 대문자로 변경 (기존 코드와 호환성 위해)
            df.columns = ["timestamp", "Open", "High", "Low", "Close", "Volume"]

            print(f"📊 {symbol} 일봉 데이터 수집: {len(df)}개")
            return df
        except Exception as e:
            print(f"❌ {symbol} 일봉 데이터 수집 실패: {e}")
            return None

    def _get_historical_daily_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """25년치 과거 일봉 데이터를 기간별로 분할 수집 (2000년~현재)"""

        print(f"📊 {symbol} 25년치 과거 데이터 수집 시작 (2000년~현재)...")

        all_dataframes = []
        current_year = datetime.now().year

        # 🚀 2000년부터 현재까지 연도별로 수집 (25년치!)
        for year in range(2000, current_year + 1):
            try:
                # 각 연도별로 데이터 수집
                start_timestamp = int(datetime(year, 1, 1).timestamp())
                end_timestamp = int(datetime(year, 12, 31, 23, 59, 59).timestamp())

                url = f"{self.BASE_URL}{symbol}?period1={start_timestamp}&period2={end_timestamp}&interval=1d"

                print(f"   📅 {year}년 데이터 수집 중...")

                res = self._make_request(url, symbol)
                if not res:
                    continue
                    
                res.raise_for_status()
                data = res.json()

                if not data.get("chart") or not data["chart"].get("result"):
                    print(f"   ⚠️ {year}년 데이터 없음")
                    continue

                if not data["chart"]["result"][0].get("indicators"):
                    print(f"   ⚠️ {year}년 지표 데이터 없음")
                    continue

                timestamps = data["chart"]["result"][0]["timestamp"]
                quotes = data["chart"]["result"][0]["indicators"]["quote"][0]

                # 필수 필드 확인
                required_fields = ["open", "high", "low", "close", "volume"]
                missing_fields = [
                    field for field in required_fields if field not in quotes
                ]
                if missing_fields:
                    print(
                        f"   ⚠️ {year}년 데이터 필드 누락: {', '.join(missing_fields)}"
                    )
                    continue

                year_df = pd.DataFrame(
                    {
                        "timestamp": timestamps,
                        "open": quotes["open"],
                        "high": quotes["high"],
                        "low": quotes["low"],
                        "close": quotes["close"],
                        "volume": quotes["volume"],
                    }
                ).dropna()

                if not year_df.empty:
                    all_dataframes.append(year_df)
                    print(f"   ✅ {year}년: {len(year_df)}개 데이터 수집")
                else:
                    print(f"   ⚠️ {year}년: 데이터 없음")

                # API 호출 제한 방지를 위한 딜레이
                time.sleep(0.5)

            except Exception as e:
                print(f"   ❌ {year}년 데이터 수집 실패: {e}")
                continue

        if not all_dataframes:
            print(f"❌ {symbol} 모든 연도 데이터 수집 실패")
            return None

        # 모든 연도 데이터 합치기
        combined_df = pd.concat(all_dataframes, ignore_index=True)

        # 중복 제거 (같은 날짜 데이터가 있을 수 있음)
        combined_df = combined_df.drop_duplicates(subset=["timestamp"])

        # 시간순 정렬
        combined_df = combined_df.sort_values("timestamp")

        # datetime 컬럼 추가
        combined_df["datetime"] = pd.to_datetime(combined_df["timestamp"], unit="s")

        # 인덱스를 날짜로 설정 (기존 코드와 호환성 위해)
        combined_df.set_index("datetime", inplace=True)

        # 컬럼명을 대문자로 변경 (기존 코드와 호환성 위해)
        combined_df.columns = ["timestamp", "Open", "High", "Low", "Close", "Volume"]

        print(
            f"🎉 {symbol} 전체 데이터 수집 완료: {len(combined_df)}개 (2000~{current_year}) - 25년치!"
        )

        return combined_df
