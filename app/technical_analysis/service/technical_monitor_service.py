"""
기술적 지표 모니터링 서비스

이 파일은 실제로 기술적 지표를 모니터링하고 신호 발생시 알림을 보내는 서비스입니다.
- 나스닥 선물: 1분봉, 15분봉으로 단기 신호 모니터링
- 나스닥 지수: 일봉으로 장기 추세 모니터링
- 신호 감지시 텔레그램 알림 자동 전송
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
import pandas as pd
from app.common.infra.client.yahoo_price_client import YahooPriceClient
from app.technical_analysis.service.technical_indicator_service import (
    TechnicalIndicatorService,
)
from app.technical_analysis.service.signal_storage_service import SignalStorageService
from app.market_price.service.price_alert_log_service import PriceAlertLogService
from app.common.constants.technical_settings import (
    TECHNICAL_SYMBOLS,
    MA_PERIODS,
    RSI_SETTINGS,
    MACD_SETTINGS,
    STOCHASTIC_SETTINGS,
    VOLUME_SETTINGS,
    ALERT_INTERVALS,
)
from app.common.utils.telegram_notifier import (
    send_ma_breakout_message,
    send_rsi_alert_message,
    send_bollinger_alert_message,
    send_golden_cross_message,
    send_dead_cross_message,
)


class TechnicalMonitorService:
    """기술적 지표 모니터링을 담당하는 서비스 클래스"""

    def __init__(self):
        self.yahoo_client = YahooPriceClient()
        self.indicator_service = TechnicalIndicatorService()
        self.alert_log_service = PriceAlertLogService()
        self.signal_storage_service = SignalStorageService()

    def monitor_comprehensive_signals(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        종합 기술적 신호 모니터링 (기존 + 새로 추가된 전략 통합)

        기존 전략:
        - 50일/200일 이동평균선
        - 골든크로스/데드크로스
        - RSI 과매수/과매도

        새로 추가된 전략:
        1. 고급 이동평균 (SMA 5,10,21,50,100,200 + EMA 9,21,50 + VWAP)
        2. MACD (교차, 제로선 돌파, 히스토그램)
        3. 스토캐스틱 (과매수/과매도, 교차)
        4. 거래량 (급증/부족)
        5. 종합 시장 심리 분석
        """
        try:
            print(f"🔍 {symbol} 종합 기술적 분석 시작 (기존 + 신규 전략)")

            # 데이터 가져오기 (1년치)
            df = self.yahoo_client.get_daily_data(symbol, period="1y")
            if df is None or len(df) < 200:
                print(f"❌ {symbol} 데이터 부족")
                return None

            # 컬럼명을 소문자로 변환
            df.columns = df.columns.str.lower()

            # 종합 분석 수행 (모든 전략 포함)
            analysis_result = self.indicator_service.analyze_comprehensive_signals(df)

            if analysis_result:
                current_price = analysis_result["current_price"]
                price_change_pct = analysis_result["price_change_pct"]
                signals = analysis_result.get("signals", {})
                indicators = analysis_result.get("indicators", {})

                print(
                    f"💰 {symbol} 현재가: {current_price:.2f} ({price_change_pct:+.2f}%)"
                )
                print(f"🔔 감지된 신호: {len(signals)}개")

                # 신호별 상세 출력
                if signals:
                    for signal_type, signal_value in signals.items():
                        if signal_type == "rsi":
                            rsi_val = indicators.get("rsi", {}).get("current", 0)
                            print(f"  📊 RSI 신호: {signal_value} (RSI: {rsi_val:.1f})")
                        elif signal_type == "macd":
                            print(f"  📈 MACD 신호: {signal_value}")
                        elif signal_type == "stochastic":
                            stoch = indicators.get("stochastic", {})
                            k_val = stoch.get("k_percent", 0)
                            d_val = stoch.get("d_percent", 0)
                            print(
                                f"  🔄 스토캐스틱 신호: {signal_value} (%K:{k_val:.1f}, %D:{d_val:.1f})"
                            )
                        elif signal_type == "volume":
                            vol_ratio = indicators.get("volume", {}).get("ratio", 0)
                            print(
                                f"  📊 거래량 신호: {signal_value} (비율: {vol_ratio:.1f}배)"
                            )
                        else:
                            print(f"  🔔 {signal_type.upper()} 신호: {signal_value}")

                return {
                    "symbol": symbol,
                    "timestamp": datetime.now(),
                    "current_price": current_price,
                    "price_change_pct": price_change_pct,
                    "signals": signals,
                    "indicators": indicators,
                }

            return None

        except Exception as e:
            print(f"❌ {symbol} 종합 분석 실패: {e}")
            return None

    def monitor_market_sentiment(self, symbol: str) -> Optional[Dict[str, Any]]:
        """시장 심리 분석"""
        try:
            print(f"🧠 {symbol} 시장 심리 분석 시작")

            # 데이터 가져오기
            df = self.yahoo_client.get_daily_data(symbol, period="6mo")
            if df is None or len(df) < 100:
                print(f"❌ {symbol} 데이터 부족")
                return None

            # 컬럼명을 소문자로 변환
            df.columns = df.columns.str.lower()

            # 각 지표별 점수 계산
            scores = {}

            # 1. RSI 점수 (-2 ~ +2)
            rsi = self.indicator_service.calculate_rsi(df["close"])
            if not rsi.empty:
                current_rsi = rsi.iloc[-1]
                if current_rsi >= 70:
                    scores["rsi"] = -2  # 과매수 (약세)
                elif current_rsi >= 60:
                    scores["rsi"] = -1
                elif current_rsi <= 30:
                    scores["rsi"] = 2  # 과매도 (강세)
                elif current_rsi <= 40:
                    scores["rsi"] = 1
                else:
                    scores["rsi"] = 0  # 중립

            # 2. MACD 점수 (-2 ~ +2)
            macd_data = self.indicator_service.calculate_macd(df["close"])
            if macd_data:
                current_macd = macd_data["macd"].iloc[-1]
                current_signal = macd_data["signal"].iloc[-1]
                histogram = macd_data["histogram"].iloc[-1]

                if current_macd > current_signal and histogram > 0:
                    scores["macd"] = 2  # 강한 상승 신호
                elif current_macd > current_signal:
                    scores["macd"] = 1  # 상승 신호
                elif current_macd < current_signal and histogram < 0:
                    scores["macd"] = -2  # 강한 하락 신호
                elif current_macd < current_signal:
                    scores["macd"] = -1  # 하락 신호
                else:
                    scores["macd"] = 0  # 중립

            # 3. 스토캐스틱 점수 (-2 ~ +2)
            stoch_data = self.indicator_service.calculate_stochastic(df)
            if stoch_data:
                k_percent = stoch_data["k_percent"].iloc[-1]
                d_percent = stoch_data["d_percent"].iloc[-1]

                if k_percent >= 80 and d_percent >= 80:
                    scores["stochastic"] = -2  # 과매수
                elif k_percent >= 70 or d_percent >= 70:
                    scores["stochastic"] = -1
                elif k_percent <= 20 and d_percent <= 20:
                    scores["stochastic"] = 2  # 과매도
                elif k_percent <= 30 or d_percent <= 30:
                    scores["stochastic"] = 1
                else:
                    scores["stochastic"] = 0  # 중립

            # 4. 이동평균 점수 (-2 ~ +2)
            current_price = df["close"].iloc[-1]
            sma20 = self.indicator_service.calculate_moving_average(
                df["close"], 20, "SMA"
            )
            sma50 = self.indicator_service.calculate_moving_average(
                df["close"], 50, "SMA"
            )

            if not sma20.empty and not sma50.empty:
                sma20_current = sma20.iloc[-1]
                sma50_current = sma50.iloc[-1]

                if current_price > sma20_current > sma50_current:
                    scores["moving_average"] = 2  # 강한 상승 추세
                elif current_price > sma20_current:
                    scores["moving_average"] = 1  # 상승 추세
                elif current_price < sma20_current < sma50_current:
                    scores["moving_average"] = -2  # 강한 하락 추세
                elif current_price < sma20_current:
                    scores["moving_average"] = -1  # 하락 추세
                else:
                    scores["moving_average"] = 0  # 중립

            # 5. 거래량 점수 (-1 ~ +1)
            volume_sma = self.indicator_service.calculate_volume_sma(df["volume"])
            if not volume_sma.empty:
                current_volume = df["volume"].iloc[-1]
                avg_volume = volume_sma.iloc[-1]
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1

                if volume_ratio >= 1.5:
                    scores["volume"] = 1  # 거래량 증가 (긍정적)
                elif volume_ratio <= 0.7:
                    scores["volume"] = -1  # 거래량 감소 (부정적)
                else:
                    scores["volume"] = 0  # 정상

            # 종합 점수 계산
            total_score = sum(scores.values())
            max_score = len(scores) * 2  # 최대 점수
            min_score = len(scores) * -2  # 최소 점수

            # 심리 상태 결정
            if total_score >= 4:
                sentiment = "매우 강세"
                emoji = "🚀"
            elif total_score >= 2:
                sentiment = "강세"
                emoji = "📈"
            elif total_score >= 1:
                sentiment = "약간 강세"
                emoji = "🔼"
            elif total_score <= -4:
                sentiment = "매우 약세"
                emoji = "💥"
            elif total_score <= -2:
                sentiment = "약세"
                emoji = "📉"
            elif total_score <= -1:
                sentiment = "약간 약세"
                emoji = "🔽"
            else:
                sentiment = "중립"
                emoji = "🔄"

            # 비율 계산 (0~1)
            score_range = max_score - min_score
            normalized_score = (
                (total_score - min_score) / score_range if score_range > 0 else 0.5
            )

            return {
                "symbol": symbol,
                "timestamp": datetime.now(),
                "sentiment": sentiment,
                "emoji": emoji,
                "score": total_score,
                "max_score": max_score,
                "min_score": min_score,
                "ratio": normalized_score,
                "individual_scores": scores,
            }

        except Exception as e:
            print(f"❌ {symbol} 시장 심리 분석 실패: {e}")
            return None

    def run_daily_comprehensive_analysis(self):
        """
        일일 종합 분석 실행 (기존 + 새로 추가된 전략 통합)
        
        한시간마다 실행되는 핵심 분석:
        - 나스닥 지수 (^IXIC) 
        - S&P 500 지수 (^GSPC)
        
        분석 내용:
        기존: 50일선, 200일선, 골든크로스, RSI
        신규: MACD, 스토캐스틱, 거래량, 고급 이동평균, 시장심리
        """
        try:
            print("📊 일일 종합 기술적 분석 시작 (기존 + 신규 전략)")

            # 주요 지수들 분석 (나스닥, S&P500 중심)
            symbols = ["^IXIC", "^GSPC"]  # 핵심 2개 지수

            for symbol in symbols:
                symbol_name = "나스닥" if symbol == "^IXIC" else "S&P 500"
                print(f"\n� {symbol} }({symbol_name}) 종합 분석 중...")

                # 종합 신호 분석 (모든 전략 포함)
                comprehensive_result = self.monitor_comprehensive_signals(symbol)

                # 시장 심리 분석
                sentiment_result = self.monitor_market_sentiment(symbol)

                if comprehensive_result and sentiment_result:
                    signals = comprehensive_result.get("signals", {})
                    indicators = comprehensive_result.get("indicators", {})

                    print(f"📊 {symbol_name} 분석 완료:")
                    print(f"  💰 현재가: {comprehensive_result['current_price']:.2f}")
                    print(
                        f"  📈 변화율: {comprehensive_result['price_change_pct']:+.2f}%"
                    )
                    print(f"  🔔 신호: {len(signals)}개")
                    print(
                        f"  🧠 심리: {sentiment_result['sentiment']} {sentiment_result['emoji']}"
                    )

                    # 주요 지표 현재값 요약
                    if "rsi" in indicators:
                        rsi_val = indicators["rsi"]["current"]
                        print(f"  📊 RSI: {rsi_val:.1f}")

                    if "macd" in indicators:
                        macd_val = indicators["macd"]["current_macd"]
                        signal_val = indicators["macd"]["current_signal"]
                        trend = "상승" if macd_val > signal_val else "하락"
                        print(f"  📈 MACD: {trend} 모멘텀")

                    if "stochastic" in indicators:
                        k_val = indicators["stochastic"]["k_percent"]
                        d_val = indicators["stochastic"]["d_percent"]
                        print(f"  🔄 스토캐스틱: %K={k_val:.1f}, %D={d_val:.1f}")

                    if "volume" in indicators:
                        vol_ratio = indicators["volume"]["ratio"]
                        print(f"  📊 거래량: {vol_ratio:.1f}배")

                    # 중요한 신호가 있으면 상세 출력
                    if signals:
                        print(f"  ⚠️  감지된 신호:")
                        for signal_type, signal_value in signals.items():
                            print(f"    - {signal_type.upper()}: {signal_value}")

            print("\n✅ 일일 종합 분석 완료 (기존 + 신규 전략)")

        except Exception as e:
            print(f"❌ 일일 종합 분석 실패: {e}")

    def monitor_moving_average_signals(
        self, symbol: str, timeframe: str = "1d"
    ) -> List[Dict[str, Any]]:
        """이동평균선 신호 모니터링"""
        try:
            print(f"📊 {symbol} 이동평균선 신호 모니터링 ({timeframe})")

            # 데이터 가져오기
            if timeframe == "1d":
                df = self.yahoo_client.get_daily_data(symbol, period="1y")
            else:
                df = self.yahoo_client.get_intraday_data(
                    symbol, interval=timeframe, period="5d"
                )

            if df is None or len(df) < 200:
                print(f"❌ {symbol} 데이터 부족")
                return []

            # 컬럼명을 소문자로 변환
            df.columns = df.columns.str.lower()

            signals = []
            current_price = df["close"].iloc[-1]

            # SMA 신호 체크
            sma_periods = MA_PERIODS["SMA"]
            for period in sma_periods:
                sma = self.indicator_service.calculate_moving_average(
                    df["close"], period, "SMA"
                )
                if not sma.empty and len(sma) >= 2:
                    current_sma = sma.iloc[-1]
                    prev_sma = sma.iloc[-2]

                    # 돌파 신호 감지
                    if df["close"].iloc[-2] <= prev_sma and current_price > current_sma:
                        signals.append(
                            {
                                "type": "SMA_BREAKOUT_UP",
                                "period": period,
                                "price": current_price,
                                "ma_value": current_sma,
                                "timestamp": datetime.now(),
                            }
                        )
                    elif (
                        df["close"].iloc[-2] >= prev_sma and current_price < current_sma
                    ):
                        signals.append(
                            {
                                "type": "SMA_BREAKOUT_DOWN",
                                "period": period,
                                "price": current_price,
                                "ma_value": current_sma,
                                "timestamp": datetime.now(),
                            }
                        )

            return signals

        except Exception as e:
            print(f"❌ {symbol} 이동평균선 모니터링 실패: {e}")
            return []

    def monitor_rsi_signals(
        self, symbol: str, timeframe: str = "1d"
    ) -> List[Dict[str, Any]]:
        """RSI 신호 모니터링"""
        try:
            print(f"📊 {symbol} RSI 신호 모니터링 ({timeframe})")

            # 데이터 가져오기
            if timeframe == "1d":
                df = self.yahoo_client.get_daily_data(symbol, period="3mo")
            else:
                df = self.yahoo_client.get_intraday_data(
                    symbol, interval=timeframe, period="5d"
                )

            if df is None or len(df) < 50:
                print(f"❌ {symbol} 데이터 부족")
                return []

            # 컬럼명을 소문자로 변환
            df.columns = df.columns.str.lower()

            signals = []

            # RSI 계산
            rsi = self.indicator_service.calculate_rsi(df["close"])
            if not rsi.empty and len(rsi) >= 2:
                current_rsi = rsi.iloc[-1]
                prev_rsi = rsi.iloc[-2]

                # 과매수/과매도 신호
                if prev_rsi <= 70 and current_rsi > 70:
                    signals.append(
                        {
                            "type": "RSI_OVERBOUGHT",
                            "rsi_value": current_rsi,
                            "timestamp": datetime.now(),
                        }
                    )
                elif prev_rsi >= 30 and current_rsi < 30:
                    signals.append(
                        {
                            "type": "RSI_OVERSOLD",
                            "rsi_value": current_rsi,
                            "timestamp": datetime.now(),
                        }
                    )

            return signals

        except Exception as e:
            print(f"❌ {symbol} RSI 모니터링 실패: {e}")
            return []
