"""
신호 패턴 분석 엔티티

이 파일은 여러 기술적 신호들이 조합되어 나타나는 패턴을 분석하기 위한 엔티티입니다.

신호 패턴이란?
- RSI 과매수 → 볼린저 밴드 상단 터치 → 가격 하락 (연속 패턴)
- 200일선 돌파 + 거래량 급증 (동시 패턴)
- 골든크로스 발생 전 50일선 상승 추세 (선행 패턴)

패턴 분석의 목적:
1. 신호 조합의 효과 측정: 단일 신호 vs 복합 신호의 성과 비교
2. 시장 상황별 패턴 발견: 상승장/하락장에서 다른 패턴의 효과
3. 타이밍 최적화: 어떤 순서로 신호가 나타날 때 가장 효과적인가?
4. 리스크 관리: 위험한 패턴과 안전한 패턴 구분
5. 자동 매매 전략: 효과적인 패턴을 기반으로 한 알고리즘 개발

패턴 유형:
- Sequential Pattern: A 신호 → B 신호 → C 신호 (순차적)
- Concurrent Pattern: A 신호 + B 신호 (동시 발생)
- Leading Pattern: A 신호 → (시간 간격) → B 신호 (선행 지표)
"""

from sqlalchemy import (
    Column,
    BigInteger,
    String,
    DECIMAL,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.common.infra.database.config.database_config import Base


class SignalPattern(Base):
    """
    신호 패턴 분석 테이블

    여러 기술적 신호들의 조합 패턴과 그 결과를 추적합니다.
    예: "RSI 과매수 후 볼린저 상단 터치 패턴은 80% 확률로 하락한다"
    """

    __tablename__ = "signal_patterns"

    # =================================================================
    # 기본 식별 정보
    # =================================================================

    id = Column(
        BigInteger, primary_key=True, autoincrement=True, comment="패턴 고유 ID"
    )

    pattern_name = Column(
        String(100),
        nullable=False,
        comment="""
        패턴 이름 (예시):
        - RSI_overbought_then_BB_upper: RSI 과매수 후 볼린저 상단 터치
        - MA200_breakout_with_volume: 200일선 돌파 + 거래량 급증
        - golden_cross_after_consolidation: 횡보 후 골든크로스
        - triple_bottom_reversal: 삼중 바닥 반전 패턴
        """,
    )

    pattern_type = Column(
        String(20),
        nullable=False,
        comment="""
        패턴 유형:
        - sequential: 순차적 패턴 (A → B → C)
        - concurrent: 동시 발생 패턴 (A + B + C)
        - leading: 선행 지표 패턴 (A → 시간 간격 → B)
        - reversal: 반전 패턴
        - continuation: 지속 패턴
        """,
    )

    symbol = Column(String(20), nullable=False, comment="패턴이 발생한 심볼")

    timeframe = Column(String(10), nullable=False, comment="패턴 분석 시간대")

    # =================================================================
    # 패턴 구성 신호들 (최대 5개까지 지원)
    # =================================================================

    first_signal_id = Column(
        BigInteger,
        ForeignKey("technical_signals.id"),
        nullable=False,
        comment="첫 번째 신호 ID (패턴의 시작점)",
    )

    second_signal_id = Column(
        BigInteger,
        ForeignKey("technical_signals.id"),
        nullable=True,
        comment="두 번째 신호 ID",
    )

    third_signal_id = Column(
        BigInteger,
        ForeignKey("technical_signals.id"),
        nullable=True,
        comment="세 번째 신호 ID",
    )

    fourth_signal_id = Column(
        BigInteger,
        ForeignKey("technical_signals.id"),
        nullable=True,
        comment="네 번째 신호 ID",
    )

    fifth_signal_id = Column(
        BigInteger,
        ForeignKey("technical_signals.id"),
        nullable=True,
        comment="다섯 번째 신호 ID",
    )

    # =================================================================
    # 패턴 시간 정보
    # =================================================================

    pattern_start = Column(
        DateTime, nullable=False, comment="패턴 시작 시점 (첫 번째 신호 발생 시점)"
    )

    pattern_end = Column(
        DateTime, nullable=False, comment="패턴 완성 시점 (마지막 신호 발생 시점)"
    )

    pattern_duration_hours = Column(
        DECIMAL(8, 2),
        nullable=True,
        comment="""
        패턴 지속 시간 (시간 단위)
        패턴 시작부터 완성까지 걸린 시간
        예: 2.5 (2시간 30분), 24.0 (1일), 168.0 (1주일)
        """,
    )

    # =================================================================
    # 패턴 결과 분석
    # =================================================================

    pattern_outcome_1h = Column(
        DECIMAL(8, 4), nullable=True, comment="패턴 완성 후 1시간 후 수익률 (%)"
    )

    pattern_outcome_1d = Column(
        DECIMAL(8, 4), nullable=True, comment="패턴 완성 후 1일 후 수익률 (%)"
    )

    pattern_outcome_1w = Column(
        DECIMAL(8, 4), nullable=True, comment="패턴 완성 후 1주일 후 수익률 (%)"
    )

    max_favorable_move = Column(
        DECIMAL(8, 4),
        nullable=True,
        comment="""
        패턴 방향으로 최대 움직임 (%)
        - 상승 패턴: 최대 상승률
        - 하락 패턴: 최대 하락률 (음수)
        """,
    )

    max_adverse_move = Column(
        DECIMAL(8, 4),
        nullable=True,
        comment="""
        패턴 반대 방향으로 최대 움직임 (%)
        - 상승 패턴: 최대 하락률 (음수)
        - 하락 패턴: 최대 상승률
        """,
    )

    # =================================================================
    # 패턴 성공/실패 판정
    # =================================================================

    is_successful_1h = Column(
        Boolean, nullable=True, comment="1시간 기준 패턴 성공 여부"
    )

    is_successful_1d = Column(Boolean, nullable=True, comment="1일 기준 패턴 성공 여부")

    is_successful_1w = Column(
        Boolean, nullable=True, comment="1주일 기준 패턴 성공 여부"
    )

    confidence_score = Column(
        DECIMAL(5, 2),
        nullable=True,
        comment="""
        패턴 신뢰도 점수 (0~100)
        - 100: 매우 강한 패턴 (높은 성공률)
        - 50: 중립적 패턴
        - 0: 매우 약한 패턴 (낮은 성공률)
        
        계산 요소:
        - 과거 동일 패턴의 성공률
        - 신호들 간의 시간 간격
        - 시장 상황과의 일치도
        - 거래량 등 부가 지표
        """,
    )

    # =================================================================
    # 패턴 컨텍스트 정보
    # =================================================================

    market_condition = Column(
        String(20),
        nullable=True,
        comment="""
        패턴 발생 시 시장 상황
        - strong_uptrend: 강한 상승 추세
        - weak_uptrend: 약한 상승 추세
        - sideways: 횡보
        - weak_downtrend: 약한 하락 추세
        - strong_downtrend: 강한 하락 추세
        """,
    )

    volatility_level = Column(
        String(10),
        nullable=True,
        comment="""
        패턴 발생 시 변동성 수준
        - low: 낮은 변동성 (< 1% 일일 변동)
        - medium: 보통 변동성 (1-3% 일일 변동)
        - high: 높은 변동성 (> 3% 일일 변동)
        """,
    )

    volume_profile = Column(
        String(20),
        nullable=True,
        comment="""
        패턴 발생 시 거래량 프로필
        - increasing: 거래량 증가 중
        - decreasing: 거래량 감소 중
        - spike: 거래량 급증
        - normal: 평상시 수준
        """,
    )

    # =================================================================
    # 패턴 메타데이터
    # =================================================================

    pattern_description = Column(
        Text,
        nullable=True,
        comment="""
        패턴에 대한 상세 설명 (JSON 형태)
        {
            "signals": ["RSI 과매수", "볼린저 상단 터치"],
            "sequence": "RSI가 먼저 70을 돌파한 후 2시간 내에 볼린저 상단 터치",
            "market_context": "상승 추세 중 과열 신호",
            "expected_outcome": "단기 조정 예상"
        }
        """,
    )

    similar_patterns_count = Column(
        BigInteger, default=0, comment="과거 동일한 패턴 발생 횟수 (참고용)"
    )

    # =================================================================
    # 시스템 메타데이터
    # =================================================================

    created_at = Column(DateTime, default=func.now(), comment="패턴 레코드 생성 시점")

    updated_at = Column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        comment="패턴 레코드 수정 시점",
    )

    analyzed_at = Column(DateTime, nullable=True, comment="패턴 분석 완료 시점")

    # =================================================================
    # 관계 설정 (ORM)
    # =================================================================

    # 패턴을 구성하는 신호들과의 관계
    first_signal = relationship("TechnicalSignal", foreign_keys=[first_signal_id])
    second_signal = relationship("TechnicalSignal", foreign_keys=[second_signal_id])
    third_signal = relationship("TechnicalSignal", foreign_keys=[third_signal_id])
    fourth_signal = relationship("TechnicalSignal", foreign_keys=[fourth_signal_id])
    fifth_signal = relationship("TechnicalSignal", foreign_keys=[fifth_signal_id])

    # =================================================================
    # 인덱스 설정 (쿼리 성능 최적화)
    # =================================================================

    __table_args__ = (
        # 패턴 이름별 조회 최적화
        Index("idx_pattern_name", "pattern_name"),
        # 심볼 + 시간대별 조회 최적화
        Index("idx_symbol_timeframe", "symbol", "timeframe"),
        # 패턴 타입별 조회 최적화
        Index("idx_pattern_type", "pattern_type"),
        # 성공률 분석용 인덱스
        Index("idx_success_analysis", "is_successful_1d", "confidence_score"),
        # 시장 상황별 분석용 인덱스
        Index("idx_market_condition", "market_condition", "volatility_level"),
        # 시간 범위 조회 최적화
        Index("idx_pattern_time_range", "pattern_start", "pattern_end"),
    )

    def __repr__(self):
        return f"<SignalPattern(id={self.id}, pattern_name={self.pattern_name}, symbol={self.symbol})>"

    def to_dict(self):
        """
        엔티티를 딕셔너리로 변환 (API 응답용)
        """
        return {
            "id": self.id,
            "pattern_name": self.pattern_name,
            "pattern_type": self.pattern_type,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timing": {
                "pattern_start": (
                    self.pattern_start.isoformat() if self.pattern_start else None
                ),
                "pattern_end": (
                    self.pattern_end.isoformat() if self.pattern_end else None
                ),
                "duration_hours": (
                    float(self.pattern_duration_hours)
                    if self.pattern_duration_hours
                    else None
                ),
            },
            "signals": {
                "first_signal_id": self.first_signal_id,
                "second_signal_id": self.second_signal_id,
                "third_signal_id": self.third_signal_id,
                "fourth_signal_id": self.fourth_signal_id,
                "fifth_signal_id": self.fifth_signal_id,
            },
            "outcomes": {
                "1h": (
                    float(self.pattern_outcome_1h) if self.pattern_outcome_1h else None
                ),
                "1d": (
                    float(self.pattern_outcome_1d) if self.pattern_outcome_1d else None
                ),
                "1w": (
                    float(self.pattern_outcome_1w) if self.pattern_outcome_1w else None
                ),
            },
            "performance": {
                "max_favorable_move": (
                    float(self.max_favorable_move) if self.max_favorable_move else None
                ),
                "max_adverse_move": (
                    float(self.max_adverse_move) if self.max_adverse_move else None
                ),
                "confidence_score": (
                    float(self.confidence_score) if self.confidence_score else None
                ),
            },
            "success_rates": {
                "1h": self.is_successful_1h,
                "1d": self.is_successful_1d,
                "1w": self.is_successful_1w,
            },
            "context": {
                "market_condition": self.market_condition,
                "volatility_level": self.volatility_level,
                "volume_profile": self.volume_profile,
            },
            "metadata": {
                "similar_patterns_count": self.similar_patterns_count,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "analyzed_at": (
                    self.analyzed_at.isoformat() if self.analyzed_at else None
                ),
            },
        }

    def get_signal_sequence(self) -> list:
        """
        패턴을 구성하는 신호들의 순서를 반환

        Returns:
            신호 ID들의 리스트 (None 제외)
        """
        signals = [
            self.first_signal_id,
            self.second_signal_id,
            self.third_signal_id,
            self.fourth_signal_id,
            self.fifth_signal_id,
        ]
        return [signal_id for signal_id in signals if signal_id is not None]

    def calculate_pattern_strength(self) -> float:
        """
        패턴의 강도를 계산 (0~100)

        Returns:
            패턴 강도 점수

        계산 요소:
        - 성공률 (가중치 40%)
        - 신뢰도 점수 (가중치 30%)
        - 과거 유사 패턴 횟수 (가중치 20%)
        - 시장 상황 일치도 (가중치 10%)
        """
        strength = 0.0

        # 성공률 기반 점수 (40%)
        success_count = sum(
            [
                1
                for success in [
                    self.is_successful_1h,
                    self.is_successful_1d,
                    self.is_successful_1w,
                ]
                if success is True
            ]
        )
        total_evaluations = sum(
            [
                1
                for success in [
                    self.is_successful_1h,
                    self.is_successful_1d,
                    self.is_successful_1w,
                ]
                if success is not None
            ]
        )

        if total_evaluations > 0:
            success_rate = success_count / total_evaluations
            strength += success_rate * 40

        # 신뢰도 점수 (30%)
        if self.confidence_score:
            strength += float(self.confidence_score) * 0.3

        # 과거 패턴 횟수 (20%) - 많을수록 신뢰도 높음
        if self.similar_patterns_count:
            pattern_score = min(self.similar_patterns_count / 10, 1.0) * 20
            strength += pattern_score

        # 시장 상황 일치도 (10%) - 적절한 시장 상황에서 발생했는지
        if self.market_condition and self.volatility_level:
            context_score = 10  # 기본 점수
            strength += context_score

        return min(strength, 100.0)
