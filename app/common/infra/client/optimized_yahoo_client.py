"""
최적화된 Yahoo Finance API 클라이언트
"""

import time
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta

import yfinance as yf
from app.common.utils.api_client import adaptive_retry
from app.common.utils.parallel_executor import measure_execution_time, ParallelExecutor


class OptimizedYahooPriceClient:
    """최적화된 Yahoo Finance API 클라이언트"""

    def __init__(self):
        # 메모리 캐시 (심볼별 최근 데이터)
        self.price_cache = {}
        self.cache_ttl = 300  # 5분
        self.cache_timestamps = {}

    def _is_cache_valid(self, symbol: str) -> bool:
        """캐시 유효성 확인"""
        if symbol not in self.cache_timestamps:
            return False

        elapsed = time.time() - self.cache_timestamps[symbol]
        return elapsed < self.cache_ttl

    @adaptive_retry(max_retries=3, base_delay=2.0)
    def get_current_price(self, symbol: str) -> Optional[float]:
        """현재 가격 조회 (캐싱 적용)"""
        # 캐시 확인
        if symbol in self.price_cache and self._is_cache_valid(symbol):
            return self.price_cache[symbol]

        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")

            if data.empty:
                return None

            price = data["Close"].iloc[-1]

            # 캐시 업데이트
            self.price_cache[symbol] = price
            self.cache_timestamps[symbol] = time.time()

            return price

        except Exception as e:
            print(f"❌ {symbol} 현재 가격 조회 실패: {e}")
            return None

    @adaptive_retry(max_retries=3, base_delay=2.0)
    def get_historical_data(
        self, symbol: str, period: str = "1mo", interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """과거 데이터 조회"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)

            if data.empty:
                print(f"⚠️ {symbol} {period} 기간 데이터 없음")
                return None

            return data

        except Exception as e:
            print(f"❌ {symbol} 과거 데이터 조회 실패: {e}")
            return None

    @measure_execution_time
    def get_multi_symbol_data(
        self, symbols: List[str], period: str = "1mo", interval: str = "1d"
    ) -> Dict[str, pd.DataFrame]:
        """여러 심볼 데이터 한번에 조회 (병렬 처리)"""
        executor = ParallelExecutor(max_workers=5)

        def fetch_data(symbol):
            data = self.get_historical_data(symbol, period, interval)
            return symbol, data

        tasks = [(fetch_data, symbol) for symbol in symbols]
        results = executor.run_parallel(tasks)

        # 결과 딕셔너리로 변환
        data_dict = {}
        for result in results:
            if result is not None:
                symbol, data = result
                if data is not None:
                    data_dict[symbol] = data

        return data_dict

    @adaptive_retry(max_retries=3, base_delay=2.0)
    def get_yearly_data(self, symbol: str, year: int) -> Optional[pd.DataFrame]:
        """특정 연도의 일별 데이터 조회"""
        try:
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"

            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date, interval="1d")

            if data.empty:
                print(f"⚠️ {symbol} {year}년 데이터 없음")
                return None

            return data

        except Exception as e:
            print(f"❌ {symbol} {year}년 데이터 조회 실패: {e}")
            return None

    @measure_execution_time
    def get_multi_year_data(
        self, symbol: str, start_year: int, end_year: int
    ) -> Optional[pd.DataFrame]:
        """여러 연도의 데이터 조회 및 병합"""
        all_dataframes = []

        for year in range(start_year, end_year + 1):
            try:
                year_df = self.get_yearly_data(symbol, year)

                if year_df is not None and not year_df.empty:
                    all_dataframes.append(year_df)
                    print(f"   ✅ {year}년: {len(year_df)}개 데이터 수집")
                else:
                    print(f"   ⚠️ {year}년: 데이터 없음")

            except Exception as e:
                print(f"   ❌ {year}년 데이터 수집 실패: {e}")
                continue

        if not all_dataframes:
            print(f"❌ {symbol} 모든 연도 데이터 수집 실패")
            return None

        # 모든 연도 데이터 합치기
        combined_df = pd.concat(all_dataframes, ignore_index=False)

        # 중복 제거 (같은 날짜 데이터가 있을 수 있음)
        combined_df = combined_df.loc[~combined_df.index.duplicated(keep="first")]

        # 시간순 정렬
        combined_df = combined_df.sort_index()

        return combined_df
