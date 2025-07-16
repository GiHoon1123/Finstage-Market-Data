"""
기술적 지표 계산 서비스

이 파일은 주가 데이터를 받아서 다양한 기술적 지표를 계산하는 함수들을 제공합니다.
각 함수는 pandas DataFrame을 입력받아 계산된 지표값을 반환합니다.
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict, Any
from datetime import datetime


class TechnicalIndicatorService:
    """기술적 지표 계산을 담당하는 서비스 클래스"""

    def __init__(self):
        pass

    # =========================================================================
    # 이동평균선 (Moving Average) 계산
    # =========================================================================

    def calculate_moving_average(self, prices: pd.Series, period: int) -> pd.Series:
        """
        이동평균선 계산

        이동평균이란?
        - 최근 N일간의 평균 가격을 계산해서 선으로 연결한 것
        - 주가의 잡음을 제거하고 전체적인 추세를 보여줌
        - 예: 20일 이동평균 = 최근 20일간 종가의 평균

        Args:
            prices: 가격 데이터 (보통 종가)
            period: 평균을 계산할 기간 (예: 20일, 50일, 200일)

        Returns:
            이동평균값들의 시리즈

        Example:
            ma_20 = service.calculate_moving_average(df['close'], 20)
            ma_200 = service.calculate_moving_average(df['close'], 200)
        """
        try:
            # pandas의 rolling() 함수로 이동평균 계산
            # rolling(20)은 최근 20개 데이터의 평균을 계산
            ma = prices.rolling(window=period, min_periods=period).mean()

            print(f"📊 {period}일 이동평균 계산 완료: {len(ma.dropna())}개 데이터")
            return ma

        except Exception as e:
            print(f"❌ 이동평균 계산 실패 (period={period}): {e}")
            return pd.Series()

    def detect_ma_breakout(
        self, current_price: float, current_ma: float, prev_price: float, prev_ma: float
    ) -> Optional[str]:
        """
        이동평균선 돌파 감지

        돌파란?
        - 주가가 이동평균선을 위로 뚫고 올라가는 것 (상향 돌파)
        - 주가가 이동평균선을 아래로 뚫고 내려가는 것 (하향 돌파)

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
            # 이전에는 주가가 이동평균선 아래 있었는데, 지금은 위에 있음 → 상향 돌파
            if prev_price <= prev_ma and current_price > current_ma:
                print(
                    f"🚀 상향 돌파 감지: {prev_price:.2f} → {current_price:.2f} (MA: {current_ma:.2f})"
                )
                return "breakout_up"

            # 이전에는 주가가 이동평균선 위에 있었는데, 지금은 아래에 있음 → 하향 돌파
            elif prev_price >= prev_ma and current_price < current_ma:
                print(
                    f"📉 하향 돌파 감지: {prev_price:.2f} → {current_price:.2f} (MA: {current_ma:.2f})"
                )
                return "breakout_down"

            return None

        except Exception as e:
            print(f"❌ 이동평균 돌파 감지 실패: {e}")
            return None

    # =========================================================================
    # RSI (Relative Strength Index) 계산
    # =========================================================================

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        RSI 지표 계산

        RSI란?
        - Relative Strength Index (상대강도지수)
        - 최근 가격 변동에서 상승폭과 하락폭의 비율을 나타내는 지표
        - 0~100 사이의 값을 가짐
        - 70 이상: 과매수 (너무 많이 올라서 조정 가능성)
        - 30 이하: 과매도 (너무 많이 떨어져서 반등 가능성)

        계산 방법:
        1. 매일의 가격 변화량 계산 (오늘 종가 - 어제 종가)
        2. 상승한 날들의 평균 상승폭 계산
        3. 하락한 날들의 평균 하락폭 계산
        4. RS = 평균 상승폭 / 평균 하락폭
        5. RSI = 100 - (100 / (1 + RS))

        Args:
            prices: 가격 데이터 (보통 종가)
            period: 계산 기간 (기본값: 14일)

        Returns:
            RSI 값들의 시리즈 (0~100)
        """
        try:
            # 1. 매일의 가격 변화량 계산
            delta = prices.diff()  # 오늘 가격 - 어제 가격

            # 2. 상승분과 하락분 분리
            gain = delta.where(delta > 0, 0)  # 상승한 날만 값 유지, 나머지는 0
            loss = -delta.where(
                delta < 0, 0
            )  # 하락한 날만 값 유지 (음수를 양수로), 나머지는 0

            # 3. 지수이동평균으로 평균 상승폭/하락폭 계산
            # 지수이동평균: 최근 데이터에 더 큰 가중치를 주는 평균
            avg_gain = gain.ewm(span=period, adjust=False).mean()
            avg_loss = loss.ewm(span=period, adjust=False).mean()

            # 4. RS (Relative Strength) 계산
            rs = avg_gain / avg_loss

            # 5. RSI 계산
            rsi = 100 - (100 / (1 + rs))

            print(f"📊 RSI({period}) 계산 완료: {len(rsi.dropna())}개 데이터")
            return rsi

        except Exception as e:
            print(f"❌ RSI 계산 실패: {e}")
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
            # 과매수 진입: RSI가 70을 위로 돌파
            if prev_rsi <= 70 and current_rsi > 70:
                print(f"🔴 RSI 과매수 진입: {prev_rsi:.1f} → {current_rsi:.1f}")
                return "overbought"

            # 과매도 진입: RSI가 30을 아래로 이탈
            elif prev_rsi >= 30 and current_rsi < 30:
                print(f"🟢 RSI 과매도 진입: {prev_rsi:.1f} → {current_rsi:.1f}")
                return "oversold"

            # 상승 모멘텀: RSI가 50을 위로 돌파
            elif prev_rsi <= 50 and current_rsi > 50:
                print(f"📈 RSI 상승 모멘텀: {prev_rsi:.1f} → {current_rsi:.1f}")
                return "bullish"

            # 하락 모멘텀: RSI가 50을 아래로 이탈
            elif prev_rsi >= 50 and current_rsi < 50:
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

        볼린저 밴드란?
        - 이동평균선을 중심으로 위아래로 표준편차만큼 띄운 밴드
        - 가격 변동성을 시각적으로 보여주는 지표
        - 상단 밴드 = 이동평균 + (표준편차 × 2)
        - 하단 밴드 = 이동평균 - (표준편차 × 2)

        해석:
        - 상단 밴드 터치: 과매수, 하락 가능성
        - 하단 밴드 터치: 과매도, 상승 가능성
        - 밴드폭 축소: 곧 큰 변동성 예상
        - 밴드폭 확장: 변동성 증가 중

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

        골든크로스란?
        - 단기 이동평균선(예: 50일선)이 장기 이동평균선(예: 200일선)을 위로 돌파
        - 매우 강력한 상승 신호로 여겨짐
        - 장기 상승 추세의 시작을 의미

        데드크로스란?
        - 단기 이동평균선이 장기 이동평균선을 아래로 이탈
        - 매우 강력한 하락 신호로 여겨짐
        - 장기 하락 추세의 시작을 의미

        Args:
            short_ma: 단기 이동평균선 (예: 50일선)
            long_ma: 장기 이동평균선 (예: 200일선)

        Returns:
            "golden_cross": 골든크로스 발생
            "dead_cross": 데드크로스 발생
            None: 크로스 신호 없음
        """
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

    def analyze_all_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        모든 기술적 지표를 종합 분석

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

            # 1. 이동평균선들 계산
            ma_20 = self.calculate_moving_average(df["close"], 20)
            ma_50 = self.calculate_moving_average(df["close"], 50)
            ma_200 = self.calculate_moving_average(df["close"], 200)

            result["indicators"]["moving_averages"] = {
                "MA20": ma_20.iloc[-1] if not ma_20.empty else None,
                "MA50": ma_50.iloc[-1] if not ma_50.empty else None,
                "MA200": ma_200.iloc[-1] if not ma_200.empty else None,
            }

            # 2. RSI 계산
            rsi = self.calculate_rsi(df["close"])
            result["indicators"]["RSI"] = rsi.iloc[-1] if not rsi.empty else None

            # 3. 볼린저 밴드 계산
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
