import requests
import random
import pandas as pd
from typing import Optional, Tuple, Dict, Any
from datetime import datetime


class YahooPriceClient:
    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/"
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Mozilla/5.0 (X11; Linux x86_64)",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": random.choice(self.USER_AGENTS)})
        # 캐시 추가 - 동일한 요청에 대한 중복 호출 방지
        self._cache: Dict[str, Any] = {}

    def get_all_time_high(
        self, symbol: str
    ) -> Tuple[Optional[float], Optional[datetime]]:
        url = f"{self.BASE_URL}{symbol}?range=max&interval=1d"
        try:
            res = self.session.get(url)
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
            res = self.session.get(url)
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
            res = self.session.get(url)
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
            res = self.session.get(url)
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

    def get_latest_minute_price(self, symbol: str) -> Optional[float]:
        # 캐시 키 생성
        cache_key = f"latest_minute_{symbol}"

        # 캐시에 있으면 캐시된 값 반환 (30초 이내 요청은 캐시 사용)
        if cache_key in self._cache:
            cached_data = self._cache[cache_key]
            cache_time = cached_data.get("timestamp", 0)
            if (datetime.now().timestamp() - cache_time) < 30:
                print(f"📊 {symbol} 캐시된 1분봉 사용: {cached_data['price']}")
                return cached_data["price"]

        url = f"{self.BASE_URL}{symbol}?range=1d&interval=1m"
        try:
            res = self.session.get(url)
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
            res = self.session.get(url)
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
            res = self.session.get(url)
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
            res = self.session.get(url)
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
        from datetime import datetime, timedelta
        import time

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

                res = self.session.get(url)
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
