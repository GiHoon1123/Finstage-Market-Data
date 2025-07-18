"""
신호 생성 서비스

이 서비스는 저장된 일봉 데이터를 기반으로 기술적 분석 신호를 생성합니다.
과거 10년치 데이터를 분석하여 모든 기술적 신호를 찾아내고 저장합니다.

주요 기능:
- 과거 데이터 기반 신호 생성
- 이동평균선 돌파/이탈 감지
- RSI 과매수/과매도 감지
- 볼린저 밴드 터치/돌파 감지
- 골든크로스/데드크로스 감지
- 생성된 신호 자동 저장
"""

from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from app.common.infra.database.config.database_config import SessionLocal
from app.technical_analysis.infra.model.repository.daily_price_repository import (
    DailyPriceRepository,
)
from app.technical_analysis.service.technical_indicator_service import (
    TechnicalIndicatorService,
)
from app.technical_analysis.service.signal_storage_service import SignalStorageService


class SignalGeneratorService:
    """신호 생성 서비스"""

    def __init__(self):
        self.session: Optional[Session] = None
        self.daily_price_repository: Optional[DailyPriceRepository] = None
        self.indicator_service = TechnicalIndicatorService()
        self.signal_storage_service = SignalStorageService()

    def _get_session_and_repository(self):
        """세션과 리포지토리 초기화 (지연 초기화)"""
        if not self.session:
            self.session = SessionLocal()
            self.daily_price_repository = DailyPriceRepository(self.session)
        return self.session, self.daily_price_repository

    # =================================================================
    # 전체 신호 생성
    # =================================================================

    def generate_all_signals(
        self, symbols: List[str] = None, start_date: date = None, end_date: date = None
    ) -> Dict[str, Any]:
        """
        모든 심볼의 모든 기술적 신호 생성

        Args:
            symbols: 분석할 심볼 리스트
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            신호 생성 결과
        """
        if symbols is None:
            symbols = ["^IXIC", "^GSPC"]

        if start_date is None:
            start_date = datetime.now().date() - timedelta(days=365 * 10)  # 10년 전

        if end_date is None:
            end_date = datetime.now().date()

        print(f"🔍 기술적 신호 생성 시작")
        print(f"   - 심볼: {symbols}")
        print(f"   - 기간: {start_date} ~ {end_date}")

        session, repository = self._get_session_and_repository()

        total_results = {
            "symbols": symbols,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "results": {},
            "summary": {"total_signals": 0, "total_saved": 0},
        }

        try:
            for symbol in symbols:
                print(f"\n📊 {symbol} 신호 생성 중...")

                result = self.generate_symbol_signals(symbol, start_date, end_date)

                total_results["results"][symbol] = result
                total_results["summary"]["total_signals"] += result.get(
                    "total_signals", 0
                )
                total_results["summary"]["total_saved"] += result.get(
                    "saved_signals", 0
                )

                print(f"✅ {symbol} 완료: {result.get('saved_signals', 0)}개 신호 생성")

            print(f"\n🎉 전체 신호 생성 완료!")
            print(f"   - 총 신호: {total_results['summary']['total_signals']}개")
            print(f"   - 저장됨: {total_results['summary']['total_saved']}개")

            return total_results

        except Exception as e:
            print(f"❌ 신호 생성 실패: {e}")
            return {"error": str(e)}
        finally:
            if session:
                session.close()

    def generate_symbol_signals(
        self, symbol: str, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """
        특정 심볼의 기술적 신호 생성

        Args:
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            신호 생성 결과
        """
        session, repository = self._get_session_and_repository()

        try:
            # 1. 해당 기간의 일봉 데이터 조회
            daily_data = repository.find_by_symbol_and_date_range(
                symbol, start_date, end_date, order_desc=False
            )

            if len(daily_data) < 200:  # 최소 200일 데이터 필요
                return {"error": f"{symbol} 데이터 부족 (최소 200일 필요)"}

            print(f"   📊 {symbol} 분석 데이터: {len(daily_data)}개")

            # 2. pandas DataFrame으로 변환
            df = self._convert_to_dataframe(daily_data)

            # 3. 각 지표별 신호 생성
            signals = []

            # 이동평균선 신호
            ma_signals = self._generate_ma_signals(symbol, df)
            signals.extend(ma_signals)

            # RSI 신호
            rsi_signals = self._generate_rsi_signals(symbol, df)
            signals.extend(rsi_signals)

            # 볼린저 밴드 신호
            bb_signals = self._generate_bollinger_signals(symbol, df)
            signals.extend(bb_signals)

            # 크로스 신호
            cross_signals = self._generate_cross_signals(symbol, df)
            signals.extend(cross_signals)

            # 4. 신호 저장
            saved_count = 0
            for signal_data in signals:
                saved_signal = self.signal_storage_service.save_signal(
                    symbol=signal_data["symbol"],
                    signal_type=signal_data["signal_type"],
                    timeframe="1day",
                    current_price=signal_data["current_price"],
                    indicator_value=signal_data.get("indicator_value"),
                    signal_strength=signal_data.get("signal_strength"),
                    volume=signal_data.get("volume"),
                    triggered_at=signal_data["triggered_at"],
                    check_duplicate=False,  # 과거 데이터는 중복 체크 안함
                )

                if saved_signal:
                    saved_count += 1

            return {
                "symbol": symbol,
                "data_count": len(daily_data),
                "total_signals": len(signals),
                "saved_signals": saved_count,
                "signal_breakdown": {
                    "ma_signals": len(ma_signals),
                    "rsi_signals": len(rsi_signals),
                    "bollinger_signals": len(bb_signals),
                    "cross_signals": len(cross_signals),
                },
            }

        except Exception as e:
            print(f"❌ {symbol} 신호 생성 실패: {e}")
            return {"error": str(e)}

    # =================================================================
    # 개별 지표 신호 생성
    # =================================================================

    def _generate_ma_signals(
        self, symbol: str, df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """이동평균선 신호 생성"""
        signals = []

        try:
            # 50일선, 200일선 계산
            ma_50 = self.indicator_service.calculate_moving_average(df["close"], 50)
            ma_200 = self.indicator_service.calculate_moving_average(df["close"], 200)

            # 각 날짜별로 돌파 체크
            for i in range(1, len(df)):
                current_price = df["close"].iloc[i]
                prev_price = df["close"].iloc[i - 1]
                current_date = df.index[i]

                # 50일선 돌파 체크
                if (
                    i < len(ma_50)
                    and not pd.isna(ma_50.iloc[i])
                    and not pd.isna(ma_50.iloc[i - 1])
                ):
                    current_ma50 = ma_50.iloc[i]
                    prev_ma50 = ma_50.iloc[i - 1]

                    breakout = self.indicator_service.detect_ma_breakout(
                        current_price, current_ma50, prev_price, prev_ma50
                    )

                    if breakout:
                        signals.append(
                            {
                                "symbol": symbol,
                                "signal_type": f"MA50_{breakout}",
                                "triggered_at": pd.Timestamp(
                                    current_date
                                ).to_pydatetime(),
                                "current_price": float(current_price),
                                "indicator_value": float(current_ma50),
                                "signal_strength": abs(
                                    (current_price - current_ma50) / current_ma50
                                )
                                * 100,
                                "volume": (
                                    int(df["volume"].iloc[i])
                                    if pd.notna(df["volume"].iloc[i])
                                    else None
                                ),
                            }
                        )

                # 200일선 돌파 체크
                if (
                    i < len(ma_200)
                    and not pd.isna(ma_200.iloc[i])
                    and not pd.isna(ma_200.iloc[i - 1])
                ):
                    current_ma200 = ma_200.iloc[i]
                    prev_ma200 = ma_200.iloc[i - 1]

                    breakout = self.indicator_service.detect_ma_breakout(
                        current_price, current_ma200, prev_price, prev_ma200
                    )

                    if breakout:
                        signals.append(
                            {
                                "symbol": symbol,
                                "signal_type": f"MA200_{breakout}",
                                "triggered_at": pd.Timestamp(
                                    current_date
                                ).to_pydatetime(),
                                "current_price": float(current_price),
                                "indicator_value": float(current_ma200),
                                "signal_strength": abs(
                                    (current_price - current_ma200) / current_ma200
                                )
                                * 100,
                                "volume": (
                                    int(df["volume"].iloc[i])
                                    if pd.notna(df["volume"].iloc[i])
                                    else None
                                ),
                            }
                        )

        except Exception as e:
            print(f"❌ {symbol} 이동평균선 신호 생성 실패: {e}")

        return signals

    def _generate_rsi_signals(
        self, symbol: str, df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """RSI 신호 생성"""
        signals = []

        try:
            # RSI 계산
            rsi = self.indicator_service.calculate_rsi(df["close"])

            # 각 날짜별로 RSI 신호 체크
            for i in range(1, len(df)):
                if i >= len(rsi) or pd.isna(rsi.iloc[i]) or pd.isna(rsi.iloc[i - 1]):
                    continue

                current_rsi = rsi.iloc[i]
                prev_rsi = rsi.iloc[i - 1]
                current_date = df.index[i]

                rsi_signal = self.indicator_service.detect_rsi_signals(
                    current_rsi, prev_rsi
                )

                if rsi_signal:
                    signals.append(
                        {
                            "symbol": symbol,
                            "signal_type": f"RSI_{rsi_signal}",
                            "triggered_at": pd.Timestamp(current_date).to_pydatetime(),
                            "current_price": float(df["close"].iloc[i]),
                            "indicator_value": float(current_rsi),
                            "signal_strength": abs(
                                current_rsi - 50
                            ),  # 중립선(50)에서 얼마나 벗어났는지
                            "volume": (
                                int(df["volume"].iloc[i])
                                if pd.notna(df["volume"].iloc[i])
                                else None
                            ),
                        }
                    )

        except Exception as e:
            print(f"❌ {symbol} RSI 신호 생성 실패: {e}")

        return signals

    def _generate_bollinger_signals(
        self, symbol: str, df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """볼린저 밴드 신호 생성"""
        signals = []

        try:
            # 볼린저 밴드 계산
            bollinger = self.indicator_service.calculate_bollinger_bands(df["close"])

            if not bollinger:
                return signals

            # 각 날짜별로 볼린저 밴드 신호 체크
            for i in range(1, len(df)):
                if (
                    i >= len(bollinger["upper"])
                    or pd.isna(bollinger["upper"].iloc[i])
                    or pd.isna(bollinger["upper"].iloc[i - 1])
                ):
                    continue

                current_price = df["close"].iloc[i]
                prev_price = df["close"].iloc[i - 1]
                current_upper = bollinger["upper"].iloc[i]
                current_lower = bollinger["lower"].iloc[i]
                prev_upper = bollinger["upper"].iloc[i - 1]
                prev_lower = bollinger["lower"].iloc[i - 1]
                current_date = df.index[i]

                bb_signal = self.indicator_service.detect_bollinger_signals(
                    current_price,
                    current_upper,
                    current_lower,
                    prev_price,
                    prev_upper,
                    prev_lower,
                )

                if bb_signal:
                    band_value = (
                        current_upper if "upper" in bb_signal else current_lower
                    )

                    signals.append(
                        {
                            "symbol": symbol,
                            "signal_type": f"BB_{bb_signal}",
                            "triggered_at": pd.Timestamp(current_date).to_pydatetime(),
                            "current_price": float(current_price),
                            "indicator_value": float(band_value),
                            "signal_strength": abs(
                                (current_price - band_value) / band_value
                            )
                            * 100,
                            "volume": (
                                int(df["volume"].iloc[i])
                                if pd.notna(df["volume"].iloc[i])
                                else None
                            ),
                        }
                    )

        except Exception as e:
            print(f"❌ {symbol} 볼린저 밴드 신호 생성 실패: {e}")

        return signals

    def _generate_cross_signals(
        self, symbol: str, df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """크로스 신호 생성"""
        signals = []

        try:
            # 50일선, 200일선 계산
            ma_50 = self.indicator_service.calculate_moving_average(df["close"], 50)
            ma_200 = self.indicator_service.calculate_moving_average(df["close"], 200)

            # 크로스 신호 감지
            cross_signal = self.indicator_service.detect_cross_signals(ma_50, ma_200)

            if cross_signal:
                # 크로스가 발생한 지점들 찾기
                for i in range(1, min(len(ma_50), len(ma_200))):
                    if pd.isna(ma_50.iloc[i]) or pd.isna(ma_200.iloc[i]):
                        continue
                    if pd.isna(ma_50.iloc[i - 1]) or pd.isna(ma_200.iloc[i - 1]):
                        continue

                    current_50 = ma_50.iloc[i]
                    current_200 = ma_200.iloc[i]
                    prev_50 = ma_50.iloc[i - 1]
                    prev_200 = ma_200.iloc[i - 1]

                    # 골든크로스: 이전에는 50일선이 200일선 아래, 지금은 위
                    if prev_50 <= prev_200 and current_50 > current_200:
                        signals.append(
                            {
                                "symbol": symbol,
                                "signal_type": "golden_cross",
                                "triggered_at": pd.Timestamp(
                                    df.index[i]
                                ).to_pydatetime(),
                                "current_price": float(df["close"].iloc[i]),
                                "indicator_value": float(current_50),
                                "signal_strength": abs(
                                    (current_50 - current_200) / current_200
                                )
                                * 100,
                                "volume": (
                                    int(df["volume"].iloc[i])
                                    if pd.notna(df["volume"].iloc[i])
                                    else None
                                ),
                            }
                        )

                    # 데드크로스: 이전에는 50일선이 200일선 위, 지금은 아래
                    elif prev_50 >= prev_200 and current_50 < current_200:
                        signals.append(
                            {
                                "symbol": symbol,
                                "signal_type": "dead_cross",
                                "triggered_at": pd.Timestamp(
                                    df.index[i]
                                ).to_pydatetime(),
                                "current_price": float(df["close"].iloc[i]),
                                "indicator_value": float(current_50),
                                "signal_strength": abs(
                                    (current_200 - current_50) / current_200
                                )
                                * 100,
                                "volume": (
                                    int(df["volume"].iloc[i])
                                    if pd.notna(df["volume"].iloc[i])
                                    else None
                                ),
                            }
                        )

        except Exception as e:
            print(f"❌ {symbol} 크로스 신호 생성 실패: {e}")

        return signals

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

    def get_signal_statistics(self, symbol: str = None) -> Dict[str, Any]:
        """
        생성된 신호 통계 조회

        Args:
            symbol: 특정 심볼 (None이면 전체)

        Returns:
            신호 통계
        """
        try:
            # SignalStorageService를 통해 통계 조회
            # 이 부분은 실제 구현에서는 technical_signals 테이블을 직접 조회해야 함
            return {"message": "신호 통계 조회 기능은 별도 구현 필요", "symbol": symbol}
        except Exception as e:
            return {"error": str(e)}

    def __del__(self):
        """소멸자 - 세션 정리"""
        if self.session:
            self.session.close()
