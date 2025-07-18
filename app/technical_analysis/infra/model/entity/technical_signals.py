"""
기술적 신호 엔티티

이 파일은 기술적 분석에서 발생하는 모든 신호들을 데이터베이스에 저장하기 위한 엔티티입니다.

기술적 신호란?
- 이동평균선 돌파/이탈 (MA20, MA50, MA200 등)
- RSI 과매수/과매도 신호 (70 이상, 30 이하)
- 볼린저 밴드 터치/돌파
- 골든크로스/데드크로스 등

이 데이터를 저장하는 이유:
1. 백테스팅: 과거 신호들의 성과 분석
2. 패턴 분석: 어떤 신호 조합이 효과적인지 분석
3. 알림 최적화: 성과가 좋은 신호만 알림 발송
4. 통계 분석: 신호 발생 빈도, 성공률 등 분석
"""

from sqlalchemy import (
    Column,
    BigInteger,
    String,
    DECIMAL,
    DateTime,
    Boolean,
    Text,
    Index,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.common.infra.database.config.database_config import Base


class TechnicalSignal(Base):
    """
    기술적 신호 테이블

    모든 기술적 분석 신호가 발생할 때마다 이 테이블에 기록됩니다.
    예: "NQ=F에서 200일선을 상향 돌파했다", "RSI가 70을 넘어 과매수 상태가 되었다" 등
    """

    __tablename__ = "technical_signals"

    # =================================================================
    # 기본 식별 정보
    # =================================================================

    id = Column(
        BigInteger, primary_key=True, autoincrement=True, comment="신호 고유 ID"
    )

    symbol = Column(String(20), nullable=False, comment="심볼 (예: NQ=F, ^IXIC, AAPL)")

    signal_type = Column(
        String(50),
        nullable=False,
        comment="""
        신호 타입 (예시):
        - MA20_breakout_up: 20일선 상향 돌파
        - MA200_breakout_down: 200일선 하향 이탈
        - RSI_overbought: RSI 과매수 (70 이상)
        - RSI_oversold: RSI 과매도 (30 이하)
        - BB_touch_upper: 볼린저 밴드 상단 터치
        - golden_cross: 골든크로스 (50일선이 200일선 상향돌파)
        - dead_cross: 데드크로스 (50일선이 200일선 하향이탈)
        """,
    )

    timeframe = Column(
        String(10), nullable=False, comment="시간대 (1min, 15min, 1hour, 1day)"
    )

    triggered_at = Column(DateTime, nullable=False, comment="신호 발생 시점 (UTC 기준)")

    # =================================================================
    # 신호 발생 시점의 가격 및 지표 정보
    # =================================================================

    current_price = Column(
        DECIMAL(12, 4), nullable=False, comment="신호 발생 시점의 현재 가격"
    )

    indicator_value = Column(
        DECIMAL(12, 4),
        nullable=True,
        comment="""
        신호와 관련된 지표값
        - 이동평균 신호: MA값 (예: 200일선 값)
        - RSI 신호: RSI값 (예: 72.5)
        - 볼린저밴드 신호: 상단/하단 밴드값
        """,
    )

    signal_strength = Column(
        DECIMAL(8, 4),
        nullable=True,
        comment="""
        신호의 강도 (%)
        - 이동평균 돌파: 돌파폭 (현재가 - MA값) / MA값 * 100
        - RSI: 과매수/과매도 정도 (70 이상이면 70에서 얼마나 벗어났는지)
        - 볼린저밴드: 밴드에서 얼마나 벗어났는지
        """,
    )

    # =================================================================
    # 추가 컨텍스트 정보
    # =================================================================

    volume = Column(
        BigInteger,
        nullable=True,
        comment="신호 발생 시점의 거래량 (거래량 급증 여부 판단용)",
    )

    market_condition = Column(
        String(20),
        nullable=True,
        comment="""
        신호 발생 시점의 시장 상황
        - bullish: 상승장
        - bearish: 하락장  
        - sideways: 횡보장
        - volatile: 변동성 큰 상황
        """,
    )

    additional_context = Column(
        Text,
        nullable=True,
        comment="""
        추가 컨텍스트 정보 (JSON 형태)
        예: {"prev_signals": ["RSI_overbought"], "market_news": "FOMC 발표"}
        """,
    )

    # =================================================================
    # 알림 및 메타데이터
    # =================================================================

    alert_sent = Column(Boolean, default=False, comment="텔레그램 알림 발송 여부")

    alert_sent_at = Column(DateTime, nullable=True, comment="알림 발송 시점")

    created_at = Column(DateTime, default=func.now(), comment="레코드 생성 시점")

    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), comment="레코드 수정 시점"
    )

    # =================================================================
    # 관계 설정 (ORM)
    # =================================================================

    # 신호 결과와의 관계 설정 (1:1 관계)
    outcome = relationship(
        "SignalOutcome",
        back_populates="signal",
        uselist=False,  # 1:1 관계이므로 단일 객체
        cascade="all, delete-orphan",  # 신호 삭제시 결과도 함께 삭제
    )

    # =================================================================
    # 인덱스 설정 (쿼리 성능 최적화)
    # =================================================================

    __table_args__ = (
        # 🆕 중복 방지: 같은 심볼, 신호타입, 시간대, 발생시점의 신호는 1개만 허용
        UniqueConstraint(
            "symbol",
            "signal_type",
            "timeframe",
            "triggered_at",
            name="uq_signal_unique",
        ),
        # 심볼 + 시간 기준 조회 최적화 (가장 많이 사용되는 쿼리)
        Index("idx_symbol_triggered_at", "symbol", "triggered_at"),
        # 신호 타입별 조회 최적화 (백테스팅에서 많이 사용)
        Index("idx_signal_type", "signal_type"),
        # 시간대별 조회 최적화
        Index("idx_timeframe", "timeframe"),
        # 시간 범위 조회 최적화 (특정 기간 신호 조회)
        Index("idx_triggered_at", "triggered_at"),
        # 복합 인덱스: 심볼 + 신호타입 + 시간대 (상세 분석용)
        Index("idx_symbol_signal_timeframe", "symbol", "signal_type", "timeframe"),
    )

    def __repr__(self):
        return f"<TechnicalSignal(id={self.id}, symbol={self.symbol}, signal_type={self.signal_type}, triggered_at={self.triggered_at})>"

    def to_dict(self):
        """
        엔티티를 딕셔너리로 변환 (API 응답용)
        """
        return {
            "id": self.id,
            "symbol": self.symbol,
            "signal_type": self.signal_type,
            "timeframe": self.timeframe,
            "triggered_at": (
                self.triggered_at.isoformat() if self.triggered_at else None
            ),
            "current_price": float(self.current_price) if self.current_price else None,
            "indicator_value": (
                float(self.indicator_value) if self.indicator_value else None
            ),
            "signal_strength": (
                float(self.signal_strength) if self.signal_strength else None
            ),
            "volume": self.volume,
            "market_condition": self.market_condition,
            "alert_sent": self.alert_sent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
