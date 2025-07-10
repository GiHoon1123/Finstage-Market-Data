import requests
import random
import pandas as pd
from typing import Optional, Tuple
from datetime import datetime


class YahooPriceClient:
    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/"
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Mozilla/5.0 (X11; Linux x86_64)"
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": random.choice(self.USER_AGENTS)
        })

    def get_all_time_high(self, symbol: str) -> Tuple[Optional[float], Optional[datetime]]:
        url = f"{self.BASE_URL}{symbol}?range=max&interval=1d"
        try:
            res = self.session.get(url)
            res.raise_for_status()
            data = res.json()

            timestamps = data["chart"]["result"][0]["timestamp"]
            highs = data["chart"]["result"][0]["indicators"]["quote"][0]["high"]

            df = pd.DataFrame({
                "timestamp": timestamps,
                "high": highs
            }).dropna()

            if df.empty:
                return None, None

            idxmax = df["high"].idxmax()
            return df.loc[idxmax, "high"], datetime.fromtimestamp(df.loc[idxmax, "timestamp"])
        except Exception as e:
            print(f"❌ {symbol} 최고가 요청 실패: {e}")
            return None, None

    def get_previous_close(self, symbol: str) -> Tuple[Optional[float], Optional[datetime]]:
        url = f"{self.BASE_URL}{symbol}?range=5d&interval=1d"
        try:
            res = self.session.get(url)
            res.raise_for_status()
            data = res.json()

            timestamps = data["chart"]["result"][0]["timestamp"]
            closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]

            df = pd.DataFrame({
                "timestamp": timestamps,
                "close": closes
            }).dropna()

            if len(df) < 2:
                return None, None

            prev_row = df.iloc[-2]
            return prev_row["close"], datetime.fromtimestamp(prev_row["timestamp"])
        except Exception as e:
            print(f"❌ {symbol} 전일 종가 요청 실패: {e}")
            return None, None
    
    def get_previous_low(self, symbol: str) -> Tuple[Optional[float], Optional[datetime]]:
        url = f"{self.BASE_URL}{symbol}?range=5d&interval=1d"
        try:
            res = self.session.get(url)
            res.raise_for_status()
            data = res.json()

            timestamps = data["chart"]["result"][0]["timestamp"]
            lows = data["chart"]["result"][0]["indicators"]["quote"][0]["low"]

            df = pd.DataFrame({
                "timestamp": timestamps,
                "low": lows
            }).dropna()

            if len(df) < 2:
                return None, None

            prev_row = df.iloc[-2]
            return prev_row["low"], datetime.fromtimestamp(prev_row["timestamp"])
        except Exception as e:
            print(f"❌ {symbol} 전일 저점 요청 실패: {e}")
            return None, None
        
    def get_previous_high(self, symbol: str) -> Tuple[Optional[float], Optional[datetime]]:
        url = f"{self.BASE_URL}{symbol}?range=5d&interval=1d"
        try:
            res = self.session.get(url)
            res.raise_for_status()
            data = res.json()

            timestamps = data["chart"]["result"][0]["timestamp"]
            highs = data["chart"]["result"][0]["indicators"]["quote"][0]["high"]

            df = pd.DataFrame({
                "timestamp": timestamps,
                "high": highs
            }).dropna()

            if len(df) < 2:
                return None, None

            prev_row = df.iloc[-2]
            return prev_row["high"], datetime.fromtimestamp(prev_row["timestamp"])

        except Exception as e:
            print(f"❌ {symbol} 전일 고점 요청 실패: {e}")
            return None, None

    def get_latest_minute_price(self, symbol: str) -> Optional[float]:
        url = f"{self.BASE_URL}{symbol}?range=1d&interval=1m"
        try:
            res = self.session.get(url)
            res.raise_for_status()
            data = res.json()

            timestamps = data["chart"]["result"][0]["timestamp"]
            closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]

            df = pd.DataFrame({
                "timestamp": timestamps,
                "close": closes
            }).dropna()

            if df.empty:
                print(f"❌ {symbol} 1분봉 데이터 없음")
                return None

            latest = df.iloc[-1]
            price = latest["close"]
            timestamp = datetime.fromtimestamp(latest["timestamp"])
            print(f"📉 {symbol} 최근 1분봉: {price} @ {timestamp}")
            return price
        except Exception as e:
            print(f"❌ {symbol} 1분봉 수집 실패: {e}")
            return None
