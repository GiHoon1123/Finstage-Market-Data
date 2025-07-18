"""
신호 저장 서비스

이 서비스는 기술적 분석에서 발생한 신호들을 데이터베이스에 저장하는 역할을 담당합니다.
기술적 지표 모니터링 서비스에서 신호가 감지되면 이 서비스를 통해 저장됩니다.

주요 기능:
1. 신호 저장 - 발생한 기술적 신호를 DB에 기록
2. 중복 체크 - 동일한 신호의 반복 저장 방지
3. 컨텍스트 추가 - 시장 상황, 추가 정보 등을 함께 저장
4. 알림 상태 관리 - 텔레그램 알림 발송 여부 추적

저장되는 신호 타입들:
- 이동평균선 돌파/이탈 (MA20, MA50, MA200)
- RSI 과매수/과매도 (70/30 기준)
- 볼린저 밴드 터치/돌파
- 골든크로스/데드크로스
- 기타 커스텀 신호들

데이터 활용:
- 백테스팅: 과거 신호들의 성과 분석
- 패턴 분석: 성공적인 신호 패턴 발견
- 알림 최적화: 효과적인 신호만 알림 발송
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from app.common.infra.database.config.database_config import SessionLocal
from app.technical_analysis.infra.model.entity.technical_signals import TechnicalSignal
from app.technical_analysis.infra.model.repository.technical_signal_repository import (
    TechnicalSignalRepository,
)


class SignalStorageService:
    """
    기술적 신호 저장을 담당하는 서비스

    기술적 지표 모니터링에서 신호가 감지될 때마다 호출되어
    신호 정보를 데이터베이스에 저장하고 관리합니다.
    """

    def __init__(self):
        """서비스 초기화"""
        self.session: Optional[Session] = None
        self.repository: Optional[TechnicalSignalRepository] = None

    def _get_session_and_repository(self):
        """세션과 리포지토리 초기화 (지연 초기화)"""
        if not self.session:
            self.session = SessionLocal()
            self.repository = TechnicalSignalRepository(self.session)
        return self.session, self.repository

    # =================================================================
    # 신호 저장 메인 함수들
    # =================================================================

    def save_signal(
        self,
        symbol: str,
        signal_type: str,
        timeframe: str,
        current_price: float,
        indicator_value: Optional[float] = None,
        signal_strength: Optional[float] = None,
        volume: Optional[int] = None,
        market_condition: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
        triggered_at: Optional[datetime] = None,
        check_duplicate: bool = True,
        duplicate_window_minutes: int = 60,
    ) -> Optional[TechnicalSignal]:
        """
        기술적 신호를 데이터베이스에 저장

        Args:
            symbol: 심볼 (예: ^IXIC, ^GSPC, AAPL)
            signal_type: 신호 타입 (예: MA200_breakout_up, RSI_overbought)
            timeframe: 시간대 (1day - 일봉 중심)
            current_price: 신호 발생 시점의 현재 가격
            indicator_value: 관련 지표값 (MA값, RSI값 등)
            signal_strength: 신호 강도 (돌파폭, 과매수 정도 등)
            volume: 거래량
            market_condition: 시장 상황 (bullish, bearish, sideways)
            additional_context: 추가 컨텍스트 정보
            check_duplicate: 중복 체크 여부
            duplicate_window_minutes: 중복 체크 시간 범위 (분)

        Returns:
            저장된 신호 엔티티 또는 None (중복인 경우)

        Example:
            # 나스닥 지수 200일선 상향 돌파 신호 저장
            signal = service.save_signal(
                symbol="^IXIC",
                signal_type="MA200_breakout_up",
                timeframe="1day",
                current_price=18550.75,
                indicator_value=18500.25,
                signal_strength=0.27,  # 0.27% 돌파
                market_condition="bullish"
            )
        """
        session, repository = self._get_session_and_repository()

        try:
            # 1. 중복 체크 (옵션)
            if check_duplicate:
                if repository.exists_recent_signal(
                    symbol=symbol,
                    signal_type=signal_type,
                    minutes=duplicate_window_minutes,
                ):
                    print(
                        f"⚠️ 중복 신호 감지: {symbol} {signal_type} (최근 {duplicate_window_minutes}분 내 동일 신호 존재)"
                    )
                    return None

            # 2. 신호 엔티티 생성
            signal = TechnicalSignal(
                symbol=symbol,
                signal_type=signal_type,
                timeframe=timeframe,
                triggered_at=triggered_at if triggered_at else datetime.utcnow(),
                current_price=current_price,
                indicator_value=indicator_value,
                signal_strength=signal_strength,
                volume=volume,
                market_condition=market_condition,
                additional_context=(
                    str(additional_context) if additional_context else None
                ),
                alert_sent=False,  # 초기값은 False, 알림 발송 후 업데이트
            )

            # 3. 데이터베이스에 저장
            saved_signal = repository.save(signal)
            session.commit()

            # 🆕 4. 결과 추적 자동 시작 (모든 신호에 대해 실행)
            try:
                from app.technical_analysis.service.outcome_tracking_service import (
                    OutcomeTrackingService,
                )

                outcome_service = OutcomeTrackingService()
                outcome_service.initialize_outcome_tracking(saved_signal.id)
                print(f"📊 결과 추적 시작: 신호 ID {saved_signal.id}")
            except Exception as e:
                print(f"⚠️ 결과 추적 시작 실패: {e}")

            print(
                f"✅ 기술적 신호 저장 완료: {symbol} {signal_type} (ID: {saved_signal.id})"
            )
            return saved_signal

        except Exception as e:
            session.rollback()
            print(f"❌ 신호 저장 실패: {symbol} {signal_type} - {e}")
            return None
        finally:
            session.close()

    def save_ma_breakout_signal(
        self,
        symbol: str,
        timeframe: str,
        ma_period: int,
        breakout_direction: str,  # "up" or "down"
        current_price: float,
        ma_value: float,
        volume: Optional[int] = None,
    ) -> Optional[TechnicalSignal]:
        """
        이동평균선 돌파 신호 저장 (편의 함수)

        Args:
            symbol: 심볼
            timeframe: 시간대
            ma_period: 이동평균 기간 (20, 50, 200 등)
            breakout_direction: 돌파 방향 ("up" 또는 "down")
            current_price: 현재 가격
            ma_value: 이동평균값
            volume: 거래량

        Returns:
            저장된 신호 엔티티
        """
        # 신호 타입 생성
        signal_type = f"MA{ma_period}_breakout_{breakout_direction}"

        # 돌파폭 계산 (신호 강도)
        if breakout_direction == "up":
            signal_strength = ((current_price - ma_value) / ma_value) * 100
        else:  # down
            signal_strength = ((ma_value - current_price) / ma_value) * 100

        # 시장 상황 판단 (간단한 로직)
        market_condition = "bullish" if breakout_direction == "up" else "bearish"

        return self.save_signal(
            symbol=symbol,
            signal_type=signal_type,
            timeframe=timeframe,
            current_price=current_price,
            indicator_value=ma_value,
            signal_strength=signal_strength,
            volume=volume,
            market_condition=market_condition,
            additional_context={
                "ma_period": ma_period,
                "breakout_direction": breakout_direction,
            },
        )

    def save_rsi_signal(
        self,
        symbol: str,
        timeframe: str,
        rsi_value: float,
        current_price: float,
        signal_type_suffix: str,  # "overbought", "oversold", "bullish", "bearish"
        volume: Optional[int] = None,
    ) -> Optional[TechnicalSignal]:
        """
        RSI 신호 저장 (편의 함수)

        Args:
            symbol: 심볼
            timeframe: 시간대
            rsi_value: RSI 값
            current_price: 현재 가격
            signal_type_suffix: 신호 타입 접미사
            volume: 거래량

        Returns:
            저장된 신호 엔티티
        """
        signal_type = f"RSI_{signal_type_suffix}"

        # RSI 기준값에서 얼마나 벗어났는지 계산
        if signal_type_suffix == "overbought":
            signal_strength = rsi_value - 70  # 70에서 얼마나 초과했는지
            market_condition = "bearish"  # 과매수는 하락 신호
        elif signal_type_suffix == "oversold":
            signal_strength = 30 - rsi_value  # 30에서 얼마나 미달했는지
            market_condition = "bullish"  # 과매도는 상승 신호
        else:
            signal_strength = abs(rsi_value - 50)  # 50에서 얼마나 벗어났는지
            market_condition = (
                "bullish" if signal_type_suffix == "bullish" else "bearish"
            )

        return self.save_signal(
            symbol=symbol,
            signal_type=signal_type,
            timeframe=timeframe,
            current_price=current_price,
            indicator_value=rsi_value,
            signal_strength=signal_strength,
            volume=volume,
            market_condition=market_condition,
            additional_context={
                "rsi_value": rsi_value,
                "signal_reason": signal_type_suffix,
            },
        )

    def save_bollinger_signal(
        self,
        symbol: str,
        timeframe: str,
        current_price: float,
        band_value: float,  # 터치한 밴드값 (상단 또는 하단)
        signal_type_suffix: str,  # "touch_upper", "touch_lower", "break_upper", "break_lower"
        volume: Optional[int] = None,
    ) -> Optional[TechnicalSignal]:
        """
        볼린저 밴드 신호 저장 (편의 함수)

        Args:
            symbol: 심볼
            timeframe: 시간대
            current_price: 현재 가격
            band_value: 밴드값
            signal_type_suffix: 신호 타입 접미사
            volume: 거래량

        Returns:
            저장된 신호 엔티티
        """
        signal_type = f"BB_{signal_type_suffix}"

        # 밴드에서 얼마나 벗어났는지 계산
        signal_strength = abs((current_price - band_value) / band_value) * 100

        # 시장 상황 판단
        if "upper" in signal_type_suffix:
            market_condition = "bearish"  # 상단 밴드는 하락 신호
        else:  # lower
            market_condition = "bullish"  # 하단 밴드는 상승 신호

        return self.save_signal(
            symbol=symbol,
            signal_type=signal_type,
            timeframe=timeframe,
            current_price=current_price,
            indicator_value=band_value,
            signal_strength=signal_strength,
            volume=volume,
            market_condition=market_condition,
            additional_context={
                "band_type": "upper" if "upper" in signal_type_suffix else "lower",
                "action": "touch" if "touch" in signal_type_suffix else "break",
            },
        )

    def save_cross_signal(
        self,
        symbol: str,
        cross_type: str,  # "golden_cross" or "dead_cross"
        ma_short_value: float,  # 단기 이동평균값 (보통 50일선)
        ma_long_value: float,  # 장기 이동평균값 (보통 200일선)
        current_price: float,
        volume: Optional[int] = None,
    ) -> Optional[TechnicalSignal]:
        """
        크로스 신호 저장 (골든크로스/데드크로스)

        Args:
            symbol: 심볼
            cross_type: 크로스 타입
            ma_short_value: 단기 이동평균값
            ma_long_value: 장기 이동평균값
            current_price: 현재 가격
            volume: 거래량

        Returns:
            저장된 신호 엔티티
        """
        # 두 이동평균선의 차이 계산 (신호 강도)
        signal_strength = abs((ma_short_value - ma_long_value) / ma_long_value) * 100

        # 시장 상황 판단
        market_condition = "bullish" if cross_type == "golden_cross" else "bearish"

        return self.save_signal(
            symbol=symbol,
            signal_type=cross_type,
            timeframe="1day",  # 크로스 신호는 보통 일봉에서 발생
            current_price=current_price,
            indicator_value=ma_long_value,  # 기준이 되는 장기 이동평균값
            signal_strength=signal_strength,
            volume=volume,
            market_condition=market_condition,
            additional_context={
                "ma_short": ma_short_value,
                "ma_long": ma_long_value,
                "cross_type": cross_type,
            },
        )

    # =================================================================
    # 알림 상태 관리
    # =================================================================

    def mark_alert_sent(self, signal_id: int) -> bool:
        """
        신호의 알림 발송 상태를 업데이트

        Args:
            signal_id: 신호 ID

        Returns:
            업데이트 성공 여부
        """
        session, repository = self._get_session_and_repository()

        try:
            success = repository.update_alert_status(signal_id, True)
            session.commit()

            if success:
                print(f"✅ 알림 발송 상태 업데이트: 신호 ID {signal_id}")
            else:
                print(f"⚠️ 알림 상태 업데이트 실패: 신호 ID {signal_id} (신호 없음)")

            return success

        except Exception as e:
            session.rollback()
            print(f"❌ 알림 상태 업데이트 실패: {e}")
            return False
        finally:
            session.close()

    # =================================================================
    # 조회 함수들 (간단한 통계용)
    # =================================================================

    def get_recent_signals(
        self, symbol: Optional[str] = None, hours: int = 24, limit: int = 50
    ) -> List[TechnicalSignal]:
        """
        최근 발생한 신호들 조회

        Args:
            symbol: 심볼 필터 (선택사항)
            hours: 조회할 시간 범위
            limit: 최대 조회 개수

        Returns:
            최근 신호 리스트
        """
        session, repository = self._get_session_and_repository()

        try:
            signals = repository.find_recent_signals(hours=hours, symbol=symbol)
            return signals[:limit]  # 제한 개수만큼만 반환
        finally:
            session.close()

    def get_signal_count_today(self, symbol: Optional[str] = None) -> int:
        """
        오늘 발생한 신호 개수

        Args:
            symbol: 심볼 필터 (선택사항)

        Returns:
            오늘 신호 개수
        """
        signals = self.get_recent_signals(symbol=symbol, hours=24)
        return len(signals)

    def __del__(self):
        """소멸자 - 세션 정리"""
        if self.session:
            self.session.close()
