"""
기술적 지표 모니터링 서비스

이 파일은 실제로 기술적 지표를 모니터링하고 신호 발생시 알림을 보내는 서비스입니다.
- 나스닥 선물: 1분봉, 15분봉으로 단기 신호 모니터링
- 나스닥 지수: 일봉으로 장기 추세 모니터링
- 신호 감지시 텔레그램 알림 자동 전송
"""

from datetime import datetime
from typing import Optional, Dict, Any
from app.common.infra.client.yahoo_price_client import YahooPriceClient
from app.market_price.service.technical_indicator_service import (
    TechnicalIndicatorService,
)
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

    # =========================================================================
    # 나스닥 선물 모니터링 (단기 - 1분봉, 15분봉)
    # =========================================================================

    def check_nasdaq_futures_1min(self):
        """
        나스닥 선물 1분봉 기술적 지표 모니터링

        모니터링 대상:
        - 20분 이동평균선 돌파/이탈
        - 50분 이동평균선 돌파/이탈
        - RSI 과매수/과매도 신호
        - 볼린저 밴드 터치/돌파

        특징:
        - 매우 단기적인 신호 (스캘핑, 초단타용)
        - 변동성이 크고 가짜 신호 가능성 높음
        - 빠른 대응이 필요한 신호들
        """
        symbol = "NQ=F"  # 나스닥 선물
        timeframe = "1min"

        try:
            print(f"📊 {symbol} 1분봉 기술적 지표 분석 시작")

            # 1분봉 데이터 가져오기 (1일치 = 약 390개 1분봉)
            df = self.yahoo_client.get_minute_data(symbol, period="1d")
            if (
                df is None or len(df) < 200
            ):  # 최소 200개 데이터 필요 (200분 이동평균 계산용)
                print(
                    f"⚠️ {symbol} 1분봉 데이터 부족: {len(df) if df is not None else 0}개"
                )
                return

            # 현재 시간
            now = datetime.utcnow()
            current_price = df["close"].iloc[-1]

            print(f"💰 {symbol} 현재가: {current_price:.2f} (1분봉 기준)")

            # 이동평균선 분석
            self._check_moving_averages(symbol, df, timeframe, now)

            # RSI 분석
            self._check_rsi_signals(symbol, df, timeframe, now)

            # 볼린저 밴드 분석
            self._check_bollinger_bands(symbol, df, timeframe, now)

            print(f"✅ {symbol} 1분봉 분석 완료")

        except Exception as e:
            print(f"❌ {symbol} 1분봉 분석 실패: {e}")

    def check_nasdaq_futures_15min(self):
        """
        나스닥 선물 15분봉 기술적 지표 모니터링

        모니터링 대상:
        - 20봉 이동평균선 돌파/이탈 (5시간)
        - 50봉 이동평균선 돌파/이탈 (12.5시간)
        - RSI 과매수/과매도 신호
        - 볼린저 밴드 터치/돌파

        특징:
        - 1분봉보다 신뢰도 높은 신호
        - 단타매매, 스윙트레이딩에 적합
        - 하루~며칠 보유 포지션에 유용
        """
        symbol = "NQ=F"  # 나스닥 선물
        timeframe = "15min"

        try:
            print(f"📊 {symbol} 15분봉 기술적 지표 분석 시작")

            # 15분봉 데이터 가져오기 (5일치 = 약 480개 15분봉)
            df = self.yahoo_client.get_15minute_data(symbol, period="5d")
            if df is None or len(df) < 200:
                print(
                    f"⚠️ {symbol} 15분봉 데이터 부족: {len(df) if df is not None else 0}개"
                )
                return

            # 현재 시간
            now = datetime.utcnow()
            current_price = df["close"].iloc[-1]

            print(f"💰 {symbol} 현재가: {current_price:.2f} (15분봉 기준)")

            # 이동평균선 분석
            self._check_moving_averages(symbol, df, timeframe, now)

            # RSI 분석
            self._check_rsi_signals(symbol, df, timeframe, now)

            # 볼린저 밴드 분석
            self._check_bollinger_bands(symbol, df, timeframe, now)

            print(f"✅ {symbol} 15분봉 분석 완료")

        except Exception as e:
            print(f"❌ {symbol} 15분봉 분석 실패: {e}")

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
                        # 텔레그램 알림 전송
                        send_ma_breakout_message(
                            symbol=symbol,
                            timeframe=timeframe,
                            ma_period=period,
                            current_price=current_price,
                            ma_value=current_ma,
                            signal_type=breakout_signal,
                            now=now,
                        )

                        # 알림 로그 저장
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
                    # 텔레그램 알림 전송
                    send_rsi_alert_message(
                        symbol=symbol,
                        timeframe=timeframe,
                        current_rsi=current_rsi,
                        signal_type=rsi_signal,
                        now=now,
                    )

                    # 알림 로그 저장
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
                    # 텔레그램 알림 전송
                    send_bollinger_alert_message(
                        symbol=symbol,
                        timeframe=timeframe,
                        current_price=current_price,
                        upper_band=current_upper,
                        lower_band=current_lower,
                        signal_type=bollinger_signal,
                        now=now,
                    )

                    # 알림 로그 저장
                    self.alert_log_service.save_alert(
                        symbol=symbol,
                        alert_type=alert_type,
                        base_type="BOLLINGER",
                        base_price=(
                            current_upper
                            if "upper" in bollinger_signal
                            else current_lower
                        ),
                        current_price=current_price,
                        threshold_percent=0.0,
                        actual_percent=0.0,
                        base_time=now,
                        triggered_at=now,
                    )

                    print(f"📨 {symbol} 볼린저 밴드 {bollinger_signal} 알림 전송 완료")

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

                    # 텔레그램 알림 전송
                    if cross_signal == "golden_cross":
                        send_golden_cross_message(
                            symbol=symbol, ma_50=current_50, ma_200=current_200, now=now
                        )
                    else:  # dead_cross
                        send_dead_cross_message(
                            symbol=symbol, ma_50=current_50, ma_200=current_200, now=now
                        )

                    # 알림 로그 저장
                    self.alert_log_service.save_alert(
                        symbol=symbol,
                        alert_type=alert_type,
                        base_type="CROSS",
                        base_price=current_200,
                        current_price=df["close"].iloc[-1],
                        threshold_percent=0.0,
                        actual_percent=((current_50 - current_200) / current_200) * 100,
                        base_time=now,
                        triggered_at=now,
                    )

                    print(f"📨 {symbol} {cross_signal} 알림 전송 완료")

        except Exception as e:
            print(f"❌ 크로스 신호 분석 실패: {e}")

    # =========================================================================
    # 통합 모니터링 함수
    # =========================================================================

    def run_all_technical_monitoring(self):
        """
        모든 기술적 지표 모니터링을 한번에 실행

        실행 순서:
        1. 나스닥 선물 1분봉 (가장 빠른 신호)
        2. 나스닥 선물 15분봉 (중간 신호)
        3. 나스닥 지수 일봉 (가장 중요한 신호)
        """
        try:
            print("🚀 기술적 지표 통합 모니터링 시작")
            start_time = datetime.utcnow()

            # 1. 나스닥 선물 1분봉 분석
            self.check_nasdaq_futures_1min()

            # 2. 나스닥 선물 15분봉 분석
            self.check_nasdaq_futures_15min()

            # 3. 나스닥 지수 일봉 분석
            self.check_nasdaq_index_daily()

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            print(f"✅ 기술적 지표 통합 모니터링 완료 (소요시간: {duration:.1f}초)")

        except Exception as e:
            print(f"❌ 기술적 지표 통합 모니터링 실패: {e}")

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
