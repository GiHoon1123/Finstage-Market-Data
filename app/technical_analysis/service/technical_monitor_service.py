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
    send_telegram_message,
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
                print(f"\n🔍 {symbol} ({symbol_name}) 종합 분석 중...")

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

    def generate_market_status_report(
        self, symbol: str, comprehensive_result: Dict, sentiment_result: Dict
    ) -> str:
        """
        시장 상태 리포트 생성 (비트코인 스타일 상세 분석)

        Args:
            symbol: 심볼 (^IXIC, ^GSPC)
            comprehensive_result: 종합 분석 결과
            sentiment_result: 시장 심리 분석 결과

        Returns:
            텔레그램 전송용 상세 상태 리포트 메시지
        """
        try:
            symbol_name = "나스닥" if symbol == "^IXIC" else "S&P 500"
            current_time = datetime.now().strftime("%H:%M")
            current_price = comprehensive_result["current_price"]
            price_change_pct = comprehensive_result["price_change_pct"]
            indicators = comprehensive_result.get("indicators", {})

            # 헤더 (일봉 분석 리포트)
            report = f"🔔 {symbol_name} 일봉 분석 리포트 ({current_time})\n\n"

            # 💰 가격 정보
            report += "💰 가격 정보\n"
            report += f"{symbol_name}: {current_price:,.2f}\n"

            if price_change_pct >= 0:
                price_change_amount = current_price * (price_change_pct / 100)
                report += f"일봉 변화: +{price_change_pct:.2f}% (+{price_change_amount:,.2f}) 📈\n\n"
            else:
                price_change_amount = current_price * (price_change_pct / 100)
                report += f"일봉 변화: {price_change_pct:.2f}% ({price_change_amount:,.2f}) 📉\n\n"
            report += f"{symbol_name}: {current_price:,.2f}\n"

            if price_change_pct >= 0:
                price_change_amount = current_price * (price_change_pct / 100)
                report += f"일봉 변화: +{price_change_pct:.2f}% (+{price_change_amount:,.2f}) 📈\n\n"
            else:
                price_change_amount = current_price * (price_change_pct / 100)
                report += f"일봉 변화: {price_change_pct:.2f}% ({price_change_amount:,.2f}) 📉\n\n"

            # 📈 이동평균선 (현재가 대비)
            report += "📈 이동평균선 (현재가 대비)\n"
            if "moving_averages" in indicators:
                ma_data = indicators["moving_averages"]

                # 주요 이동평균선들 (비트코인 스타일 + 추가)
                ma_lines = [
                    ("SMA5", "SMA5"),
                    ("SMA10", "SMA10"),  # 추가
                    ("SMA21", "SMA20"),  # SMA21을 SMA20으로 표시
                    ("SMA50", "SMA50"),
                    ("SMA200", "SMA200"),
                    ("EMA9", "EMA12"),  # EMA9를 EMA12로 표시
                    ("EMA21", "EMA26"),  # EMA21을 EMA26으로 표시
                    ("VWAP", "VWAP"),
                ]

                for ma_key, display_name in ma_lines:
                    if ma_key in ma_data and not ma_data[ma_key].empty:
                        ma_value = ma_data[ma_key].iloc[-1]
                        ma_diff_pct = ((current_price - ma_value) / ma_value) * 100

                        if ma_diff_pct >= 0:
                            arrow = "⬆️"
                            sign = "+"
                        else:
                            arrow = "⬇️"
                            sign = ""

                        report += f"• {display_name}: {ma_value:,.0f} ({sign}{ma_diff_pct:.2f}% {arrow})\n"

            report += "\n"

            # 📊 기술 지표
            report += "📊 기술 지표\n"

            # RSI (더 상세하게)
            if "rsi" in indicators:
                rsi_val = indicators["rsi"]["current"]
                rsi_to_70 = 70 - rsi_val
                rsi_to_30 = rsi_val - 30

                if rsi_val >= 80:
                    rsi_status = "🔴 극과매수"
                elif rsi_val >= 70:
                    rsi_status = "🔴 과매수"
                elif rsi_val >= 60:
                    rsi_status = f"⚠️ 과매수 근접, 70까지 {rsi_to_70:.1f}"
                elif rsi_val <= 20:
                    rsi_status = "🟢 극과매도"
                elif rsi_val <= 30:
                    rsi_status = "🟢 과매도"
                elif rsi_val <= 40:
                    rsi_status = f"⚠️ 과매도 근접, 30까지 {rsi_to_30:.1f}"
                else:
                    rsi_status = "🟡 중립"

                report += f"• RSI(14): {rsi_val:.1f} ({rsi_status})\n"

            # MACD (더 상세하게)
            if "macd" in indicators:
                macd_val = indicators["macd"]["current_macd"]
                signal_val = indicators["macd"]["current_signal"]
                histogram = indicators["macd"]["current_histogram"]

                # MACD 상태 판단
                if macd_val > signal_val and histogram > 0:
                    macd_status = "📈 골든크로스 유지 (강세)"
                elif macd_val > signal_val and histogram < 0:
                    macd_status = "📈 골든크로스 (약화 중)"
                elif macd_val < signal_val and histogram < 0:
                    macd_status = "📉 데드크로스 (약세)"
                elif macd_val < signal_val and histogram > 0:
                    macd_status = "📉 데드크로스 (회복 중)"
                else:
                    macd_status = "🟡 중립"

                report += f"• MACD: {macd_val:+.1f} / Signal: {signal_val:+.1f} / Hist: {histogram:+.1f}\n"
                report += f"→ {macd_status}\n"

            report += "\n"

            # 🎯 볼린저 밴드 (가상 데이터 - 실제로는 indicators에서 가져와야 함)
            if "bollinger" in indicators:
                bb_data = indicators["bollinger"]
                upper = bb_data.get("upper_band", current_price * 1.02)
                middle = bb_data.get("middle_band", current_price)
                lower = bb_data.get("lower_band", current_price * 0.98)
            else:
                # 볼린저 밴드가 없으면 대략적으로 계산
                upper = current_price * 1.02
                middle = current_price
                lower = current_price * 0.98

            report += "🎯 볼린저 밴드\n"

            upper_diff = ((upper - current_price) / current_price) * 100
            middle_diff = ((middle - current_price) / current_price) * 100
            lower_diff = ((lower - current_price) / current_price) * 100

            report += f"• 상단: {upper:,.0f} ({upper_diff:+.2f}% ⬆️)\n"
            report += f"• 중심: {middle:,.0f} ({middle_diff:+.2f}% ⬇️)\n"
            report += f"• 하단: {lower:,.0f} ({lower_diff:+.2f}% ⬇️)\n"

            # 현재 위치 계산
            bb_position = ((current_price - lower) / (upper - lower)) * 100
            if bb_position >= 80:
                bb_status = "상단 근접"
            elif bb_position <= 20:
                bb_status = "하단 근접"
            else:
                bb_status = "중간"

            report += f"• 현재 위치: {bb_position:.0f}% ({bb_status})\n\n"

            # 📊 거래량 분석 (더 상세하게)
            report += "📊 거래량 분석\n"
            if "volume" in indicators:
                vol_ratio = indicators["volume"]["ratio"]
                current_volume = indicators["volume"].get("current", 0)
                avg_volume = indicators["volume"].get("average", 0)

                # 거래량 상태 판단
                if vol_ratio >= 2.0:
                    vol_status = "🔥 급증"
                elif vol_ratio >= 1.5:
                    vol_status = "📈 증가"
                elif vol_ratio >= 1.2:
                    vol_status = "📊 정상+"
                elif vol_ratio >= 0.8:
                    vol_status = "📊 정상"
                else:
                    vol_status = "📉 부족"

                # 현재 거래량을 적절한 단위로 표시
                if current_volume >= 1000000:
                    vol_display = f"{current_volume/1000000:.1f}M"
                elif current_volume >= 1000:
                    vol_display = f"{current_volume/1000:.0f}K"
                else:
                    vol_display = f"{current_volume:.0f}"

                report += f"• 현재: {vol_display}\n"
                report += f"• 평균 대비: +{(vol_ratio-1)*100:.0f}% {vol_status}\n"

                # OBV (On-Balance Volume) - 가상 데이터
                # 실제로는 indicators에서 계산해야 함
                obv_trend = "상승 지속" if vol_ratio > 1.0 else "하락 지속"
                fake_obv = int(current_volume * vol_ratio * 0.7)  # 가상 OBV
                if fake_obv >= 0:
                    report += f"• OBV: +{fake_obv:,} ({obv_trend})\n"
                else:
                    report += f"• OBV: {fake_obv:,} ({obv_trend})\n"

            report += "\n"

            # 💡 종합 판단 (더 상세하게)
            report += "💡 종합 판단\n"

            # RSI + 스토캐스틱 기반 단기 판단
            short_term_score = 0
            if "rsi" in indicators:
                rsi_val = indicators["rsi"]["current"]
                if rsi_val >= 80:
                    short_term = "극과매수 (조정 임박)"
                    short_term_score -= 2
                elif rsi_val >= 70:
                    short_term = "과매수 주의"
                    short_term_score -= 1
                elif rsi_val <= 20:
                    short_term = "극과매도 (반등 기대)"
                    short_term_score += 2
                elif rsi_val <= 30:
                    short_term = "과매도 반등"
                    short_term_score += 1
                else:
                    short_term = "중립"
            else:
                short_term = "중립"

            # MACD + 히스토그램 기반 중기 판단
            if "macd" in indicators:
                macd_val = indicators["macd"]["current_macd"]
                signal_val = indicators["macd"]["current_signal"]
                histogram = indicators["macd"]["current_histogram"]

                if macd_val > signal_val and histogram > 0:
                    mid_term = "강세 (MACD 골든크로스)"
                elif macd_val > signal_val and histogram < 0:
                    mid_term = "강세 (모멘텀 약화)"
                elif macd_val < signal_val and histogram < 0:
                    mid_term = "약세 (MACD 데드크로스)"
                else:
                    mid_term = "약세 (모멘텀 회복)"
            else:
                mid_term = "중립"

            # 200일선 + 50일선 기반 장기 판단
            if "moving_averages" in indicators:
                sma200 = indicators["moving_averages"].get("SMA200")
                sma50 = indicators["moving_averages"].get("SMA50")

                if sma200 is not None and not sma200.empty:
                    sma200_val = sma200.iloc[-1]
                    sma200_diff = ((current_price - sma200_val) / sma200_val) * 100

                    if sma50 is not None and not sma50.empty:
                        sma50_val = sma50.iloc[-1]
                        if current_price > sma50_val > sma200_val:
                            long_term = f"상승 (200일선 +{sma200_diff:.1f}%)"
                        elif current_price > sma200_val:
                            long_term = f"상승 추세 (+{sma200_diff:.1f}%)"
                        else:
                            long_term = f"하락 추세 ({sma200_diff:.1f}%)"
                    else:
                        if current_price > sma200_val:
                            long_term = f"상승 (+{sma200_diff:.1f}%)"
                        else:
                            long_term = f"하락 ({sma200_diff:.1f}%)"
                else:
                    long_term = "중립"
            else:
                long_term = "중립"

            report += f"단기: {short_term}\n"
            report += f"중기: {mid_term}\n"
            report += f"장기: {long_term}\n"

            return report

        except Exception as e:
            return f"❌ 상태 리포트 생성 실패: {e}"
            report += "📊 핵심 지표 상태:\n"

            # 1. 이동평균선 상태 (모든 추가된 이동평균선 포함)
            if "moving_averages" in indicators:
                ma_data = indicators["moving_averages"]

                # 주요 이동평균선들 순서대로 표시
                ma_lines = [
                    ("SMA5", "5일선", 1.0, 2.0),  # (키, 이름, 주의기준%, 안전기준%)
                    ("SMA10", "10일선", 1.5, 3.0),
                    ("SMA21", "21일선", 2.0, 4.0),
                    ("SMA50", "50일선", 3.0, 5.0),
                    ("SMA200", "200일선", 5.0, 8.0),
                ]

                for ma_key, ma_name, caution_pct, safe_pct in ma_lines:
                    if ma_key in ma_data and not ma_data[ma_key].empty:
                        ma_value = ma_data[ma_key].iloc[-1]
                        ma_diff_pct = ((current_price - ma_value) / ma_value) * 100

                        if ma_diff_pct >= safe_pct:
                            ma_status = f"🟢 {ma_name}: +{ma_diff_pct:.1f}% 위 (강세)"
                        elif ma_diff_pct >= caution_pct:
                            ma_status = f"🟡 {ma_name}: +{ma_diff_pct:.1f}% 위 (보통)"
                        elif ma_diff_pct >= 0:
                            ma_status = (
                                f"🟡 {ma_name}: +{ma_diff_pct:.1f}% 위 (약간 위)"
                            )
                        elif ma_diff_pct >= -caution_pct:
                            ma_status = f"🟡 {ma_name}: {ma_diff_pct:.1f}% 아래 (주의)"
                        elif ma_diff_pct >= -safe_pct:
                            ma_status = f"🔴 {ma_name}: {ma_diff_pct:.1f}% 아래 (약세)"
                        else:
                            ma_status = f"🔴 {ma_name}: {ma_diff_pct:.1f}% 아래 (위험)"

                        report += f"{ma_status}\n"

                # EMA도 추가
                ema_lines = [
                    ("EMA9", "EMA9일", 1.0, 2.5),
                    ("EMA21", "EMA21일", 2.0, 4.0),
                    ("EMA50", "EMA50일", 3.0, 5.0),
                ]

                for ema_key, ema_name, caution_pct, safe_pct in ema_lines:
                    if ema_key in ma_data and not ma_data[ema_key].empty:
                        ema_value = ma_data[ema_key].iloc[-1]
                        ema_diff_pct = ((current_price - ema_value) / ema_value) * 100

                        if ema_diff_pct >= safe_pct:
                            ema_status = (
                                f"🟢 {ema_name}: +{ema_diff_pct:.1f}% 위 (강세)"
                            )
                        elif ema_diff_pct >= caution_pct:
                            ema_status = (
                                f"🟡 {ema_name}: +{ema_diff_pct:.1f}% 위 (보통)"
                            )
                        elif ema_diff_pct >= 0:
                            ema_status = (
                                f"🟡 {ema_name}: +{ema_diff_pct:.1f}% 위 (약간 위)"
                            )
                        elif ema_diff_pct >= -caution_pct:
                            ema_status = (
                                f"🟡 {ema_name}: {ema_diff_pct:.1f}% 아래 (주의)"
                            )
                        else:
                            ema_status = (
                                f"🔴 {ema_name}: {ema_diff_pct:.1f}% 아래 (약세)"
                            )

                        report += f"{ema_status}\n"

                # VWAP도 추가
                if "VWAP" in ma_data and not ma_data["VWAP"].empty:
                    vwap_value = ma_data["VWAP"].iloc[-1]
                    vwap_diff_pct = ((current_price - vwap_value) / vwap_value) * 100

                    if vwap_diff_pct >= 2.0:
                        vwap_status = f"🟢 VWAP: +{vwap_diff_pct:.1f}% 위 (강세)"
                    elif vwap_diff_pct >= 0.5:
                        vwap_status = f"🟡 VWAP: +{vwap_diff_pct:.1f}% 위 (보통)"
                    elif vwap_diff_pct >= 0:
                        vwap_status = f"🟡 VWAP: +{vwap_diff_pct:.1f}% 위 (약간 위)"
                    elif vwap_diff_pct >= -0.5:
                        vwap_status = f"🟡 VWAP: {vwap_diff_pct:.1f}% 아래 (주의)"
                    else:
                        vwap_status = f"🔴 VWAP: {vwap_diff_pct:.1f}% 아래 (약세)"

                    report += f"{vwap_status}\n"

            # 2. RSI 상태
            if "rsi" in indicators:
                rsi_val = indicators["rsi"]["current"]

                if rsi_val >= 80:
                    rsi_status = f"🔴 RSI: {rsi_val:.1f} (극과매수)"
                elif rsi_val >= 70:
                    rsi_status = f"🟡 RSI: {rsi_val:.1f} (과매수 근접)"
                elif rsi_val >= 50:
                    rsi_status = f"🟢 RSI: {rsi_val:.1f} (상승 모멘텀)"
                elif rsi_val >= 30:
                    rsi_status = f"🟡 RSI: {rsi_val:.1f} (중립)"
                elif rsi_val >= 20:
                    rsi_status = f"🟡 RSI: {rsi_val:.1f} (과매도 근접)"
                else:
                    rsi_status = f"🟢 RSI: {rsi_val:.1f} (극과매도)"

                report += f"{rsi_status}\n"

            # 3. MACD 상태
            if "macd" in indicators:
                macd_val = indicators["macd"]["current_macd"]
                signal_val = indicators["macd"]["current_signal"]
                histogram = indicators["macd"]["current_histogram"]

                if macd_val > signal_val and histogram > 0:
                    macd_status = f"🟢 MACD: 상승 모멘텀 (강세)"
                elif macd_val > signal_val:
                    macd_status = f"🟡 MACD: 상승 모멘텀 (보통)"
                elif macd_val < signal_val and histogram < 0:
                    macd_status = f"🔴 MACD: 하락 모멘텀 (약세)"
                else:
                    macd_status = f"🟡 MACD: 하락 모멘텀 (주의)"

                report += f"{macd_status}\n"

            # 4. 스토캐스틱 상태
            if "stochastic" in indicators:
                k_val = indicators["stochastic"]["k_percent"]
                d_val = indicators["stochastic"]["d_percent"]

                if k_val >= 80 and d_val >= 80:
                    stoch_status = f"🔴 스토캐스틱: {k_val:.1f}/{d_val:.1f} (과매수)"
                elif k_val >= 70 or d_val >= 70:
                    stoch_status = (
                        f"🟡 스토캐스틱: {k_val:.1f}/{d_val:.1f} (과매수 근접)"
                    )
                elif k_val <= 20 and d_val <= 20:
                    stoch_status = f"🟢 스토캐스틱: {k_val:.1f}/{d_val:.1f} (과매도)"
                elif k_val <= 30 or d_val <= 30:
                    stoch_status = (
                        f"🟡 스토캐스틱: {k_val:.1f}/{d_val:.1f} (과매도 근접)"
                    )
                else:
                    stoch_status = f"🟢 스토캐스틱: {k_val:.1f}/{d_val:.1f} (중립)"

                report += f"{stoch_status}\n"

            # 5. 거래량 상태
            if "volume" in indicators:
                vol_ratio = indicators["volume"]["ratio"]

                if vol_ratio >= 2.0:
                    vol_status = f"🔴 거래량: {vol_ratio:.1f}배 (급증)"
                elif vol_ratio >= 1.5:
                    vol_status = f"🟡 거래량: {vol_ratio:.1f}배 (증가)"
                elif vol_ratio <= 0.5:
                    vol_status = f"🟡 거래량: {vol_ratio:.1f}배 (부족)"
                else:
                    vol_status = f"🟢 거래량: {vol_ratio:.1f}배 (정상)"

                report += f"{vol_status}\n"

            # 종합 판단
            report += f"\n🧠 시장 심리: {sentiment_result['sentiment']} {sentiment_result['emoji']}"
            report += f" ({sentiment_result['score']}/10점)\n"

            # 주의사항 및 권장사항
            signals = comprehensive_result.get("signals", {})
            if signals:
                report += f"\n⚠️ 주요 신호:\n"
                for signal_type, signal_value in signals.items():
                    if signal_type == "rsi" and "overbought" in signal_value:
                        report += f"• RSI 과매수 - 조정 가능성\n"
                    elif signal_type == "rsi" and "oversold" in signal_value:
                        report += f"• RSI 과매도 - 반등 가능성\n"
                    elif signal_type == "stochastic" and "overbought" in signal_value:
                        report += f"• 스토캐스틱 과매수 - 단기 조정 주의\n"
                    elif signal_type == "macd" and "bullish" in signal_value:
                        report += f"• MACD 상승 교차 - 상승 모멘텀\n"
                    elif signal_type == "macd" and "bearish" in signal_value:
                        report += f"• MACD 하락 교차 - 하락 모멘텀\n"

            # 포지션 권장
            sentiment_ratio = sentiment_result.get("ratio", 0.5)
            if sentiment_ratio >= 0.7:
                position_advice = "💡 포지션: 적극 매수 고려"
            elif sentiment_ratio >= 0.6:
                position_advice = "💡 포지션: 선별 매수"
            elif sentiment_ratio >= 0.4:
                position_advice = "💡 포지션: 관망"
            elif sentiment_ratio >= 0.3:
                position_advice = "💡 포지션: 주의 관찰"
            else:
                position_advice = "💡 포지션: 방어적 운용"

            report += f"\n{position_advice}"

            return report

        except Exception as e:
            return f"❌ 상태 리포트 생성 실패: {e}"

    def run_hourly_status_report(self):
        """
        한시간마다 실행되는 상태 리포트 생성 및 전송

        기존 임계점 돌파 알림 → 상태 리포트 형태로 변경
        더 실용적이고 유용한 정보 제공
        """
        try:
            print("📊 한시간 상태 리포트 생성 시작")

            # 주요 지수들 분석 (나스닥, S&P500)
            symbols = ["^IXIC", "^GSPC"]

            for symbol in symbols:
                symbol_name = "나스닥" if symbol == "^IXIC" else "S&P 500"
                print(f"\n🔍 {symbol} ({symbol_name}) 상태 리포트 생성 중...")

                # 종합 신호 분석
                comprehensive_result = self.monitor_comprehensive_signals(symbol)

                # 시장 심리 분석
                sentiment_result = self.monitor_market_sentiment(symbol)

                if comprehensive_result and sentiment_result:
                    # 상태 리포트 생성
                    status_report = self.generate_market_status_report(
                        symbol, comprehensive_result, sentiment_result
                    )

                    print(f"📊 {symbol_name} 상태 리포트:")
                    print(status_report)
                    print("-" * 50)

                    # 텔레그램으로 상태 리포트 전송
                    try:
                        # 상태 리포트 전송
                        send_telegram_message(status_report)
                        print(f"📱 {symbol_name} 상태 리포트 텔레그램 전송 완료")

                    except Exception as telegram_error:
                        print(f"❌ {symbol_name} 텔레그램 전송 실패: {telegram_error}")

            print("\n✅ 한시간 상태 리포트 생성 완료")

        except Exception as e:
            print(f"❌ 상태 리포트 생성 실패: {e}")
