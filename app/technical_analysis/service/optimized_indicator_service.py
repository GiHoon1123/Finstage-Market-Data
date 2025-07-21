"""
최적화된 기술적 지표 계산 서비스

이 파일은 주가 데이터를 받아서 다양한 기술적 지표를 계산하는 함수들을 제공합니다.
각 함수는 pandas DataFrame을 입력받아 계산된 지표값을 반환합니다.

최적화 포인트:
1. 메모리 캐싱 적용
2. 증분 계산 지원
3. 성능 측정 데코레이터 적용
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime
from functools import lru_cache

from app.common.utils.parallel_executor import measure_execution_time


class OptimizedIndicatorService:
    """최적화된 기술적 지표 계산 서비스"""

    def __init__(self):
        # 계산 결과 캐시
        self.ma_cache = {}
        self.rsi_cache = {}
        self.bollinger_cache = {}

    # =========================================================================
    # 이동평균선 (Moving Average) 계산
    # =========================================================================

    @measure_execution_time
    def calculate_moving_average(
        self, prices: pd.Series, period: int, use_cache: bool = True
    ) -> pd.Series:
        """
        이동평균선 계산 (캐싱 적용)

        Args:
            prices: 가격 데이터 (보통 종가)
            period: 평균을 계산할 기간 (예: 20일, 50일, 200일)
            use_cache: 캐시 사용 여부

        Returns:
            이동평균값들의 시리즈
        """
        # 캐시 키 생성
        cache_key = f"{id(prices)}_{period}"

        # 캐시 확인
        if use_cache and cache_key in self.ma_cache:
            cached_result = self.ma_cache[cache_key]

            # 새 데이터가 추가된 경우 증분 계산
            if len(prices) > len(cached_result):
                # 기존 캐시 데이터 재사용
                existing_data = cached_result

                # 새 데이터에 대해서만 계산
                new_data = prices.iloc[len(existing_data) :]
                if len(new_data) > 0:
                    # 이전 값들도 필요하므로 충분한 데이터 확보
                    calculation_data = prices.iloc[-(len(new_data) + period) :]
                    new_ma = calculation_data.rolling(
                        window=period, min_periods=period
                    ).mean()
                    new_ma = new_ma.iloc[period:]

                    # 기존 데이터와 새 데이터 병합
                    result = pd.concat([existing_data, new_ma])

                    # 캐시 업데이트
                    self.ma_cache[cache_key] = result
                    return result
                else:
                    return existing_data

        try:
            # 전체 계산
            ma = prices.rolling(window=period, min_periods=period).mean()

            # 캐시 저장
            if use_cache:
                self.ma_cache[cache_key] = ma

            return ma

        except Exception as e:
            print(f"❌ 이동평균 계산 실패 (period={period}): {e}")
            return pd.Series()

    def detect_ma_breakout(
        self, current_price: float, current_ma: float, prev_price: float, prev_ma: float
    ) -> Optional[str]:
        """이동평균선 돌파 감지"""
        try:
            # 돌파 강도 계산 (최소 0.5% 이상 돌파해야 유의미한 신호로 인정)
            min_breakout_pct = 0.005  # 0.5%

            # 상향 돌파: 이전에는 MA 근처나 아래, 지금은 확실히 위
            if (
                prev_price <= prev_ma * 1.01  # 이전에는 MA 1% 이내 또는 아래
                and current_price > current_ma * (1 + min_breakout_pct)
            ):  # 지금은 MA 0.5% 이상 위
                breakout_strength = ((current_price - current_ma) / current_ma) * 100
                print(
                    f"🚀 상향 돌파 감지: {prev_price:.2f} → {current_price:.2f} (MA: {current_ma:.2f}, 강도: {breakout_strength:.2f}%)"
                )
                return "breakout_up"

            # 하향 돌파: 이전에는 MA 근처나 위, 지금은 확실히 아래
            elif (
                prev_price >= prev_ma * 0.99  # 이전에는 MA 1% 이내 또는 위
                and current_price < current_ma * (1 - min_breakout_pct)
            ):  # 지금은 MA 0.5% 이상 아래
                breakout_strength = ((current_ma - current_price) / current_ma) * 100
                print(
                    f"📉 하향 돌파 감지: {prev_price:.2f} → {current_price:.2f} (MA: {current_ma:.2f}, 강도: {breakout_strength:.2f}%)"
                )
                return "breakout_down"

            return None

        except Exception as e:
            print(f"❌ 이동평균 돌파 감지 실패: {e}")
            return None

    # =========================================================================
    # RSI (Relative Strength Index) 계산
    # =========================================================================

    @measure_execution_time
    def calculate_rsi(
        self, prices: pd.Series, period: int = 14, use_cache: bool = True
    ) -> pd.Series:
        """
        RSI 지표 계산 (캐싱 적용)

        Args:
            prices: 가격 데이터 (보통 종가)
            period: 계산 기간 (기본값: 14일)
            use_cache: 캐시 사용 여부

        Returns:
            RSI 값들의 시리즈 (0~100)
        """
        # 캐시 키 생성
        cache_key = f"{id(prices)}_{period}"

        # 캐시 확인
        if use_cache and cache_key in self.rsi_cache:
            cached_result = self.rsi_cache[cache_key]

            # 새 데이터가 추가된 경우 증분 계산
            if len(prices) > len(cached_result):
                # RSI는 증분 계산이 복잡하므로 일정 기간 이상 추가된 경우만 재계산
                if len(prices) - len(cached_result) > period:
                    # 전체 재계산
                    pass
                else:
                    return cached_result

        try:
            # 1. 매일의 가격 변화량 계산
            delta = prices.diff()

            # 2. 상승분과 하락분 분리
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            # 3. 지수이동평균으로 평균 상승폭/하락폭 계산
            avg_gain = gain.ewm(span=period, adjust=False).mean()
            avg_loss = loss.ewm(span=period, adjust=False).mean()

            # 4. RS (Relative Strength) 계산
            rs = avg_gain / avg_loss

            # 5. RSI 계산
            rsi = 100 - (100 / (1 + rs))

            # 캐시 저장
            if use_cache:
                self.rsi_cache[cache_key] = rsi

            return rsi

        except Exception as e:
            print(f"❌ RSI 계산 실패: {e}")
            return pd.Series()

    def detect_rsi_signals(self, current_rsi: float, prev_rsi: float) -> Optional[str]:
        """RSI 신호 감지"""
        try:
            # 과매수 진입: RSI가 68~72 범위에서 70을 돌파
            if prev_rsi <= 72 and current_rsi > 68 and current_rsi >= prev_rsi + 2:
                print(f"🔴 RSI 과매수 진입: {prev_rsi:.1f} → {current_rsi:.1f}")
                return "overbought"

            # 과매도 진입: RSI가 28~32 범위에서 30을 이탈
            elif prev_rsi >= 28 and current_rsi < 32 and current_rsi <= prev_rsi - 2:
                print(f"🟢 RSI 과매도 진입: {prev_rsi:.1f} → {current_rsi:.1f}")
                return "oversold"

            # 상승 모멘텀: RSI가 48~52 범위에서 50을 돌파
            elif prev_rsi <= 52 and current_rsi > 48 and current_rsi >= prev_rsi + 3:
                print(f"📈 RSI 상승 모멘텀: {prev_rsi:.1f} → {current_rsi:.1f}")
                return "bullish"

            # 하락 모멘텀: RSI가 48~52 범위에서 50을 이탈
            elif prev_rsi >= 48 and current_rsi < 52 and current_rsi <= prev_rsi - 3:
                print(f"📉 RSI 하락 모멘텀: {prev_rsi:.1f} → {current_rsi:.1f}")
                return "bearish"

            return None

        except Exception as e:
            print(f"❌ RSI 신호 감지 실패: {e}")
            return None

    # =========================================================================
    # 볼린저 밴드 (Bollinger Bands) 계산
    # =========================================================================

    @measure_execution_time
    def calculate_bollinger_bands(
        self,
        prices: pd.Series,
        period: int = 20,
        std_dev: float = 2,
        use_cache: bool = True,
    ) -> Dict[str, pd.Series]:
        """
        볼린저 밴드 계산 (캐싱 적용)

        Args:
            prices: 가격 데이터 (보통 종가)
            period: 이동평균 계산 기간 (기본값: 20일)
            std_dev: 표준편차 배수 (기본값: 2배)
            use_cache: 캐시 사용 여부

        Returns:
            딕셔너리 형태로 상단밴드, 중간선, 하단밴드 반환
        """
        # 캐시 키 생성
        cache_key = f"{id(prices)}_{period}_{std_dev}"

        # 캐시 확인
        if use_cache and cache_key in self.bollinger_cache:
            cached_result = self.bollinger_cache[cache_key]

            # 새 데이터가 추가된 경우 증분 계산
            if len(prices) > len(cached_result["middle"]):
                # 볼린저 밴드는 증분 계산이 복잡하므로 일정 기간 이상 추가된 경우만 재계산
                if len(prices) - len(cached_result["middle"]) > period:
                    # 전체 재계산
                    pass
                else:
                    return cached_result

        try:
            # 1. 중간선 (이동평균선) 계산 - 캐시 활용
            middle_band = self.calculate_moving_average(prices, period)

            # 2. 표준편차 계산
            std = prices.rolling(window=period).std()

            # 3. 상단 밴드와 하단 밴드 계산
            upper_band = middle_band + (std * std_dev)
            lower_band = middle_band - (std * std_dev)

            result = {
                "upper": upper_band,  # 상단 밴드
                "middle": middle_band,  # 중간선 (이동평균)
                "lower": lower_band,  # 하단 밴드
            }

            # 캐시 저장
            if use_cache:
                self.bollinger_cache[cache_key] = result

            return result

        except Exception as e:
            print(f"❌ 볼린저 밴드 계산 실패: {e}")
            return {}

    def detect_bollinger_signals(
        self,
        current_price: float,
        upper_band: float,
        lower_band: float,
        prev_price: float,
        prev_upper: float,
        prev_lower: float,
    ) -> Optional[str]:
        """볼린저 밴드 신호 감지"""
        try:
            # 상단 밴드 돌파: 매우 강한 상승 신호
            if prev_price <= prev_upper and current_price > upper_band:
                print(
                    f"🚀 볼린저 상단 밴드 돌파: {current_price:.2f} > {upper_band:.2f}"
                )
                return "break_upper"

            # 하단 밴드 이탈: 매우 강한 하락 신호
            elif prev_price >= prev_lower and current_price < lower_band:
                print(
                    f"💥 볼린저 하단 밴드 이탈: {current_price:.2f} < {lower_band:.2f}"
                )
                return "break_lower"

            # 상단 밴드 터치: 과매수 신호
            elif abs(current_price - upper_band) / upper_band < 0.01:  # 1% 이내 근접
                print(
                    f"🔴 볼린저 상단 밴드 터치: {current_price:.2f} ≈ {upper_band:.2f}"
                )
                return "touch_upper"

            # 하단 밴드 터치: 과매도 신호
            elif abs(current_price - lower_band) / lower_band < 0.01:  # 1% 이내 근접
                print(
                    f"🟢 볼린저 하단 밴드 터치: {current_price:.2f} ≈ {lower_band:.2f}"
                )
                return "touch_lower"

            return None

        except Exception as e:
            print(f"❌ 볼린저 밴드 신호 감지 실패: {e}")
            return None

    # =========================================================================
    # 골든크로스 & 데드크로스 감지
    # =========================================================================

    def detect_cross_signals(
        self, short_ma: pd.Series, long_ma: pd.Series
    ) -> Optional[str]:
        """골든크로스 & 데드크로스 감지"""
        try:
            # 최근 2개 데이터만 확인 (현재와 이전)
            if len(short_ma) < 2 or len(long_ma) < 2:
                return None

            # 현재값과 이전값
            current_short = short_ma.iloc[-1]
            current_long = long_ma.iloc[-1]
            prev_short = short_ma.iloc[-2]
            prev_long = long_ma.iloc[-2]

            # 골든크로스: 이전에는 단기선이 장기선 아래 있었는데, 지금은 위에 있음
            if prev_short <= prev_long and current_short > current_long:
                print(
                    f"🚀 골든크로스 발생! 단기선: {current_short:.2f}, 장기선: {current_long:.2f}"
                )
                return "golden_cross"

            # 데드크로스: 이전에는 단기선이 장기선 위에 있었는데, 지금은 아래에 있음
            elif prev_short >= prev_long and current_short < current_long:
                print(
                    f"💀 데드크로스 발생! 단기선: {current_short:.2f}, 장기선: {current_long:.2f}"
                )
                return "dead_cross"

            return None

        except Exception as e:
            print(f"❌ 크로스 신호 감지 실패: {e}")
            return None

    # =========================================================================
    # 종합 분석 함수
    # =========================================================================

    @measure_execution_time
    def analyze_all_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        모든 기술적 지표를 종합 분석 (최적화 버전)

        Args:
            df: OHLCV 데이터프레임 (open, high, low, close, volume 컬럼 필요)

        Returns:
            모든 지표 분석 결과를 담은 딕셔너리
        """
        try:
            result = {
                "timestamp": datetime.now(),
                "data_points": len(df),
                "indicators": {},
            }

            # 1. 이동평균선들 계산 (캐싱 활용)
            ma_20 = self.calculate_moving_average(df["close"], 20)
            ma_50 = self.calculate_moving_average(df["close"], 50)
            ma_200 = self.calculate_moving_average(df["close"], 200)

            result["indicators"]["moving_averages"] = {
                "MA20": ma_20.iloc[-1] if not ma_20.empty else None,
                "MA50": ma_50.iloc[-1] if not ma_50.empty else None,
                "MA200": ma_200.iloc[-1] if not ma_200.empty else None,
            }

            # 2. RSI 계산 (캐싱 활용)
            rsi = self.calculate_rsi(df["close"])
            result["indicators"]["RSI"] = rsi.iloc[-1] if not rsi.empty else None

            # 3. 볼린저 밴드 계산 (캐싱 활용)
            bollinger = self.calculate_bollinger_bands(df["close"])
            if bollinger:
                result["indicators"]["bollinger_bands"] = {
                    "upper": bollinger["upper"].iloc[-1],
                    "middle": bollinger["middle"].iloc[-1],
                    "lower": bollinger["lower"].iloc[-1],
                }

            # 4. 현재 가격
            current_price = df["close"].iloc[-1]
            result["current_price"] = current_price

            # 5. 신호 감지
            signals = []

            # 이동평균선 돌파 체크
            if len(df) >= 2:
                prev_price = df["close"].iloc[-2]

                # 20일선 돌파
                if not ma_20.empty and len(ma_20) >= 2:
                    ma20_signal = self.detect_ma_breakout(
                        current_price, ma_20.iloc[-1], prev_price, ma_20.iloc[-2]
                    )
                    if ma20_signal:
                        signals.append(f"MA20_{ma20_signal}")

                # 200일선 돌파 (가장 중요!)
                if not ma_200.empty and len(ma_200) >= 2:
                    ma200_signal = self.detect_ma_breakout(
                        current_price, ma_200.iloc[-1], prev_price, ma_200.iloc[-2]
                    )
                    if ma200_signal:
                        signals.append(f"MA200_{ma200_signal}")

            # RSI 신호 체크
            if not rsi.empty and len(rsi) >= 2:
                rsi_signal = self.detect_rsi_signals(rsi.iloc[-1], rsi.iloc[-2])
                if rsi_signal:
                    signals.append(f"RSI_{rsi_signal}")

            # 골든크로스/데드크로스 체크
            if not ma_50.empty and not ma_200.empty:
                cross_signal = self.detect_cross_signals(ma_50, ma_200)
                if cross_signal:
                    signals.append(cross_signal)

            result["signals"] = signals

            print(f"📊 종합 기술적 분석 완료: {len(signals)}개 신호 감지")
            return result

        except Exception as e:
            print(f"❌ 종합 기술적 분석 실패: {e}")
            return {}
