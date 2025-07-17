"""
기술적 지표 모니터링 서비스

이 파일은 실제로 기술적 지표를 모니터링하고 신호 발생시 알림을 보내는 서비스입니다.
- 나스닥 선물: 1분봉, 15분봉으로 단기 신호 모니터링
- 나스닥 지수: 일봉으로 장기 추세 모니터링
- 신호 감지시 텔레그램 알림 자동 전송
"""

from datetime import datetime
from typing import Optional, Dict, Any
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

    # =========================================================================
    # 주요 지수 모니터링 (일봉 중심)
    # =========================================================================

    # =========================================================================
    # 나스닥 지수 모니터링 (장기 - 일봉)
    # =========================================================================

    def check_nasdaq_index_daily(self):
        """
        나스닥 지수 일봉 기술적 지표 모니터링

        모니터링 대상:
        - 50일 이동평균선 돌파/이탈 (중기 추세)
        - 200일 이동평균선 돌파/이탈 (장기 추세, 가장 중요!)
        - 골든크로스/데드크로스 (50일선 vs 200일선)
        - RSI 과매수/과매도 (장기 관점)

        특징:
        - 가장 신뢰도 높은 신호들
        - 중장기 투자 관점에서 중요
        - 가짜 신호 적고 의미있는 추세 변화
        """
        symbol = "^IXIC"  # 나스닥 지수
        timeframe = "1day"

        try:
            print(f"📊 {symbol} 일봉 기술적 지표 분석 시작")

            # 일봉 데이터 가져오기 (1년치 = 약 252개 거래일)
            df = self.yahoo_client.get_daily_data(symbol, period="1y")
            if df is None or len(df) < 200:
                print(
                    f"⚠️ {symbol} 일봉 데이터 부족: {len(df) if df is not None else 0}개"
                )
                return

            # 현재 시간
            now = datetime.utcnow()
            current_price = df["close"].iloc[-1]

            print(f"💰 {symbol} 현재가: {current_price:.2f} (일봉 기준)")

            # 이동평균선 분석 (50일선, 200일선)
            self._check_moving_averages(symbol, df, timeframe, now)

            # 골든크로스/데드크로스 분석 (가장 중요!)
            self._check_cross_signals(symbol, df, timeframe, now)

            # RSI 분석 (장기 관점)
            self._check_rsi_signals(symbol, df, timeframe, now)

            print(f"✅ {symbol} 일봉 분석 완료")

        except Exception as e:
            print(f"❌ {symbol} 일봉 분석 실패: {e}")

    def check_sp500_index_daily(self):
        """
        S&P 500 지수 일봉 기술적 지표 모니터링

        모니터링 대상:
        - 50일 이동평균선 돌파/이탈 (중기 추세)
        - 200일 이동평균선 돌파/이탈 (장기 추세, 가장 중요!)
        - 골든크로스/데드크로스 (50일선 vs 200일선)
        - RSI 과매수/과매도 (장기 관점)

        특징:
        - 미국 전체 시장을 대표하는 지수
        - 500대 기업의 시가총액 가중평균
        - 가장 신뢰도 높은 신호들
        - 중장기 투자 관점에서 중요
        """
        symbol = "^GSPC"  # S&P 500 지수
        timeframe = "1day"

        try:
            print(f"📊 {symbol} 일봉 기술적 지표 분석 시작")

            # 일봉 데이터 가져오기 (1년치 = 약 252개 거래일)
            df = self.yahoo_client.get_daily_data(symbol, period="1y")
            if df is None or len(df) < 200:
                print(
                    f"⚠️ {symbol} 일봉 데이터 부족: {len(df) if df is not None else 0}개"
                )
                return

            # 현재 시간
            now = datetime.utcnow()
            current_price = df["close"].iloc[-1]

            print(f"💰 {symbol} 현재가: {current_price:.2f} (일봉 기준)")

            # 이동평균선 분석 (50일선, 200일선)
            self._check_moving_averages(symbol, df, timeframe, now)

            # 골든크로스/데드크로스 분석 (가장 중요!)
            self._check_cross_signals(symbol, df, timeframe, now)

            # RSI 분석 (장기 관점)
            self._check_rsi_signals(symbol, df, timeframe, now)

            print(f"✅ {symbol} 일봉 분석 완료")

        except Exception as e:
            print(f"❌ {symbol} 일봉 분석 실패: {e}")

    # =========================================================================
    # 개별 지표 분석 함수들
    # =========================================================================

    def _check_moving_averages(self, symbol: str, df, timeframe: str, now: datetime):
        """이동평균선 돌파/이탈 체크"""
        try:
            current_price = df["close"].iloc[-1]
            prev_price = df["close"].iloc[-2] if len(df) >= 2 else current_price

            # 시간대별로 다른 이동평균선 체크
            if timeframe in ["1min", "15min"]:
                # 단기: 20봉, 50봉 체크
                periods = [20, 50]
            else:
                # 장기: 50일, 200일 체크
                periods = [50, 200]

            for period in periods:
                # 이동평균 계산
                ma = self.indicator_service.calculate_moving_average(
                    df["close"], period
                )
                if ma.empty or len(ma) < 2:
                    continue

                current_ma = ma.iloc[-1]
                prev_ma = ma.iloc[-2]

                # 돌파 신호 감지
                breakout_signal = self.indicator_service.detect_ma_breakout(
                    current_price, current_ma, prev_price, prev_ma
                )

                if breakout_signal:
                    # 중복 알림 방지 체크
                    alert_type = f"MA{period}_{breakout_signal}"
                    interval = ALERT_INTERVALS["MA_BREAKOUT"][timeframe]

                    if not self.alert_log_service.exists_recent_alert(
                        symbol, alert_type, f"MA{period}", interval
                    ):
                        # 🆕 1. 기술적 신호를 데이터베이스에 저장
                        saved_signal = (
                            self.signal_storage_service.save_ma_breakout_signal(
                                symbol=symbol,
                                timeframe=timeframe,
                                ma_period=period,
                                breakout_direction=breakout_signal.replace(
                                    "breakout_", ""
                                ),  # "up" or "down"
                                current_price=current_price,
                                ma_value=current_ma,
                                volume=(
                                    int(df["volume"].iloc[-1])
                                    if "volume" in df.columns
                                    and not pd.isna(df["volume"].iloc[-1])
                                    else None
                                ),
                            )
                        )

                        # 2. 텔레그램 알림 전송
                        send_ma_breakout_message(
                            symbol=symbol,
                            timeframe=timeframe,
                            ma_period=period,
                            current_price=current_price,
                            ma_value=current_ma,
                            signal_type=breakout_signal,
                            now=now,
                        )

                        # 🆕 3. 알림 발송 상태 업데이트 (신호가 저장된 경우에만)
                        if saved_signal:
                            self.signal_storage_service.mark_alert_sent(saved_signal.id)

                        # 4. 기존 알림 로그 저장 (호환성 유지)
                        self.alert_log_service.save_alert(
                            symbol=symbol,
                            alert_type=alert_type,
                            base_type=f"MA{period}",
                            base_price=current_ma,
                            current_price=current_price,
                            threshold_percent=0.0,
                            actual_percent=((current_price - current_ma) / current_ma)
                            * 100,
                            base_time=now,
                            triggered_at=now,
                        )

                        print(
                            f"📨 {symbol} MA{period} {breakout_signal} 알림 전송 완료"
                        )
                        if saved_signal:
                            print(f"💾 신호 DB 저장 완료 (ID: {saved_signal.id})")

        except Exception as e:
            print(f"❌ 이동평균선 분석 실패: {e}")

    def _check_rsi_signals(self, symbol: str, df, timeframe: str, now: datetime):
        """RSI 신호 체크"""
        try:
            # RSI 계산
            rsi = self.indicator_service.calculate_rsi(df["close"])
            if rsi.empty or len(rsi) < 2:
                return

            current_rsi = rsi.iloc[-1]
            prev_rsi = rsi.iloc[-2]

            # RSI 신호 감지
            rsi_signal = self.indicator_service.detect_rsi_signals(
                current_rsi, prev_rsi
            )

            if rsi_signal:
                # 중복 알림 방지 체크
                alert_type = f"RSI_{rsi_signal}"
                interval = ALERT_INTERVALS["RSI_ALERT"][timeframe]

                if not self.alert_log_service.exists_recent_alert(
                    symbol, alert_type, "RSI", interval
                ):
                    # 🆕 1. RSI 신호를 데이터베이스에 저장
                    saved_signal = self.signal_storage_service.save_rsi_signal(
                        symbol=symbol,
                        timeframe=timeframe,
                        rsi_value=current_rsi,
                        current_price=df["close"].iloc[-1],
                        signal_type_suffix=rsi_signal,
                        volume=(
                            int(df["volume"].iloc[-1])
                            if "volume" in df.columns
                            and not pd.isna(df["volume"].iloc[-1])
                            else None
                        ),
                    )

                    # 2. 텔레그램 알림 전송
                    send_rsi_alert_message(
                        symbol=symbol,
                        timeframe=timeframe,
                        current_rsi=current_rsi,
                        signal_type=rsi_signal,
                        now=now,
                    )

                    # 🆕 3. 알림 발송 상태 업데이트
                    if saved_signal:
                        self.signal_storage_service.mark_alert_sent(saved_signal.id)

                    # 4. 기존 알림 로그 저장 (호환성 유지)
                    self.alert_log_service.save_alert(
                        symbol=symbol,
                        alert_type=alert_type,
                        base_type="RSI",
                        base_price=current_rsi,
                        current_price=df["close"].iloc[-1],
                        threshold_percent=0.0,
                        actual_percent=current_rsi,
                        base_time=now,
                        triggered_at=now,
                    )

                    print(f"📨 {symbol} RSI {rsi_signal} 알림 전송 완료")
                    if saved_signal:
                        print(f"💾 RSI 신호 DB 저장 완료 (ID: {saved_signal.id})")

        except Exception as e:
            print(f"❌ RSI 분석 실패: {e}")

    def _check_bollinger_bands(self, symbol: str, df, timeframe: str, now: datetime):
        """볼린저 밴드 신호 체크"""
        try:
            # 볼린저 밴드 계산
            bollinger = self.indicator_service.calculate_bollinger_bands(df["close"])
            if not bollinger or len(bollinger["upper"]) < 2:
                return

            current_price = df["close"].iloc[-1]
            prev_price = df["close"].iloc[-2] if len(df) >= 2 else current_price

            current_upper = bollinger["upper"].iloc[-1]
            current_lower = bollinger["lower"].iloc[-1]
            prev_upper = bollinger["upper"].iloc[-2]
            prev_lower = bollinger["lower"].iloc[-2]

            # 볼린저 밴드 신호 감지
            bollinger_signal = self.indicator_service.detect_bollinger_signals(
                current_price,
                current_upper,
                current_lower,
                prev_price,
                prev_upper,
                prev_lower,
            )

            if bollinger_signal:
                # 중복 알림 방지 체크
                alert_type = f"BOLLINGER_{bollinger_signal}"
                interval = ALERT_INTERVALS["BOLLINGER_ALERT"][timeframe]

                if not self.alert_log_service.exists_recent_alert(
                    symbol, alert_type, "BOLLINGER", interval
                ):
                    # 🆕 1. 볼린저 밴드 신호를 데이터베이스에 저장
                    band_value = (
                        current_upper if "upper" in bollinger_signal else current_lower
                    )
                    saved_signal = self.signal_storage_service.save_bollinger_signal(
                        symbol=symbol,
                        timeframe=timeframe,
                        current_price=current_price,
                        band_value=band_value,
                        signal_type_suffix=bollinger_signal,
                        volume=(
                            int(df["volume"].iloc[-1])
                            if "volume" in df.columns
                            and not pd.isna(df["volume"].iloc[-1])
                            else None
                        ),
                    )

                    # 2. 텔레그램 알림 전송
                    send_bollinger_alert_message(
                        symbol=symbol,
                        timeframe=timeframe,
                        current_price=current_price,
                        upper_band=current_upper,
                        lower_band=current_lower,
                        signal_type=bollinger_signal,
                        now=now,
                    )

                    # 🆕 3. 알림 발송 상태 업데이트
                    if saved_signal:
                        self.signal_storage_service.mark_alert_sent(saved_signal.id)

                    # 4. 기존 알림 로그 저장 (호환성 유지)
                    self.alert_log_service.save_alert(
                        symbol=symbol,
                        alert_type=alert_type,
                        base_type="BOLLINGER",
                        base_price=band_value,
                        current_price=current_price,
                        threshold_percent=0.0,
                        actual_percent=0.0,
                        base_time=now,
                        triggered_at=now,
                    )

                    print(f"📨 {symbol} 볼린저 밴드 {bollinger_signal} 알림 전송 완료")
                    if saved_signal:
                        print(
                            f"💾 볼린저 밴드 신호 DB 저장 완료 (ID: {saved_signal.id})"
                        )

        except Exception as e:
            print(f"❌ 볼린저 밴드 분석 실패: {e}")

    def _check_cross_signals(self, symbol: str, df, timeframe: str, now: datetime):
        """골든크로스/데드크로스 신호 체크 (일봉에서만)"""
        try:
            # 50일선과 200일선 계산
            ma_50 = self.indicator_service.calculate_moving_average(df["close"], 50)
            ma_200 = self.indicator_service.calculate_moving_average(df["close"], 200)

            if ma_50.empty or ma_200.empty:
                return

            # 크로스 신호 감지
            cross_signal = self.indicator_service.detect_cross_signals(ma_50, ma_200)

            if cross_signal:
                # 중복 알림 방지 체크 (크로스는 매우 중요한 신호라서 짧은 간격)
                alert_type = cross_signal.upper()
                interval = ALERT_INTERVALS["CROSS_SIGNAL"][timeframe]

                if not self.alert_log_service.exists_recent_alert(
                    symbol, alert_type, "CROSS", interval
                ):
                    current_50 = ma_50.iloc[-1]
                    current_200 = ma_200.iloc[-1]
                    current_price = df["close"].iloc[-1]

                    # 🆕 1. 크로스 신호를 데이터베이스에 저장
                    saved_signal = self.signal_storage_service.save_cross_signal(
                        symbol=symbol,
                        cross_type=cross_signal,
                        ma_short_value=current_50,
                        ma_long_value=current_200,
                        current_price=current_price,
                        volume=(
                            int(df["volume"].iloc[-1])
                            if "volume" in df.columns
                            and not pd.isna(df["volume"].iloc[-1])
                            else None
                        ),
                    )

                    # 2. 텔레그램 알림 전송
                    if cross_signal == "golden_cross":
                        send_golden_cross_message(
                            symbol=symbol, ma_50=current_50, ma_200=current_200, now=now
                        )
                    else:  # dead_cross
                        send_dead_cross_message(
                            symbol=symbol, ma_50=current_50, ma_200=current_200, now=now
                        )

                    # 🆕 3. 알림 발송 상태 업데이트
                    if saved_signal:
                        self.signal_storage_service.mark_alert_sent(saved_signal.id)

                    # 4. 기존 알림 로그 저장 (호환성 유지)
                    self.alert_log_service.save_alert(
                        symbol=symbol,
                        alert_type=alert_type,
                        base_type="CROSS",
                        base_price=current_200,
                        current_price=current_price,
                        threshold_percent=0.0,
                        actual_percent=((current_50 - current_200) / current_200) * 100,
                        base_time=now,
                        triggered_at=now,
                    )

                    print(f"📨 {symbol} {cross_signal} 알림 전송 완료")
                    if saved_signal:
                        print(f"💾 크로스 신호 DB 저장 완료 (ID: {saved_signal.id})")

        except Exception as e:
            print(f"❌ 크로스 신호 분석 실패: {e}")

    # =========================================================================
    # 통합 모니터링 함수
    # =========================================================================

    def run_all_technical_monitoring(self):
        """
        모든 기술적 지표 모니터링을 한번에 실행

        실행 순서:
        1. 나스닥 지수 일봉 (기술주 중심)
        2. S&P 500 지수 일봉 (전체 시장)
        """
        try:
            print("🚀 주요 지수 기술적 지표 모니터링 시작")
            start_time = datetime.utcnow()

            # 1. 나스닥 지수 일봉 분석 (기술주 중심)
            self.check_nasdaq_index_daily()

            # 2. S&P 500 지수 일봉 분석 (전체 시장)
            self.check_sp500_index_daily()

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            print(
                f"✅ 주요 지수 기술적 지표 모니터링 완료 (소요시간: {duration:.1f}초)"
            )

        except Exception as e:
            print(f"❌ 주요 지수 기술적 지표 모니터링 실패: {e}")

    def get_current_technical_status(
        self, symbol: str, timeframe: str
    ) -> Dict[str, Any]:
        """
        현재 기술적 지표 상태 조회 (API 엔드포인트용)

        Args:
            symbol: 심볼 (NQ=F, ^IXIC)
            timeframe: 시간대 (1min, 15min, 1day)

        Returns:
            현재 기술적 지표 상태 딕셔너리
        """
        try:
            # 시간대별 데이터 가져오기
            if timeframe == "1min":
                df = self.yahoo_client.get_minute_data(symbol, "1d")
            elif timeframe == "15min":
                df = self.yahoo_client.get_15minute_data(symbol, "5d")
            else:  # 1day
                df = self.yahoo_client.get_daily_data(symbol, "1y")

            if df is None or len(df) < 50:
                return {"error": "데이터 부족"}

            # 종합 분석 실행
            analysis = self.indicator_service.analyze_all_indicators(df)

            # 심볼 정보 추가
            symbol_info = TECHNICAL_SYMBOLS.get(symbol, {})
            analysis["symbol_info"] = {
                "symbol": symbol,
                "name": symbol_info.get("name", symbol),
                "category": symbol_info.get("category", "기타"),
                "timeframe": timeframe,
            }

            return analysis

        except Exception as e:
            print(f"❌ 기술적 지표 상태 조회 실패: {e}")
            return {"error": str(e)}

    # =========================================================================
    # 테스트 함수들
    # =========================================================================

    def test_all_technical_alerts(self):
        """
        주요 지수 기술적 지표 알림 테스트

        나스닥 지수(^IXIC)와 S&P 500 지수(^GSPC)의 일봉 기반 신호들을 테스트합니다.
        실제 돌파가 없어도 가짜 데이터로 모든 알림 타입을 테스트해볼 수 있습니다.
        """
        from datetime import datetime

        print("🧪 주요 지수 기술적 지표 알림 테스트 시작")
        now = datetime.utcnow()

        try:
            # 1. 나스닥 지수 50일선 상향 돌파 테스트
            print("📈 1. 나스닥 지수 50일선 상향 돌파 테스트")

            # 🆕 DB에 신호 저장
            saved_signal_1 = self.signal_storage_service.save_ma_breakout_signal(
                symbol="^IXIC",
                timeframe="1day",
                ma_period=50,
                breakout_direction="up",
                current_price=18520.75,
                ma_value=18480.25,
                volume=1500000,
            )

            # 텔레그램 알림 전송
            send_ma_breakout_message(
                symbol="^IXIC",
                timeframe="1day",
                ma_period=50,
                current_price=18520.75,
                ma_value=18480.25,
                signal_type="breakout_up",
                now=now,
            )

            # 알림 발송 상태 업데이트
            if saved_signal_1:
                self.signal_storage_service.mark_alert_sent(saved_signal_1.id)
                print(
                    f"💾 나스닥 50일선 돌파 신호 DB 저장 완료 (ID: {saved_signal_1.id})"
                )

            # 2. 나스닥 지수 200일선 하향 이탈 테스트
            print("📉 2. 나스닥 지수 200일선 하향 이탈 테스트")

            # 🆕 DB에 신호 저장
            saved_signal_2 = self.signal_storage_service.save_ma_breakout_signal(
                symbol="^IXIC",
                timeframe="1day",
                ma_period=200,
                breakout_direction="down",
                current_price=18350.25,
                ma_value=18420.75,
                volume=1800000,
            )

            # 텔레그램 알림 전송
            send_ma_breakout_message(
                symbol="^IXIC",
                timeframe="1day",
                ma_period=200,
                current_price=18350.25,
                ma_value=18420.75,
                signal_type="breakout_down",
                now=now,
            )

            # 알림 발송 상태 업데이트
            if saved_signal_2:
                self.signal_storage_service.mark_alert_sent(saved_signal_2.id)
                print(
                    f"💾 나스닥 200일선 이탈 신호 DB 저장 완료 (ID: {saved_signal_2.id})"
                )

            # 3. 나스닥 지수 RSI 과매수 테스트
            print("🔴 3. 나스닥 지수 RSI 과매수 테스트")

            # 🆕 DB에 신호 저장
            saved_signal_3 = self.signal_storage_service.save_rsi_signal(
                symbol="^IXIC",
                timeframe="1day",
                rsi_value=75.8,
                current_price=18520.75,
                signal_type_suffix="overbought",
                volume=1600000,
            )

            # 텔레그램 알림 전송
            send_rsi_alert_message(
                symbol="^IXIC",
                timeframe="1day",
                current_rsi=75.8,
                signal_type="overbought",
                now=now,
            )

            # 알림 발송 상태 업데이트
            if saved_signal_3:
                self.signal_storage_service.mark_alert_sent(saved_signal_3.id)
                print(
                    f"💾 나스닥 RSI 과매수 신호 DB 저장 완료 (ID: {saved_signal_3.id})"
                )

            # 4. 나스닥 지수 RSI 과매도 테스트
            print("🟢 4. 나스닥 지수 RSI 과매도 테스트")

            # 🆕 DB에 신호 저장
            saved_signal_4 = self.signal_storage_service.save_rsi_signal(
                symbol="^IXIC",
                timeframe="1day",
                rsi_value=28.3,
                current_price=18280.50,
                signal_type_suffix="oversold",
                volume=2000000,
            )

            # 텔레그램 알림 전송
            send_rsi_alert_message(
                symbol="^IXIC",
                timeframe="1day",
                current_rsi=28.3,
                signal_type="oversold",
                now=now,
            )

            # 알림 발송 상태 업데이트
            if saved_signal_4:
                self.signal_storage_service.mark_alert_sent(saved_signal_4.id)
                print(
                    f"💾 나스닥 RSI 과매도 신호 DB 저장 완료 (ID: {saved_signal_4.id})"
                )

            # 5. 나스닥 지수 볼린저 밴드 상단 터치 테스트
            print("🔴 5. 나스닥 지수 볼린저 밴드 상단 터치 테스트")

            # 🆕 DB에 신호 저장
            saved_signal_5 = self.signal_storage_service.save_bollinger_signal(
                symbol="^IXIC",
                timeframe="1day",
                current_price=18620.50,
                band_value=18625.00,
                signal_type_suffix="touch_upper",
                volume=1400000,
            )

            # 텔레그램 알림 전송
            send_bollinger_alert_message(
                symbol="^IXIC",
                timeframe="1day",
                current_price=18620.50,
                upper_band=18625.00,
                lower_band=18280.00,
                signal_type="touch_upper",
                now=now,
            )

            # 알림 발송 상태 업데이트
            if saved_signal_5:
                self.signal_storage_service.mark_alert_sent(saved_signal_5.id)
                print(
                    f"💾 나스닥 볼린저 밴드 신호 DB 저장 완료 (ID: {saved_signal_5.id})"
                )

            # 6. 나스닥 지수 볼린저 밴드 하단 터치 테스트
            print("🟢 6. 나스닥 지수 볼린저 밴드 하단 터치 테스트")

            # 🆕 DB에 신호 저장
            saved_signal_6 = self.signal_storage_service.save_bollinger_signal(
                symbol="^IXIC",
                timeframe="1day",
                current_price=18285.25,
                band_value=18280.00,
                signal_type_suffix="touch_lower",
                volume=1700000,
            )

            # 텔레그램 알림 전송
            send_bollinger_alert_message(
                symbol="^IXIC",
                timeframe="1day",
                current_price=18285.25,
                upper_band=18620.00,
                lower_band=18280.00,
                signal_type="touch_lower",
                now=now,
            )

            # 알림 발송 상태 업데이트
            if saved_signal_6:
                self.signal_storage_service.mark_alert_sent(saved_signal_6.id)
                print(
                    f"💾 나스닥 볼린저 밴드 신호 DB 저장 완료 (ID: {saved_signal_6.id})"
                )

            # 7. 골든크로스 테스트
            print("🚀 7. 골든크로스 테스트")

            # 🆕 DB에 신호 저장
            saved_signal_7 = self.signal_storage_service.save_cross_signal(
                symbol="^IXIC",
                cross_type="golden_cross",
                ma_short_value=18520.75,
                ma_long_value=18480.25,
                current_price=18500.00,
                volume=1000000,
            )

            # 텔레그램 알림 전송
            send_golden_cross_message(
                symbol="^IXIC", ma_50=18520.75, ma_200=18480.25, now=now
            )

            # 알림 발송 상태 업데이트
            if saved_signal_7:
                self.signal_storage_service.mark_alert_sent(saved_signal_7.id)
                print(f"💾 골든크로스 신호 DB 저장 완료 (ID: {saved_signal_7.id})")

            # 8. 데드크로스 테스트
            print("💀 8. 데드크로스 테스트")

            # 🆕 DB에 신호 저장
            saved_signal_8 = self.signal_storage_service.save_cross_signal(
                symbol="^IXIC",
                cross_type="dead_cross",
                ma_short_value=18350.25,
                ma_long_value=18420.75,
                current_price=18380.00,
                volume=1200000,
            )

            # 텔레그램 알림 전송
            send_dead_cross_message(
                symbol="^IXIC", ma_50=18350.25, ma_200=18420.75, now=now
            )

            # 알림 발송 상태 업데이트
            if saved_signal_8:
                self.signal_storage_service.mark_alert_sent(saved_signal_8.id)
                print(f"💾 데드크로스 신호 DB 저장 완료 (ID: {saved_signal_8.id})")

            # 9. RSI 상승 모멘텀 테스트
            print("📈 9. RSI 상승 모멘텀 테스트")

            # 🆕 DB에 신호 저장
            saved_signal_9 = self.signal_storage_service.save_rsi_signal(
                symbol="^IXIC",
                timeframe="1day",
                rsi_value=55.2,
                current_price=18500.00,
                signal_type_suffix="bullish",
                volume=800000,
            )

            # 텔레그램 알림 전송
            send_rsi_alert_message(
                symbol="^IXIC",
                timeframe="1day",
                current_rsi=55.2,
                signal_type="bullish",
                now=now,
            )

            # 알림 발송 상태 업데이트
            if saved_signal_9:
                self.signal_storage_service.mark_alert_sent(saved_signal_9.id)
                print(f"💾 RSI 상승 모멘텀 신호 DB 저장 완료 (ID: {saved_signal_9.id})")

            # 10. S&P 500 200일선 상향 돌파 테스트
            print("🚀 10. S&P 500 200일선 상향 돌파 테스트")

            # 🆕 DB에 신호 저장
            saved_signal_10 = self.signal_storage_service.save_ma_breakout_signal(
                symbol="^GSPC",
                timeframe="1day",
                ma_period=200,
                breakout_direction="up",
                current_price=5850.75,
                ma_value=5800.25,
                volume=2500000,
            )

            # 텔레그램 알림 전송
            send_ma_breakout_message(
                symbol="^GSPC",
                timeframe="1day",
                ma_period=200,
                current_price=5850.75,
                ma_value=5800.25,
                signal_type="breakout_up",
                now=now,
            )

            # 알림 발송 상태 업데이트
            if saved_signal_10:
                self.signal_storage_service.mark_alert_sent(saved_signal_10.id)
                print(f"💾 S&P 500 신호 DB 저장 완료 (ID: {saved_signal_10.id})")

            # 11. S&P 500 골든크로스 테스트
            print("🌟 11. S&P 500 골든크로스 테스트")

            # 🆕 DB에 신호 저장
            saved_signal_11 = self.signal_storage_service.save_cross_signal(
                symbol="^GSPC",
                cross_type="golden_cross",
                ma_short_value=5820.50,
                ma_long_value=5800.25,
                current_price=5850.75,
                volume=2800000,
            )

            # 텔레그램 알림 전송
            send_golden_cross_message(
                symbol="^GSPC", ma_50=5820.50, ma_200=5800.25, now=now
            )

            # 알림 발송 상태 업데이트
            if saved_signal_11:
                self.signal_storage_service.mark_alert_sent(saved_signal_11.id)
                print(
                    f"💾 S&P 500 골든크로스 신호 DB 저장 완료 (ID: {saved_signal_11.id})"
                )

            # 12. S&P 500 RSI 과매수 테스트
            print("🔴 12. S&P 500 RSI 과매수 테스트")

            # 🆕 DB에 신호 저장
            saved_signal_12 = self.signal_storage_service.save_rsi_signal(
                symbol="^GSPC",
                timeframe="1day",
                rsi_value=72.5,
                current_price=5850.75,
                signal_type_suffix="overbought",
                volume=2200000,
            )

            # 텔레그램 알림 전송
            send_rsi_alert_message(
                symbol="^GSPC",
                timeframe="1day",
                current_rsi=72.5,
                signal_type="overbought",
                now=now,
            )

            # 알림 발송 상태 업데이트
            if saved_signal_12:
                self.signal_storage_service.mark_alert_sent(saved_signal_12.id)
                print(f"💾 S&P 500 RSI 신호 DB 저장 완료 (ID: {saved_signal_12.id})")

            print("✅ 모든 기술적 지표 알림 테스트 완료!")
            print("📱 텔레그램에서 12개의 테스트 알림을 확인해보세요.")
            print("🎯 테스트 신호 구성:")
            print("   - 나스닥 지수 (^IXIC): 골든크로스, 데드크로스, RSI")
            print("   - S&P 500 지수 (^GSPC): 200일선 돌파, 골든크로스, RSI")
            print("   - 기존 테스트 신호들 (호환성 유지)")

        except Exception as e:
            print(f"❌ 알림 테스트 실패: {e}")

    def test_single_alert(self, alert_type: str = "ma_breakout"):
        """
        단일 알림 테스트

        Args:
            alert_type: 테스트할 알림 타입
            - "ma_breakout": 이동평균선 돌파
            - "rsi": RSI 신호
            - "bollinger": 볼린저 밴드
            - "golden_cross": 골든크로스
            - "dead_cross": 데드크로스
        """
        from datetime import datetime

        now = datetime.utcnow()

        try:
            if alert_type == "ma_breakout":
                print("📈 나스닥 지수 50일선 돌파 테스트")
                send_ma_breakout_message(
                    symbol="^IXIC",
                    timeframe="1day",
                    ma_period=50,
                    current_price=18580.50,
                    ma_value=18550.25,
                    signal_type="breakout_up",
                    now=now,
                )

            elif alert_type == "rsi":
                print("🔴 나스닥 지수 RSI 과매수 테스트")
                send_rsi_alert_message(
                    symbol="^IXIC",
                    timeframe="1day",
                    current_rsi=72.5,
                    signal_type="overbought",
                    now=now,
                )

            elif alert_type == "bollinger":
                print("🟢 나스닥 지수 볼린저 밴드 하단 터치 테스트")
                send_bollinger_alert_message(
                    symbol="^IXIC",
                    timeframe="1day",
                    current_price=18275.25,
                    upper_band=18620.00,
                    lower_band=18270.00,
                    signal_type="touch_lower",
                    now=now,
                )

            elif alert_type == "golden_cross":
                print("🚀 골든크로스 테스트")
                send_golden_cross_message(
                    symbol="^IXIC", ma_50=18550.75, ma_200=18520.25, now=now
                )

            elif alert_type == "dead_cross":
                print("💀 데드크로스 테스트")
                send_dead_cross_message(
                    symbol="^IXIC", ma_50=18380.25, ma_200=18450.75, now=now
                )

            else:
                print(f"❌ 알 수 없는 알림 타입: {alert_type}")
                return

            print(f"✅ {alert_type} 테스트 완료!")

        except Exception as e:
            print(f"❌ {alert_type} 테스트 실패: {e}")
