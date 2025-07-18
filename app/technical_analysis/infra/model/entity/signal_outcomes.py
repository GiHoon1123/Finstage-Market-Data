"""
신호 결과 추적 엔티티

이 파일은 기술적 분석 신호가 발생한 후의 결과를 추적하기 위한 엔티티입니다.

신호 결과 추적이란?
- 200일선 돌파 신호 발생 후 1시간, 1일, 1주일, 1개월 후 실제 수익률은?
- RSI 과매수 신호 후 실제로 가격이 하락했는가?
- 골든크로스 후 평균 수익률은 얼마인가?

이 데이터의 활용:
1. 백테스팅: 과거 신호들의 실제 성과 분석
2. 신호 품질 평가: 어떤 신호가 가장 정확한가?
3. 알림 최적화: 성과가 좋은 신호만 알림 발송
4. 매매 전략 개발: 효과적인 신호 조합 발견
5. 리스크 관리: 최대 손실률, 승률 등 분석

데이터 수집 방식:
- 신호 발생 후 1시간마다 현재 가격 체크
- 1시간, 4시간, 1일, 1주일, 1개월 후 수익률 계산
- 최대 수익률과 최대 손실률도 함께 추적
- 성공/실패 여부를 다양한 기준으로 판정
"""

from sqlalchemy import (
    Column,
    BigInteger,
    DECIMAL,
    DateTime,
    Boolean,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.common.infra.database.config.database_config import Base


class SignalOutcome(Base):
    """
    신호 결과 추적 테이블

    각 기술적 신호가 발생한 후의 실제 결과를 시간대별로 추적합니다.
    예: "200일선 돌파 신호 후 1주일간 +3.5% 수익률을 기록했다"
    """

    __tablename__ = "signal_outcomes"

    # =================================================================
    # 기본 식별 정보
    # =================================================================

    id = Column(
        BigInteger, primary_key=True, autoincrement=True, comment="결과 추적 고유 ID"
    )

    signal_id = Column(
        BigInteger,
        ForeignKey("technical_signals.id", ondelete="CASCADE"),
        nullable=False,
        comment="추적 대상 신호의 ID (technical_signals 테이블 참조)",
    )

    # =================================================================
    # 시간별 가격 추적 (신호 발생 후 N시간/일 후의 가격)
    # =================================================================

    price_1h_after = Column(
        DECIMAL(12, 4), nullable=True, comment="신호 발생 1시간 후 가격"
    )

    price_4h_after = Column(
        DECIMAL(12, 4), nullable=True, comment="신호 발생 4시간 후 가격"
    )

    price_1d_after = Column(
        DECIMAL(12, 4), nullable=True, comment="신호 발생 1일(24시간) 후 가격"
    )

    price_1w_after = Column(
        DECIMAL(12, 4), nullable=True, comment="신호 발생 1주일(7일) 후 가격"
    )

    price_1m_after = Column(
        DECIMAL(12, 4), nullable=True, comment="신호 발생 1개월(30일) 후 가격"
    )

    # =================================================================
    # 수익률 계산 (신호 발생 시점 대비 수익률 %)
    # =================================================================

    return_1h = Column(
        DECIMAL(8, 4),
        nullable=True,
        comment="""
        1시간 후 수익률 (%)
        계산식: (1시간후가격 - 신호발생시가격) / 신호발생시가격 * 100
        예: +2.5 (2.5% 상승), -1.2 (-1.2% 하락)ㅁ
        """,
    )

    return_4h = Column(DECIMAL(8, 4), nullable=True, comment="4시간 후 수익률 (%)")

    return_1d = Column(DECIMAL(8, 4), nullable=True, comment="1일 후 수익률 (%)")

    return_1w = Column(DECIMAL(8, 4), nullable=True, comment="1주일 후 수익률 (%)")

    return_1m = Column(DECIMAL(8, 4), nullable=True, comment="1개월 후 수익률 (%)")

    # =================================================================
    # 최대/최소 추적 (신호 발생 후 도달한 최고점/최저점)
    # =================================================================

    max_price_reached = Column(
        DECIMAL(12, 4),
        nullable=True,
        comment="""
        신호 발생 후 도달한 최고 가격
        - 상승 신호의 경우: 얼마나 높이 올라갔는지 확인
        - 하락 신호의 경우: 반등이 얼마나 있었는지 확인
        """,
    )

    min_price_reached = Column(
        DECIMAL(12, 4),
        nullable=True,
        comment="""
        신호 발생 후 도달한 최저 가격
        - 상승 신호의 경우: 중간에 얼마나 떨어졌는지 확인
        - 하락 신호의 경우: 얼마나 낮게 떨어졌는지 확인
        """,
    )

    max_return = Column(
        DECIMAL(8, 4),
        nullable=True,
        comment="""
        최대 수익률 (%)
        신호 발생 후 가장 좋았을 때의 수익률
        예: 200일선 돌파 후 최대 +8.5%까지 올라갔다
        """,
    )

    max_drawdown = Column(
        DECIMAL(8, 4),
        nullable=True,
        comment="""
        최대 손실률 (%)
        신호 발생 후 가장 나빴을 때의 손실률 (음수)
        예: RSI 과매수 신호 후 최대 -5.2%까지 떨어졌다
        """,
    )

    min_return = Column(
        DECIMAL(8, 4),
        nullable=True,
        comment="최소 수익률 (%) - 추적 기간 중 가장 낮은 수익률",
    )

    # =================================================================
    # 성공/실패 판정 (다양한 기준으로 신호의 성공 여부 평가)
    # =================================================================

    is_successful_1h = Column(
        Boolean,
        nullable=True,
        comment="""
        1시간 기준 성공 여부
        - 상승 신호: 1시간 후 가격이 올랐으면 True
        - 하락 신호: 1시간 후 가격이 떨어졌으면 True
        - 중립 신호: 특정 기준에 따라 판정
        """,
    )

    is_successful_1d = Column(Boolean, nullable=True, comment="1일 기준 성공 여부")

    is_successful_1w = Column(Boolean, nullable=True, comment="1주일 기준 성공 여부")

    is_successful_1m = Column(Boolean, nullable=True, comment="1개월 기준 성공 여부")

    # =================================================================
    # 추가 분석 지표
    # =================================================================

    volatility_1d = Column(
        DECIMAL(8, 4),
        nullable=True,
        comment="""
        1일간 변동성 (%)
        신호 발생 후 1일간 가격 변동의 표준편차
        높을수록 가격이 많이 흔들렸다는 의미
        """,
    )

    volatility_1w = Column(DECIMAL(8, 4), nullable=True, comment="1주일간 변동성 (%)")

    trend_strength = Column(
        DECIMAL(8, 4),
        nullable=True,
        comment="""
        추세 강도 점수 (0~100)
        신호 방향으로 얼마나 일관되게 움직였는지 측정
        100: 완벽한 일방향 움직임
        0: 완전한 횡보 또는 반대 방향 움직임
        """,
    )

    # =================================================================
    # 메타데이터
    # =================================================================

    last_updated_at = Column(
        DateTime, nullable=True, comment="마지막 업데이트 시점 (가격 데이터 수집 시점)"
    )

    is_complete = Column(
        Boolean,
        default=False,
        comment="""
        추적 완료 여부
        - False: 아직 추적 중 (1개월이 지나지 않음)
        - True: 추적 완료 (1개월 후 데이터까지 수집 완료)
        """,
    )

    created_at = Column(DateTime, default=func.now(), comment="레코드 생성 시점")

    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), comment="레코드 수정 시점"
    )

    # =================================================================
    # 관계 설정 (ORM)
    # =================================================================

    # 원본 신호와의 관계 설정
    signal = relationship(
        "TechnicalSignal",
        back_populates="outcome",
    )

    # =================================================================
    # 인덱스 설정 (쿼리 성능 최적화)
    # =================================================================

    __table_args__ = (
        # 🆕 중복 방지: 하나의 신호에 대해서는 하나의 결과만 허용
        UniqueConstraint("signal_id", name="uq_signal_outcome"),
        # 신호 ID 기준 조회 최적화 (가장 많이 사용)
        Index("idx_signal_id", "signal_id"),
        # 완료 상태별 조회 최적화 (배치 작업에서 사용)
        Index("idx_is_complete", "is_complete"),
        # 업데이트 시간 기준 조회 최적화 (오래된 데이터 찾기)
        Index("idx_last_updated_at", "last_updated_at"),
        # 성공률 분석용 복합 인덱스
        Index("idx_success_analysis", "is_successful_1d", "is_successful_1w"),
        # 수익률 분석용 인덱스
        Index("idx_returns", "return_1d", "return_1w"),
    )

    def __repr__(self):
        return f"<SignalOutcome(id={self.id}, signal_id={self.signal_id}, return_1d={self.return_1d})>"

    def to_dict(self):
        """
        엔티티를 딕셔너리로 변환 (API 응답용)
        """
        return {
            "id": self.id,
            "signal_id": self.signal_id,
            "returns": {
                "1h": float(self.return_1h) if self.return_1h else None,
                "4h": float(self.return_4h) if self.return_4h else None,
                "1d": float(self.return_1d) if self.return_1d else None,
                "1w": float(self.return_1w) if self.return_1w else None,
                "1m": float(self.return_1m) if self.return_1m else None,
            },
            "extremes": {
                "max_return": float(self.max_return) if self.max_return else None,
                "max_drawdown": float(self.max_drawdown) if self.max_drawdown else None,
            },
            "success_rates": {
                "1h": self.is_successful_1h,
                "1d": self.is_successful_1d,
                "1w": self.is_successful_1w,
                "1m": self.is_successful_1m,
            },
            "analysis": {
                "volatility_1d": (
                    float(self.volatility_1d) if self.volatility_1d else None
                ),
                "volatility_1w": (
                    float(self.volatility_1w) if self.volatility_1w else None
                ),
                "trend_strength": (
                    float(self.trend_strength) if self.trend_strength else None
                ),
            },
            "metadata": {
                "is_complete": self.is_complete,
                "last_updated_at": (
                    self.last_updated_at.isoformat() if self.last_updated_at else None
                ),
                "created_at": self.created_at.isoformat() if self.created_at else None,
            },
        }

    def calculate_success_rate(self, timeframe: str = "1d") -> bool:
        """
        신호의 성공 여부를 계산

        Args:
            timeframe: 평가 기간 ('1h', '1d', '1w', '1m')

        Returns:
            성공 여부 (True/False)

        성공 기준:
        - 상승 신호 (breakout_up, golden_cross, oversold 등): 수익률 > 0
        - 하락 신호 (breakout_down, dead_cross, overbought 등): 수익률 < 0
        - 중립 신호: 절대값 기준으로 판정
        """
        if not hasattr(self, "signal") or not self.signal:
            return False

        # 해당 시간대의 수익률 가져오기
        return_value = getattr(self, f"return_{timeframe}", None)
        if return_value is None:
            return False

        signal_type = self.signal.signal_type

        # 상승 신호들
        if any(
            keyword in signal_type.lower()
            for keyword in [
                "breakout_up",
                "golden_cross",
                "oversold",
                "bullish",
                "touch_lower",
            ]
        ):
            return float(return_value) > 0

        # 하락 신호들
        elif any(
            keyword in signal_type.lower()
            for keyword in [
                "breakout_down",
                "dead_cross",
                "overbought",
                "bearish",
                "touch_upper",
            ]
        ):
            return float(return_value) < 0

        # 중립 신호들 (절대값이 클수록 성공)
        else:
            return abs(float(return_value)) > 1.0  # 1% 이상 움직이면 성공
