"""
기술적 지표 계산 서비스

이 파일은 주가 데이터를 받아서 다양한 기술적 지표를 계산하는 함수들을 제공합니다.
각 함수는 pandas DataFrame을 입력받아 계산된 지표값을 반환합니다.
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from app.common.constants.technical_settings import MA_PERIODS


class TechnicalIndicatorService:
    """기술적 지표 계산을 담당하는 서비스 클래스"""

    def __init__(self):
        pass

    # =========================================================================
    # 이동평균선 (Moving Average) 계산
    # =========================================================================

    def calculate_moving_average(
        self, prices: pd.Series, period: int, ma_type: str = "SMA"
    ) -> pd.Series:
        """
        이동평균선 계산 (SMA, EMA 지원)

        Args:
            prices: 가격 데이터 (보통 종가)
            period: 평균을 계산할 기간 (예: 20일, 50일, 200일)
            ma_type: 이동평균 유형 ("SMA", "EMA")

        Returns:
            이동평균값들의 시리즈
        """
        try:
            if ma_type == "SMA":
                # 단순이동평균(SMA): 모든 데이터에 동일한 가중치
                ma = prices.rolling(window=period, min_periods=period).mean()
            elif ma_type == "EMA":
                # 지수이동평균(EMA): 최근 데이터에 더 높은 가중치
                ma = prices.ewm(span=period, adjust=False).mean()
            else:
                raise ValueError(f"지원하지 않는 이동평균 유형: {ma_type}")

            print(
                f"📊 {ma_type} {period}일 이동평균 계산 완료: {len(ma.dropna())}개 데이터"
            )
            return ma

        except Exception as e:
            print(f"❌ {ma_type} 이동평균 계산 실패 (period={period}): {e}")
            return pd.Series()

    def calculate_sma(self, prices: pd.Series, period: int) -> pd.Series:
        """단순이동평균(SMA) 계산"""
        return self.calculate_moving_average(prices, period, "SMA")

    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """지수이동평균(EMA) 계산"""
        return self.calculate_moving_average(prices, period, "EMA")

    def calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """
        거래량가중평균가격(VWAP) 계산

        Args:
            df: OHLCV 데이터프레임 (high, low, close, volume 컬럼 필요)

        Returns:
            VWAP 시리즈
        """
        try:
            # 필요한 컬럼 확인
            required_columns = ["high", "low", "close", "volume"]
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                print(f"❌ VWAP 계산에 필요한 컬럼이 없습니다: {missing_columns}")
                return pd.Series()

            # 대표 가격 계산 (HLC 평균)
            typical_price = (df["high"] + df["low"] + df["close"]) / 3

            # 거래량가중가격 계산
            volume_price = typical_price * df["volume"]

            # 누적 거래량가중가격과 누적 거래량 계산
            cumulative_volume_price = volume_price.cumsum()
            cumulative_volume = df["volume"].cumsum()

            # VWAP 계산 (0으로 나누기 방지)
            vwap = cumulative_volume_price / cumulative_volume.replace(0, np.nan)

            print(f"📊 VWAP 계산 완료: {len(vwap.dropna())}개 데이터")
            return vwap

        except Exception as e:
            print(f"❌ VWAP 계산 실패: {e}")
            return pd.Series()

    def calculate_all_moving_averages(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        모든 이동평균선을 한번에 계산

        Args:
            df: OHLCV 데이터프레임

        Returns:
            이동평균선들의 딕셔너리
        """
        try:

            ma_results = {}
            prices = df["close"]

            for ma_key, ma_config in MA_PERIODS.items():
                ma_type = ma_config.get("type", "SMA")
                period = ma_config.get("period")

                if ma_type == "VWAP":
                    # VWAP는 별도 계산
                    ma_results[ma_key] = self.calculate_vwap(df)
                elif period:
                    # SMA 또는 EMA 계산
                    ma_results[ma_key] = self.calculate_moving_average(
                        prices, period, ma_type
                    )

            print(f"📊 모든 이동평균선 계산 완료: {len(ma_results)}개")
            return ma_results

        except Exception as e:
            print(f"❌ 이동평균선 일괄 계산 실패: {e}")
            return {}

    # =========================================================================
    # RSI (Relative Strength Index) 계산
    # =========================================================================

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        RSI 지표 계산

        Args:
            prices: 가격 데이터 (보통 종가)
            period: RSI 계산 기간 (기본값: 14일)

        Returns:
            RSI 값들의 시리즈
        """
        try:
            # 가격 변화량 계산
            delta = prices.diff()

            # 상승분과 하락분 분리
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

            # RS (Relative Strength) 계산
            rs = gain / loss

            # RSI 계산
            rsi = 100 - (100 / (1 + rs))

            print(f"📊 RSI {period}일 계산 완료: {len(rsi.dropna())}개 데이터")
            return rsi

        except Exception as e:
            print(f"❌ RSI 계산 실패 (period={period}): {e}")
            return pd.Series()

    def detect_rsi_signals(self, current_rsi: float, prev_rsi: float) -> Optional[str]:
        """
        RSI 신호 감지

        Args:
            current_rsi: 현재 RSI 값
            prev_rsi: 이전 RSI 값

        Returns:
            "overbought": 과매수 진입 (70 돌파)
            "oversold": 과매도 진입 (30 이탈)
            "bullish": 상승 모멘텀 (50 돌파)
            "bearish": 하락 모멘텀 (50 이탈)
            None: 특별한 신호 없음
        """
        try:
            # 과매수 진입: RSI가 70 이상으로 돌파
            if prev_rsi < 70 and current_rsi >= 70:
                print(f"🔴 RSI 과매수 진입: {prev_rsi:.1f} → {current_rsi:.1f}")
                return "overbought"

            # 과매도 진입: RSI가 30 이하로 이탈
            elif prev_rsi > 30 and current_rsi <= 30:
                print(f"🟢 RSI 과매도 진입: {prev_rsi:.1f} → {current_rsi:.1f}")
                return "oversold"

            # 상승 모멘텀: RSI가 50을 상향 돌파
            elif prev_rsi < 50 and current_rsi >= 50:
                print(f"📈 RSI 상승 모멘텀: {prev_rsi:.1f} → {current_rsi:.1f}")
                return "bullish"

            # 하락 모멘텀: RSI가 50을 하향 이탈
            elif prev_rsi > 50 and current_rsi <= 50:
                print(f"📉 RSI 하락 모멘텀: {prev_rsi:.1f} → {current_rsi:.1f}")
                return "bearish"

            return None

        except Exception as e:
            print(f"❌ RSI 신호 감지 실패: {e}")
            return None

    # =========================================================================
    # 볼린저 밴드 (Bollinger Bands) 계산
    # =========================================================================

    def calculate_bollinger_bands(
        self, prices: pd.Series, period: int = 20, std_dev: float = 2
    ) -> Dict[str, pd.Series]:
        """
        볼린저 밴드 계산

        Args:
            prices: 가격 데이터 (보통 종가)
            period: 이동평균 계산 기간 (기본값: 20일)
            std_dev: 표준편차 배수 (기본값: 2배)

        Returns:
            딕셔너리 형태로 상단밴드, 중간선, 하단밴드 반환
        """
        try:
            # 1. 중간선 (이동평균선) 계산
            middle_band = prices.rolling(window=period).mean()

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

            print(f"📊 볼린저 밴드({period}, {std_dev}) 계산 완료")
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
        """
        볼린저 밴드 신호 감지

        Args:
            current_price: 현재 가격
            upper_band: 현재 상단 밴드
            lower_band: 현재 하단 밴드
            prev_price: 이전 가격
            prev_upper: 이전 상단 밴드
            prev_lower: 이전 하단 밴드

        Returns:
            "touch_upper": 상단 밴드 터치 (과매수)
            "touch_lower": 하단 밴드 터치 (과매도)
            "break_upper": 상단 밴드 돌파 (강한 상승)
            "break_lower": 하단 밴드 이탈 (강한 하락)
            None: 특별한 신호 없음
        """
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
        """
        골든크로스 & 데드크로스 감지

        Args:
            short_ma: 단기 이동평균선 (예: 50일선)
            long_ma: 장기 이동평균선 (예: 200일선)

        Returns:
            "golden_cross": 골든크로스 발생
            "dead_cross": 데드크로스 발생
            None: 크로스 신호 없음
        """
        try:
            if len(short_ma) < 2 or len(long_ma) < 2:
                return None

            # 현재와 이전 값들
            current_short = short_ma.iloc[-1]
            current_long = long_ma.iloc[-1]
            prev_short = short_ma.iloc[-2]
            prev_long = long_ma.iloc[-2]

            # 골든크로스: 단기선이 장기선을 상향 돌파
            if prev_short <= prev_long and current_short > current_long:
                print(f"🚀 골든크로스 발생: {current_short:.2f} > {current_long:.2f}")
                return "golden_cross"

            # 데드크로스: 단기선이 장기선을 하향 이탈
            elif prev_short >= prev_long and current_short < current_long:
                print(f"💀 데드크로스 발생: {current_short:.2f} < {current_long:.2f}")
                return "dead_cross"

            return None

        except Exception as e:
            print(f"❌ 크로스 신호 감지 실패: {e}")
            return None

    def detect_ma_breakout(
        self, current_price: float, current_ma: float, prev_price: float, prev_ma: float
    ) -> Optional[str]:
        """
        이동평균선 돌파 감지

        Args:
            current_price: 현재 주가
            current_ma: 현재 이동평균값
            prev_price: 이전 주가
            prev_ma: 이전 이동평균값

        Returns:
            "breakout_up": 상향 돌파
            "breakout_down": 하향 돌파
            None: 돌파 없음
        """
        try:
            # 상향 돌파: 이전에는 MA 아래나 근처, 지금은 MA 위
            if prev_price <= prev_ma and current_price > current_ma:
                breakout_strength = ((current_price - current_ma) / current_ma) * 100
                print(
                    f"🚀 상향 돌파 감지: {prev_price:.2f} → {current_price:.2f} (MA: {current_ma:.2f}, 강도: {breakout_strength:.2f}%)"
                )
                return "breakout_up"

            # 하향 돌파: 이전에는 MA 위나 근처, 지금은 MA 아래
            elif prev_price >= prev_ma and current_price < current_ma:
                breakout_strength = ((current_ma - current_price) / current_ma) * 100
                print(
                    f"📉 하향 돌파 감지: {prev_price:.2f} → {current_price:.2f} (MA: {current_ma:.2f}, 강도: {breakout_strength:.2f}%)"
                )
                return "breakout_down"

            return None

        except Exception as e:
            print(f"❌ 이동평균선 돌파 감지 실패: {e}")
            return None

    # =========================================================================
    # MACD (Moving Average Convergence Divergence) 계산
    # =========================================================================

    def calculate_macd(
        self,
        prices: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> Dict[str, pd.Series]:
        """
        MACD 지표 계산

        Args:
            prices: 가격 데이터 (보통 종가)
            fast_period: 빠른 EMA 기간 (기본값: 12)
            slow_period: 느린 EMA 기간 (기본값: 26)
            signal_period: 시그널 라인 기간 (기본값: 9)

        Returns:
            딕셔너리 형태로 MACD, Signal, Histogram 반환
        """
        try:
            # 1. 빠른 EMA와 느린 EMA 계산
            fast_ema = prices.ewm(span=fast_period).mean()
            slow_ema = prices.ewm(span=slow_period).mean()

            # 2. MACD 라인 계산 (빠른 EMA - 느린 EMA)
            macd_line = fast_ema - slow_ema

            # 3. 시그널 라인 계산 (MACD의 EMA)
            signal_line = macd_line.ewm(span=signal_period).mean()

            # 4. 히스토그램 계산 (MACD - Signal)
            histogram = macd_line - signal_line

            result = {
                "macd": macd_line,
                "signal": signal_line,
                "histogram": histogram,
            }

            print(f"📊 MACD({fast_period},{slow_period},{signal_period}) 계산 완료")
            return result

        except Exception as e:
            print(f"❌ MACD 계산 실패: {e}")
            return {}

    def detect_macd_signals(
        self,
        current_macd: float,
        current_signal: float,
        prev_macd: float,
        prev_signal: float,
    ) -> Optional[str]:
        """
        MACD 신호 감지

        Args:
            current_macd: 현재 MACD 값
            current_signal: 현재 시그널 값
            prev_macd: 이전 MACD 값
            prev_signal: 이전 시그널 값

        Returns:
            "bullish_cross": 상승 교차 (MACD가 시그널을 상향 돌파)
            "bearish_cross": 하락 교차 (MACD가 시그널을 하향 이탈)
            "zero_cross_up": 제로선 상향 돌파
            "zero_cross_down": 제로선 하향 이탈
            None: 특별한 신호 없음
        """
        try:
            # MACD 상승 교차: MACD가 시그널 라인을 상향 돌파
            if prev_macd <= prev_signal and current_macd > current_signal:
                print(f"🚀 MACD 상승 교차: {current_macd:.4f} > {current_signal:.4f}")
                return "bullish_cross"

            # MACD 하락 교차: MACD가 시그널 라인을 하향 이탈
            elif prev_macd >= prev_signal and current_macd < current_signal:
                print(f"📉 MACD 하락 교차: {current_macd:.4f} < {current_signal:.4f}")
                return "bearish_cross"

            # 제로선 상향 돌파: MACD가 0을 상향 돌파
            elif prev_macd <= 0 and current_macd > 0:
                print(f"📈 MACD 제로선 상향 돌파: {prev_macd:.4f} → {current_macd:.4f}")
                return "zero_cross_up"

            # 제로선 하향 이탈: MACD가 0을 하향 이탈
            elif prev_macd >= 0 and current_macd < 0:
                print(f"📉 MACD 제로선 하향 이탈: {prev_macd:.4f} → {current_macd:.4f}")
                return "zero_cross_down"

            return None

        except Exception as e:
            print(f"❌ MACD 신호 감지 실패: {e}")
            return None

    # =========================================================================
    # 스토캐스틱 (Stochastic) 계산
    # =========================================================================

    def calculate_stochastic(
        self, df: pd.DataFrame, k_period: int = 14, d_period: int = 3
    ) -> Dict[str, pd.Series]:
        """
        스토캐스틱 지표 계산

        Args:
            df: OHLC 데이터프레임 (high, low, close 컬럼 필요)
            k_period: %K 계산 기간 (기본값: 14)
            d_period: %D 계산 기간 (기본값: 3)

        Returns:
            딕셔너리 형태로 %K, %D 반환
        """
        try:
            # 필요한 컬럼 확인
            required_columns = ["high", "low", "close"]
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                print(f"❌ 스토캐스틱 계산에 필요한 컬럼이 없습니다: {missing_columns}")
                return {}

            # 1. 최고가와 최저가의 rolling 계산
            highest_high = df["high"].rolling(window=k_period).max()
            lowest_low = df["low"].rolling(window=k_period).min()

            # 2. %K 계산
            k_percent = ((df["close"] - lowest_low) / (highest_high - lowest_low)) * 100

            # 3. %D 계산 (%K의 이동평균)
            d_percent = k_percent.rolling(window=d_period).mean()

            result = {
                "k_percent": k_percent,
                "d_percent": d_percent,
            }

            print(f"📊 스토캐스틱({k_period},{d_period}) 계산 완료")
            return result

        except Exception as e:
            print(f"❌ 스토캐스틱 계산 실패: {e}")
            return {}

    def detect_stochastic_signals(
        self, current_k: float, current_d: float, prev_k: float, prev_d: float
    ) -> Optional[str]:
        """
        스토캐스틱 신호 감지

        Args:
            current_k: 현재 %K 값
            current_d: 현재 %D 값
            prev_k: 이전 %K 값
            prev_d: 이전 %D 값

        Returns:
            "overbought": 과매수 (80 이상)
            "oversold": 과매도 (20 이하)
            "bullish_cross": 상승 교차 (%K가 %D를 상향 돌파)
            "bearish_cross": 하락 교차 (%K가 %D를 하향 이탈)
            None: 특별한 신호 없음
        """
        try:
            # 과매수 상태: 둘 다 80 이상
            if current_k >= 80 and current_d >= 80:
                print(f"🔴 스토캐스틱 과매수: %K={current_k:.1f}, %D={current_d:.1f}")
                return "overbought"

            # 과매도 상태: 둘 다 20 이하
            elif current_k <= 20 and current_d <= 20:
                print(f"🟢 스토캐스틱 과매도: %K={current_k:.1f}, %D={current_d:.1f}")
                return "oversold"

            # 상승 교차: %K가 %D를 상향 돌파
            elif prev_k <= prev_d and current_k > current_d:
                print(
                    f"🚀 스토캐스틱 상승 교차: %K={current_k:.1f} > %D={current_d:.1f}"
                )
                return "bullish_cross"

            # 하락 교차: %K가 %D를 하향 이탈
            elif prev_k >= prev_d and current_k < current_d:
                print(
                    f"📉 스토캐스틱 하락 교차: %K={current_k:.1f} < %D={current_d:.1f}"
                )
                return "bearish_cross"

            return None

        except Exception as e:
            print(f"❌ 스토캐스틱 신호 감지 실패: {e}")
            return None

    # =========================================================================
    # 거래량 지표 계산
    # =========================================================================

    def calculate_volume_sma(self, volumes: pd.Series, period: int = 20) -> pd.Series:
        """
        거래량 이동평균 계산

        Args:
            volumes: 거래량 데이터
            period: 평균 계산 기간 (기본값: 20일)

        Returns:
            거래량 이동평균 시리즈
        """
        try:
            volume_sma = volumes.rolling(window=period).mean()
            print(f"📊 거래량 {period}일 이동평균 계산 완료")
            return volume_sma

        except Exception as e:
            print(f"❌ 거래량 이동평균 계산 실패: {e}")
            return pd.Series()

    def detect_volume_signals(
        self, current_volume: float, volume_sma: float, price_change_pct: float
    ) -> Optional[str]:
        """
        거래량 신호 감지

        Args:
            current_volume: 현재 거래량
            volume_sma: 거래량 이동평균
            price_change_pct: 가격 변화율 (%)

        Returns:
            "volume_breakout_up": 거래량 급증 + 상승
            "volume_breakout_down": 거래량 급증 + 하락
            "low_volume": 거래량 부족
            None: 특별한 신호 없음
        """
        try:
            volume_ratio = current_volume / volume_sma if volume_sma > 0 else 0

            # 거래량 급증 (평균의 2배 이상) + 상승
            if volume_ratio >= 2.0 and price_change_pct > 1.0:
                print(
                    f"🚀 거래량 급증 상승: 거래량 {volume_ratio:.1f}배, 상승 {price_change_pct:.2f}%"
                )
                return "volume_breakout_up"

            # 거래량 급증 (평균의 2배 이상) + 하락
            elif volume_ratio >= 2.0 and price_change_pct < -1.0:
                print(
                    f"💥 거래량 급증 하락: 거래량 {volume_ratio:.1f}배, 하락 {price_change_pct:.2f}%"
                )
                return "volume_breakout_down"

            # 거래량 부족 (평균의 50% 이하)
            elif volume_ratio <= 0.5:
                print(f"😴 거래량 부족: 평균의 {volume_ratio*100:.1f}%")
                return "low_volume"

            return None

        except Exception as e:
            print(f"❌ 거래량 신호 감지 실패: {e}")
            return None

    # =========================================================================
    # 종합 기술적 분석
    # =========================================================================

    def analyze_comprehensive_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        종합 기술적 분석 수행

        Args:
            df: OHLCV 데이터프레임

        Returns:
            모든 지표의 분석 결과를 담은 딕셔너리
        """
        try:
            results = {
                "timestamp": datetime.now(),
                "current_price": df["close"].iloc[-1],
                "price_change_pct": (
                    (df["close"].iloc[-1] - df["close"].iloc[-2]) / df["close"].iloc[-2]
                )
                * 100,
                "signals": {},
                "indicators": {},
            }

            # 1. 이동평균선 분석
            ma_results = self.calculate_all_moving_averages(df)
            results["indicators"]["moving_averages"] = ma_results

            # 2. RSI 분석
            rsi = self.calculate_rsi(df["close"])
            if not rsi.empty and len(rsi) >= 2:
                results["indicators"]["rsi"] = {
                    "current": rsi.iloc[-1],
                    "previous": rsi.iloc[-2],
                }
                rsi_signal = self.detect_rsi_signals(rsi.iloc[-1], rsi.iloc[-2])
                if rsi_signal:
                    results["signals"]["rsi"] = rsi_signal

            # 3. MACD 분석
            macd_data = self.calculate_macd(df["close"])
            if macd_data and len(macd_data["macd"]) >= 2:
                results["indicators"]["macd"] = {
                    "current_macd": macd_data["macd"].iloc[-1],
                    "current_signal": macd_data["signal"].iloc[-1],
                    "current_histogram": macd_data["histogram"].iloc[-1],
                }
                macd_signal = self.detect_macd_signals(
                    macd_data["macd"].iloc[-1],
                    macd_data["signal"].iloc[-1],
                    macd_data["macd"].iloc[-2],
                    macd_data["signal"].iloc[-2],
                )
                if macd_signal:
                    results["signals"]["macd"] = macd_signal

            # 4. 볼린저 밴드 분석
            bb_data = self.calculate_bollinger_bands(df["close"])
            if bb_data and len(bb_data["upper"]) >= 2:
                results["indicators"]["bollinger"] = {
                    "upper": bb_data["upper"].iloc[-1],
                    "middle": bb_data["middle"].iloc[-1],
                    "lower": bb_data["lower"].iloc[-1],
                }

            # 5. 스토캐스틱 분석
            stoch_data = self.calculate_stochastic(df)
            if stoch_data and len(stoch_data["k_percent"]) >= 2:
                results["indicators"]["stochastic"] = {
                    "k_percent": stoch_data["k_percent"].iloc[-1],
                    "d_percent": stoch_data["d_percent"].iloc[-1],
                }
                stoch_signal = self.detect_stochastic_signals(
                    stoch_data["k_percent"].iloc[-1],
                    stoch_data["d_percent"].iloc[-1],
                    stoch_data["k_percent"].iloc[-2],
                    stoch_data["d_percent"].iloc[-2],
                )
                if stoch_signal:
                    results["signals"]["stochastic"] = stoch_signal

            # 6. 거래량 분석
            volume_sma = self.calculate_volume_sma(df["volume"])
            if not volume_sma.empty:
                results["indicators"]["volume"] = {
                    "current": df["volume"].iloc[-1],
                    "sma_20": volume_sma.iloc[-1],
                    "ratio": (
                        df["volume"].iloc[-1] / volume_sma.iloc[-1]
                        if volume_sma.iloc[-1] > 0
                        else 0
                    ),
                }
                volume_signal = self.detect_volume_signals(
                    df["volume"].iloc[-1],
                    volume_sma.iloc[-1],
                    results["price_change_pct"],
                )
                if volume_signal:
                    results["signals"]["volume"] = volume_signal

            print(f"📊 종합 기술적 분석 완료: {len(results['signals'])}개 신호 감지")
            return results

        except Exception as e:
            print(f"❌ 종합 기술적 분석 실패: {e}")
            return {}
