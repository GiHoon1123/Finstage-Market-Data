"""
일봉 가격 데이터 엔티티

이 파일은 나스닥 지수와 S&P 500 지수의 일봉 데이터를 저장하기 위한 엔티티입니다.

일봉 데이터란?
- 하루 동안의 시가, 고가, 저가, 종가, 거래량 정보
- 기술적 분석의 기본이 되는 데이터
- 이동평균, RSI, 볼린저밴드 등 모든 지표 계산의 기초

데이터 수집 방식:
- 초기: 10년치 과거 데이터 일괄 수집 (2015~2025)
- 일일: 매일 장 마감 후 최신 1일봉 추가
- 중복 방지: symbol + date 조합으로 유니크 제약
"""

from sqlalchemy import (
    Column,
    BigInteger,
    String,
    DECIMAL,
    Date,
    DateTime,
    Index,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from app.common.infra.database.config.database_config import Base


class DailyPrice(Base):
    """
    일봉 가격 데이터 테이블

    나스닥 지수(^IXIC)와 S&P 500 지수(^GSPC)의 일봉 데이터를 저장합니다.
    기술적 분석의 모든 계산은 이 테이블의 데이터를 기반으로 합니다.
    """

    __tablename__ = "daily_prices"

    # =================================================================
    # 기본 식별 정보
    # =================================================================

    id = Column(
        BigInteger, primary_key=True, autoincrement=True, comment="일봉 데이터 고유 ID"
    )

    symbol = Column(
        String(10), nullable=False, comment="심볼 (^IXIC: 나스닥, ^GSPC: S&P 500)"
    )

    date = Column(Date, nullable=False, comment="거래일 (YYYY-MM-DD)")

    # =================================================================
    # OHLCV 데이터 (Open, High, Low, Close, Volume)
    # =================================================================

    open_price = Column(DECIMAL(12, 4), nullable=False, comment="시가 (장 시작 가격)")

    high_price = Column(
        DECIMAL(12, 4), nullable=False, comment="고가 (하루 중 최고 가격)"
    )

    low_price = Column(
        DECIMAL(12, 4), nullable=False, comment="저가 (하루 중 최저 가격)"
    )

    close_price = Column(
        DECIMAL(12, 4), nullable=False, comment="종가 (장 마감 가격, 가장 중요!)"
    )

    volume = Column(
        BigInteger, nullable=True, comment="거래량 (하루 총 거래된 주식 수)"
    )

    # =================================================================
    # 추가 계산 필드 (선택사항)
    # =================================================================

    price_change = Column(
        DECIMAL(12, 4),
        nullable=True,
        comment="""
        가격 변화량 (종가 - 전일 종가)
        양수: 상승, 음수: 하락, 0: 보합
        """,
    )

    price_change_percent = Column(
        DECIMAL(8, 4),
        nullable=True,
        comment="""
        가격 변화율 (%)
        계산식: (종가 - 전일종가) / 전일종가 * 100
        """,
    )

    # =================================================================
    # 메타데이터
    # =================================================================

    created_at = Column(DateTime, default=func.now(), comment="레코드 생성 시점")

    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), comment="레코드 수정 시점"
    )

    # =================================================================
    # 제약조건 및 인덱스
    # =================================================================

    __table_args__ = (
        # 중복 방지: 같은 심볼의 같은 날짜 데이터는 1개만 허용
        UniqueConstraint("symbol", "date", name="uq_symbol_date"),
        # 심볼별 조회 최적화 (가장 많이 사용되는 쿼리)
        Index("idx_symbol", "symbol"),
        # 날짜별 조회 최적화 (특정 기간 데이터 조회)
        Index("idx_date", "date"),
        # 심볼 + 날짜 범위 조회 최적화 (백테스팅에서 많이 사용)
        Index("idx_symbol_date_range", "symbol", "date"),
        # 최신 데이터 조회 최적화
        Index("idx_symbol_date_desc", "symbol", "date"),
    )

    def __repr__(self):
        return f"<DailyPrice(symbol={self.symbol}, date={self.date}, close={self.close_price})>"

    def to_dict(self):
        """
        엔티티를 딕셔너리로 변환 (API 응답용)
        """
        return {
            "id": self.id,
            "symbol": self.symbol,
            "date": self.date.isoformat() if self.date else None,
            "ohlcv": {
                "open": float(self.open_price) if self.open_price else None,
                "high": float(self.high_price) if self.high_price else None,
                "low": float(self.low_price) if self.low_price else None,
                "close": float(self.close_price) if self.close_price else None,
                "volume": self.volume,
            },
            "change": {
                "amount": float(self.price_change) if self.price_change else None,
                "percent": (
                    float(self.price_change_percent)
                    if self.price_change_percent
                    else None
                ),
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def calculate_daily_return(self, previous_close: float) -> float:
        """
        일일 수익률 계산

        Args:
            previous_close: 전일 종가

        Returns:
            일일 수익률 (%)
        """
        if not previous_close or previous_close == 0:
            return 0.0

        return ((float(self.close_price) - previous_close) / previous_close) * 100

    def is_green_candle(self) -> bool:
        """
        양봉인지 확인 (종가 > 시가)

        Returns:
            True: 양봉 (상승), False: 음봉 (하락)
        """
        return float(self.close_price) > float(self.open_price)

    def get_candle_body_size(self) -> float:
        """
        캔들 몸통 크기 계산

        Returns:
            |종가 - 시가| 절댓값
        """
        return abs(float(self.close_price) - float(self.open_price))

    def get_upper_shadow_size(self) -> float:
        """
        위꼬리 크기 계산

        Returns:
            고가 - max(시가, 종가)
        """
        body_top = max(float(self.open_price), float(self.close_price))
        return float(self.high_price) - body_top

    def get_lower_shadow_size(self) -> float:
        """
        아래꼬리 크기 계산

        Returns:
            min(시가, 종가) - 저가
        """
        body_bottom = min(float(self.open_price), float(self.close_price))
        return body_bottom - float(self.low_price)
