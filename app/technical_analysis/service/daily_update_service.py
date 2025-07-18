"""
일일 데이터 업데이트 서비스

이 서비스는 매일 장 마감 후 최신 일봉 데이터를 수집하고
새로운 기술적 신호를 감지하여 저장하는 역할을 담당합니다.

주요 기능:
- 매일 최신 일봉 데이터 수집
- 중복 데이터 자동 스킵
- 새로운 신호 자동 감지
- 실시간 알림 발송 (선택사항)
- 데이터 품질 모니터링
"""

from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
import pandas as pd
from sqlalchemy.orm import Session
from app.common.infra.database.config.database_config import SessionLocal
from app.common.infra.client.yahoo_price_client import YahooPriceClient
from app.technical_analysis.infra.model.entity.daily_prices import DailyPrice
from app.technical_analysis.infra.model.repository.daily_price_repository import (
    DailyPriceRepository,
)
from app.technical_analysis.service.technical_indicator_service import (
    TechnicalIndicatorService,
)
from app.technical_analysis.service.signal_storage_service import SignalStorageService


class DailyUpdateService:
    """일일 데이터 업데이트 서비스"""

    def __init__(self):
        self.yahoo_client = YahooPriceClient()
        self.indicator_service = TechnicalIndicatorService()
        self.signal_storage_service = SignalStorageService()
        self.session: Optional[Session] = None
        self.repository: Optional[DailyPriceRepository] = None

    def _get_session_and_repository(self):
        """세션과 리포지토리 초기화 (지연 초기화)"""
        if not self.session:
            self.session = SessionLocal()
            self.repository = DailyPriceRepository(self.session)
        return self.session, self.repository

    # =================================================================
    # 일일 데이터 업데이트
    # =================================================================

    def update_daily_data(
        self,
        symbols: List[str] = None,
        target_date: date = None,
        enable_alerts: bool = False,
    ) -> Dict[str, Any]:
        """
        일일 데이터 업데이트 및 신호 분석

        Args:
            symbols: 업데이트할 심볼 리스트
            target_date: 업데이트할 날짜 (기본값: 오늘)
            enable_alerts: 실시간 알림 활성화 여부

        Returns:
            업데이트 결과
        """
        if symbols is None:
            symbols = ["^IXIC", "^GSPC"]

        if target_date is None:
            target_date = datetime.now().date()

        print(f"📅 일일 데이터 업데이트 시작: {target_date}")
        print(f"   - 심볼: {symbols}")
        print(f"   - 알림: {'활성화' if enable_alerts else '비활성화'}")

        session, repository = self._get_session_and_repository()

        results = {
            "date": target_date.isoformat(),
            "symbols": symbols,
            "results": {},
            "summary": {
                "updated_count": 0,
                "skipped_count": 0,
                "new_signals": 0,
                "alerts_sent": 0,
            },
        }

        try:
            for symbol in symbols:
                print(f"\n🔍 {symbol} 업데이트 중...")

                result = self.update_symbol_data(
                    symbol=symbol, target_date=target_date, enable_alerts=enable_alerts
                )

                results["results"][symbol] = result

                if result.get("updated"):
                    results["summary"]["updated_count"] += 1
                else:
                    results["summary"]["skipped_count"] += 1

                results["summary"]["new_signals"] += result.get("new_signals", 0)
                results["summary"]["alerts_sent"] += result.get("alerts_sent", 0)

                status = "업데이트됨" if result.get("updated") else "스킵됨"
                print(f"✅ {symbol} {status}: 신호 {result.get('new_signals', 0)}개")

            print(f"\n🎉 일일 업데이트 완료!")
            print(f"   - 업데이트: {results['summary']['updated_count']}개")
            print(f"   - 스킵: {results['summary']['skipped_count']}개")
            print(f"   - 새 신호: {results['summary']['new_signals']}개")

            return results

        except Exception as e:
            print(f"❌ 일일 업데이트 실패: {e}")
            return {"error": str(e)}
        finally:
            if session:
                session.close()

    def update_symbol_data(
        self, symbol: str, target_date: date, enable_alerts: bool = False
    ) -> Dict[str, Any]:
        """
        특정 심볼의 일일 데이터 업데이트

        Args:
            symbol: 심볼
            target_date: 업데이트할 날짜
            enable_alerts: 알림 활성화 여부

        Returns:
            업데이트 결과
        """
        session, repository = self._get_session_and_repository()

        try:
            # 1. 해당 날짜 데이터가 이미 있는지 확인
            existing = repository.find_by_symbol_and_date(symbol, target_date)

            if existing:
                print(f"   ⏭️ {symbol} {target_date} 데이터 이미 존재")
                return {
                    "symbol": symbol,
                    "date": target_date.isoformat(),
                    "updated": False,
                    "reason": "이미 존재",
                    "new_signals": 0,
                    "alerts_sent": 0,
                }

            # 2. 야후 파이낸스에서 최신 데이터 가져오기
            print(f"   📡 {symbol} 최신 데이터 요청...")
            df = self.yahoo_client.get_daily_data(symbol, period="5d")  # 최근 5일

            if df is None or df.empty:
                return {
                    "symbol": symbol,
                    "date": target_date.isoformat(),
                    "updated": False,
                    "reason": "데이터 없음",
                    "error": "야후 파이낸스에서 데이터를 가져올 수 없음",
                }

            # 3. 해당 날짜의 데이터 찾기
            target_data = None
            for date_index, row in df.iterrows():
                if date_index.date() == target_date:
                    target_data = row
                    break

            if target_data is None:
                return {
                    "symbol": symbol,
                    "date": target_date.isoformat(),
                    "updated": False,
                    "reason": "해당 날짜 데이터 없음 (휴장일 가능성)",
                }

            # 4. 전일 종가 조회 (가격 변화 계산용)
            prev_close = None
            latest_data = repository.find_latest_by_symbol(symbol)
            if latest_data:
                prev_close = float(latest_data.close_price)

            # 5. DailyPrice 엔티티 생성
            daily_price = DailyPrice(
                symbol=symbol,
                date=target_date,
                open_price=float(target_data["Open"]),
                high_price=float(target_data["High"]),
                low_price=float(target_data["Low"]),
                close_price=float(target_data["Close"]),
                volume=(
                    int(target_data["Volume"])
                    if pd.notna(target_data["Volume"])
                    else None
                ),
            )

            # 가격 변화 계산
            if prev_close:
                daily_price.price_change = float(daily_price.close_price) - prev_close
                daily_price.price_change_percent = (
                    daily_price.price_change / prev_close
                ) * 100

            # 6. 데이터베이스에 저장
            saved_data = repository.save(daily_price)

            if not saved_data:
                return {
                    "symbol": symbol,
                    "date": target_date.isoformat(),
                    "updated": False,
                    "reason": "저장 실패",
                }

            print(f"   💾 {symbol} {target_date} 데이터 저장 완료")

            # 7. 새로운 신호 분석
            new_signals, alerts_sent = self._analyze_new_signals(
                symbol, target_date, enable_alerts
            )

            return {
                "symbol": symbol,
                "date": target_date.isoformat(),
                "updated": True,
                "price_data": {
                    "open": float(daily_price.open_price),
                    "high": float(daily_price.high_price),
                    "low": float(daily_price.low_price),
                    "close": float(daily_price.close_price),
                    "volume": daily_price.volume,
                    "change": (
                        float(daily_price.price_change)
                        if daily_price.price_change
                        else None
                    ),
                    "change_pct": (
                        float(daily_price.price_change_percent)
                        if daily_price.price_change_percent
                        else None
                    ),
                },
                "new_signals": new_signals,
                "alerts_sent": alerts_sent,
            }

        except Exception as e:
            print(f"❌ {symbol} 업데이트 실패: {e}")
            return {
                "symbol": symbol,
                "date": target_date.isoformat(),
                "updated": False,
                "error": str(e),
            }

    # =================================================================
    # 신호 분석
    # =================================================================

    def _analyze_new_signals(
        self, symbol: str, target_date: date, enable_alerts: bool = False
    ) -> tuple[int, int]:
        """
        새로운 데이터 기반 신호 분석

        Args:
            symbol: 심볼
            target_date: 분석할 날짜
            enable_alerts: 알림 활성화 여부

        Returns:
            (새로운 신호 개수, 발송된 알림 개수)
        """
        session, repository = self._get_session_and_repository()

        try:
            # 최근 250일 데이터 조회 (기술적 지표 계산용)
            end_date = target_date
            start_date = target_date - timedelta(days=365)  # 여유있게 1년

            recent_data = repository.find_by_symbol_and_date_range(
                symbol, start_date, end_date, order_desc=False
            )

            if len(recent_data) < 200:  # 최소 200일 필요
                print(f"   ⚠️ {symbol} 데이터 부족으로 신호 분석 스킵")
                return 0, 0

            # pandas DataFrame으로 변환
            df = self._convert_to_dataframe(recent_data)

            # 최신 2일 데이터로 신호 분석 (현재일과 전일)
            if len(df) < 2:
                return 0, 0

            current_idx = len(df) - 1  # 최신 데이터 인덱스
            current_price = df["close"].iloc[current_idx]
            prev_price = df["close"].iloc[current_idx - 1]
            current_date = df.index[current_idx]

            new_signals = 0
            alerts_sent = 0

            # 1. 이동평균선 신호 체크
            ma_signals = self._check_ma_signals(symbol, df, current_idx, enable_alerts)
            new_signals += ma_signals[0]
            alerts_sent += ma_signals[1]

            # 2. RSI 신호 체크
            rsi_signals = self._check_rsi_signals(
                symbol, df, current_idx, enable_alerts
            )
            new_signals += rsi_signals[0]
            alerts_sent += rsi_signals[1]

            # 3. 볼린저 밴드 신호 체크
            bb_signals = self._check_bollinger_signals(
                symbol, df, current_idx, enable_alerts
            )
            new_signals += bb_signals[0]
            alerts_sent += bb_signals[1]

            # 4. 크로스 신호 체크
            cross_signals = self._check_cross_signals(
                symbol, df, current_idx, enable_alerts
            )
            new_signals += cross_signals[0]
            alerts_sent += cross_signals[1]

            return new_signals, alerts_sent

        except Exception as e:
            print(f"❌ {symbol} 신호 분석 실패: {e}")
            return 0, 0

    def _check_ma_signals(
        self, symbol: str, df: pd.DataFrame, idx: int, enable_alerts: bool
    ) -> tuple[int, int]:
        """이동평균선 신호 체크"""
        signals = 0
        alerts = 0

        try:
            # 50일선, 200일선 계산
            ma_50 = self.indicator_service.calculate_moving_average(df["close"], 50)
            ma_200 = self.indicator_service.calculate_moving_average(df["close"], 200)

            if idx >= len(ma_50) or idx >= len(ma_200):
                return 0, 0

            current_price = df["close"].iloc[idx]
            prev_price = df["close"].iloc[idx - 1]

            # 50일선 체크
            if not pd.isna(ma_50.iloc[idx]) and not pd.isna(ma_50.iloc[idx - 1]):
                breakout = self.indicator_service.detect_ma_breakout(
                    current_price, ma_50.iloc[idx], prev_price, ma_50.iloc[idx - 1]
                )

                if breakout:
                    saved_signal = self.signal_storage_service.save_ma_breakout_signal(
                        symbol=symbol,
                        timeframe="1day",
                        ma_period=50,
                        breakout_direction=breakout.replace("breakout_", ""),
                        current_price=float(current_price),
                        ma_value=float(ma_50.iloc[idx]),
                        volume=(
                            int(df["volume"].iloc[idx])
                            if pd.notna(df["volume"].iloc[idx])
                            else None
                        ),
                    )

                    if saved_signal:
                        signals += 1
                        if enable_alerts:
                            # 실제 알림 발송 로직은 여기에 구현
                            alerts += 1

            # 200일선 체크 (동일한 로직)
            if not pd.isna(ma_200.iloc[idx]) and not pd.isna(ma_200.iloc[idx - 1]):
                breakout = self.indicator_service.detect_ma_breakout(
                    current_price, ma_200.iloc[idx], prev_price, ma_200.iloc[idx - 1]
                )

                if breakout:
                    saved_signal = self.signal_storage_service.save_ma_breakout_signal(
                        symbol=symbol,
                        timeframe="1day",
                        ma_period=200,
                        breakout_direction=breakout.replace("breakout_", ""),
                        current_price=float(current_price),
                        ma_value=float(ma_200.iloc[idx]),
                        volume=(
                            int(df["volume"].iloc[idx])
                            if pd.notna(df["volume"].iloc[idx])
                            else None
                        ),
                    )

                    if saved_signal:
                        signals += 1
                        if enable_alerts:
                            alerts += 1

        except Exception as e:
            print(f"❌ {symbol} 이동평균선 신호 체크 실패: {e}")

        return signals, alerts

    def _check_rsi_signals(
        self, symbol: str, df: pd.DataFrame, idx: int, enable_alerts: bool
    ) -> tuple[int, int]:
        """RSI 신호 체크"""
        signals = 0
        alerts = 0

        try:
            rsi = self.indicator_service.calculate_rsi(df["close"])

            if idx >= len(rsi) or pd.isna(rsi.iloc[idx]) or pd.isna(rsi.iloc[idx - 1]):
                return 0, 0

            rsi_signal = self.indicator_service.detect_rsi_signals(
                rsi.iloc[idx], rsi.iloc[idx - 1]
            )

            if rsi_signal:
                saved_signal = self.signal_storage_service.save_rsi_signal(
                    symbol=symbol,
                    timeframe="1day",
                    rsi_value=float(rsi.iloc[idx]),
                    current_price=float(df["close"].iloc[idx]),
                    signal_type_suffix=rsi_signal,
                    volume=(
                        int(df["volume"].iloc[idx])
                        if pd.notna(df["volume"].iloc[idx])
                        else None
                    ),
                )

                if saved_signal:
                    signals += 1
                    if enable_alerts:
                        alerts += 1

        except Exception as e:
            print(f"❌ {symbol} RSI 신호 체크 실패: {e}")

        return signals, alerts

    def _check_bollinger_signals(
        self, symbol: str, df: pd.DataFrame, idx: int, enable_alerts: bool
    ) -> tuple[int, int]:
        """볼린저 밴드 신호 체크"""
        signals = 0
        alerts = 0

        try:
            bollinger = self.indicator_service.calculate_bollinger_bands(df["close"])

            if not bollinger or idx >= len(bollinger["upper"]):
                return 0, 0

            current_price = df["close"].iloc[idx]
            prev_price = df["close"].iloc[idx - 1]

            bb_signal = self.indicator_service.detect_bollinger_signals(
                current_price,
                bollinger["upper"].iloc[idx],
                bollinger["lower"].iloc[idx],
                prev_price,
                bollinger["upper"].iloc[idx - 1],
                bollinger["lower"].iloc[idx - 1],
            )

            if bb_signal:
                band_value = (
                    bollinger["upper"].iloc[idx]
                    if "upper" in bb_signal
                    else bollinger["lower"].iloc[idx]
                )

                saved_signal = self.signal_storage_service.save_bollinger_signal(
                    symbol=symbol,
                    timeframe="1day",
                    current_price=float(current_price),
                    band_value=float(band_value),
                    signal_type_suffix=bb_signal,
                    volume=(
                        int(df["volume"].iloc[idx])
                        if pd.notna(df["volume"].iloc[idx])
                        else None
                    ),
                )

                if saved_signal:
                    signals += 1
                    if enable_alerts:
                        alerts += 1

        except Exception as e:
            print(f"❌ {symbol} 볼린저 밴드 신호 체크 실패: {e}")

        return signals, alerts

    def _check_cross_signals(
        self, symbol: str, df: pd.DataFrame, idx: int, enable_alerts: bool
    ) -> tuple[int, int]:
        """크로스 신호 체크"""
        signals = 0
        alerts = 0

        try:
            ma_50 = self.indicator_service.calculate_moving_average(df["close"], 50)
            ma_200 = self.indicator_service.calculate_moving_average(df["close"], 200)

            if (
                idx >= len(ma_50)
                or idx >= len(ma_200)
                or pd.isna(ma_50.iloc[idx])
                or pd.isna(ma_200.iloc[idx])
                or pd.isna(ma_50.iloc[idx - 1])
                or pd.isna(ma_200.iloc[idx - 1])
            ):
                return 0, 0

            # 골든크로스 체크
            if (
                ma_50.iloc[idx - 1] <= ma_200.iloc[idx - 1]
                and ma_50.iloc[idx] > ma_200.iloc[idx]
            ):

                saved_signal = self.signal_storage_service.save_cross_signal(
                    symbol=symbol,
                    cross_type="golden_cross",
                    ma_short_value=float(ma_50.iloc[idx]),
                    ma_long_value=float(ma_200.iloc[idx]),
                    current_price=float(df["close"].iloc[idx]),
                    volume=(
                        int(df["volume"].iloc[idx])
                        if pd.notna(df["volume"].iloc[idx])
                        else None
                    ),
                )

                if saved_signal:
                    signals += 1
                    if enable_alerts:
                        alerts += 1

            # 데드크로스 체크
            elif (
                ma_50.iloc[idx - 1] >= ma_200.iloc[idx - 1]
                and ma_50.iloc[idx] < ma_200.iloc[idx]
            ):

                saved_signal = self.signal_storage_service.save_cross_signal(
                    symbol=symbol,
                    cross_type="dead_cross",
                    ma_short_value=float(ma_50.iloc[idx]),
                    ma_long_value=float(ma_200.iloc[idx]),
                    current_price=float(df["close"].iloc[idx]),
                    volume=(
                        int(df["volume"].iloc[idx])
                        if pd.notna(df["volume"].iloc[idx])
                        else None
                    ),
                )

                if saved_signal:
                    signals += 1
                    if enable_alerts:
                        alerts += 1

        except Exception as e:
            print(f"❌ {symbol} 크로스 신호 체크 실패: {e}")

        return signals, alerts

    # =================================================================
    # 유틸리티 메서드
    # =================================================================

    def _convert_to_dataframe(self, daily_data: List) -> pd.DataFrame:
        """DailyPrice 엔티티 리스트를 pandas DataFrame으로 변환"""
        data = []
        for item in daily_data:
            data.append(
                {
                    "date": item.date,
                    "open": float(item.open_price),
                    "high": float(item.high_price),
                    "low": float(item.low_price),
                    "close": float(item.close_price),
                    "volume": item.volume if item.volume else 0,
                }
            )

        df = pd.DataFrame(data)
        df.set_index("date", inplace=True)
        return df

    def check_market_open(self, target_date: date = None) -> bool:
        """
        해당 날짜가 거래일인지 확인

        Args:
            target_date: 확인할 날짜

        Returns:
            거래일이면 True, 휴장일이면 False
        """
        if target_date is None:
            target_date = datetime.now().date()

        # 주말 체크
        if target_date.weekday() >= 5:  # 토요일(5), 일요일(6)
            return False

        # 미국 주요 휴일 체크 (간단한 버전)
        # 실제로는 더 정확한 휴일 체크가 필요
        holidays = [
            # 신정
            date(target_date.year, 1, 1),
            # 독립기념일
            date(target_date.year, 7, 4),
            # 크리스마스
            date(target_date.year, 12, 25),
        ]

        return target_date not in holidays

    def __del__(self):
        """소멸자 - 세션 정리"""
        if self.session:
            self.session.close()
