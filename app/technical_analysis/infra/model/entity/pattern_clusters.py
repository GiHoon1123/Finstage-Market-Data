"""
패턴 클러스터링 결과 엔티티

이 파일은 K-means 클러스터링을 통해 발견된 패턴 그룹들을 저장하기 위한 엔티티입니다.

패턴 클러스터링이란?
- 유사한 특성을 가진 신호 패턴들을 자동으로 그룹화
- 예: "상승 신호 패턴 그룹", "하락 신호 패턴 그룹", "중립 패턴 그룹"
- K-means 알고리즘을 사용하여 패턴들을 N개 그룹으로 분류

클러스터링의 목적:
1. 패턴 단순화: 수백 개의 복잡한 패턴을 몇 개 그룹으로 정리
2. 투자 전략 최적화: 그룹별 성과 분석으로 효과적인 패턴 그룹 발견
3. 리스크 관리: 위험한 패턴 그룹과 안전한 패턴 그룹 구분
4. 자동화: 새로운 패턴이 어느 그룹에 속하는지 자동 분류
5. 일일 리포트: "오늘 상승 패턴 그룹에서 3개 신호 발생" 등의 요약 정보

클러스터 특성:
- 클러스터 중심점: 해당 그룹의 대표적인 특성 벡터
- 그룹 내 패턴 수: 해당 그룹에 속한 패턴들의 개수
- 평균 성공률: 그룹 내 패턴들의 평균 성공률
- 대표 패턴: 그룹을 가장 잘 나타내는 패턴들
"""

from sqlalchemy import (
    Column,
    BigInteger,
    String,
    DECIMAL,
    DateTime,
    Integer,
    Text,
    Index,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from app.common.infra.database.config.database_config import Base


class PatternCluster(Base):
    """
    패턴 클러스터링 결과 테이블

    K-means 클러스터링을 통해 발견된 패턴 그룹들의 정보를 저장합니다.
    예: "상승 신호 패턴 그룹에는 25개 패턴이 있고 평균 성공률은 68%이다"
    """

    __tablename__ = "pattern_clusters"

    # =================================================================
    # 기본 식별 정보
    # =================================================================

    id = Column(
        BigInteger, primary_key=True, autoincrement=True, comment="클러스터 고유 ID"
    )

    symbol = Column(
        String(20), nullable=False, comment="클러스터링 대상 심볼 (예: ^IXIC, ^GSPC)"
    )

    cluster_id = Column(
        Integer,
        nullable=False,
        comment="""
        클러스터 번호 (0부터 시작)
        예: 0, 1, 2, 3, 4, 5 (총 6개 그룹으로 분류한 경우)
        """,
    )

    cluster_name = Column(
        String(100),
        nullable=False,
        comment="""
        클러스터 이름 (자동 생성)
        예시:
        - RSI_상승_패턴: RSI 기반 상승 신호 패턴들
        - MA_하락_패턴: 이동평균 기반 하락 신호 패턴들
        - 볼린저_중립_패턴: 볼린저밴드 기반 중립 패턴들
        - 복합_상승_패턴: 여러 지표 조합 상승 패턴들
        """,
    )

    timeframe = Column(
        String(10), nullable=False, comment="클러스터링 시간대 (1min, 15min, 1day)"
    )

    # =================================================================
    # 클러스터 통계 정보
    # =================================================================

    pattern_count = Column(Integer, nullable=False, comment="클러스터에 속한 패턴 개수")

    avg_success_rate = Column(
        DECIMAL(5, 2),
        nullable=True,
        comment="""
        클러스터 평균 성공률 (%)
        클러스터 내 모든 패턴들의 성공률 평균
        예: 68.5 (68.5% 성공률)
        """,
    )

    avg_confidence_score = Column(
        DECIMAL(5, 2),
        nullable=True,
        comment="""
        클러스터 평균 신뢰도 점수 (0~100)
        클러스터 내 모든 패턴들의 신뢰도 점수 평균
        """,
    )

    avg_duration_hours = Column(
        DECIMAL(8, 2),
        nullable=True,
        comment="""
        클러스터 평균 패턴 지속 시간 (시간)
        클러스터 내 패턴들의 평균 지속 시간
        예: 4.5 (평균 4시간 30분)
        """,
    )

    # =================================================================
    # 클러스터 성향 분석
    # =================================================================

    bullish_tendency = Column(
        DECIMAL(5, 2),
        nullable=True,
        comment="""
        상승 성향 점수 (0~1)
        클러스터가 상승 패턴에 얼마나 치우쳐 있는지
        1.0: 완전한 상승 패턴 그룹
        0.0: 상승 패턴이 전혀 없음
        """,
    )

    bearish_tendency = Column(
        DECIMAL(5, 2),
        nullable=True,
        comment="""
        하락 성향 점수 (0~1)
        클러스터가 하락 패턴에 얼마나 치우쳐 있는지
        1.0: 완전한 하락 패턴 그룹
        0.0: 하락 패턴이 전혀 없음
        """,
    )

    dominant_signal_types = Column(
        Text,
        nullable=True,
        comment="""
        클러스터 내 주요 신호 타입들 (JSON 배열)
        예: ["RSI", "MA", "BB"] - RSI, 이동평균, 볼린저밴드가 주요 신호
        """,
    )

    # =================================================================
    # 클러스터 중심점 (K-means 알고리즘의 결과)
    # =================================================================

    cluster_center = Column(
        Text,
        nullable=True,
        comment="""
        클러스터 중심점 좌표 (JSON 배열)
        K-means 알고리즘에서 계산된 클러스터의 중심점
        예: [0.5, 1.0, 0.0, 0.8, 0.2, 1.0, 0.0, 0.3, 0.4, ...]
        
        각 차원의 의미:
        - 0: 지속시간 (정규화)
        - 1-6: 신호 타입별 원-핫 인코딩 (RSI, MA, BB, MACD, CROSS, VOLUME)
        - 7-8: 상승/하락 성향
        - 9-10: 시장 상황 (상승장/하락장)
        - 11-12: 시간적 특성 (요일/월)
        """,
    )

    cluster_radius = Column(
        DECIMAL(8, 4),
        nullable=True,
        comment="""
        클러스터 반경 (클러스터 내 패턴들의 평균 거리)
        작을수록 클러스터 내 패턴들이 유사함
        클수록 클러스터 내 패턴들이 다양함
        """,
    )

    # =================================================================
    # 대표 패턴 정보
    # =================================================================

    representative_patterns = Column(
        Text,
        nullable=True,
        comment="""
        대표 패턴들의 ID 목록 (JSON 배열)
        클러스터를 가장 잘 나타내는 패턴들 (최대 5개)
        예: [123, 456, 789] - signal_patterns 테이블의 ID들
        """,
    )

    pattern_examples = Column(
        Text,
        nullable=True,
        comment="""
        패턴 예시 설명 (JSON 객체)
        사용자가 이해하기 쉬운 패턴 설명들
        예: {
            "main_pattern": "RSI 과매도 후 20일선 돌파",
            "variations": ["RSI 30 이하 → MA20 상향돌파", "RSI 반등 + 거래량 증가"],
            "success_examples": ["2024-01-15: +3.2%", "2024-02-03: +2.8%"]
        }
        """,
    )

    # =================================================================
    # 클러스터링 메타데이터
    # =================================================================

    clustering_algorithm = Column(
        String(20),
        default="kmeans",
        comment="""
        사용된 클러스터링 알고리즘
        - kmeans: K-means 클러스터링
        - hierarchical: 계층적 클러스터링
        - dbscan: DBSCAN 클러스터링
        """,
    )

    n_clusters_total = Column(
        Integer, nullable=False, comment="전체 클러스터 개수 (예: 6개 그룹으로 분류)"
    )

    clustering_quality_score = Column(
        DECIMAL(5, 2),
        nullable=True,
        comment="""
        클러스터링 품질 점수 (0~100)
        클러스터링이 얼마나 잘 되었는지 평가
        - 100: 완벽한 클러스터링 (그룹 간 명확한 구분)
        - 0: 매우 나쁜 클러스터링 (그룹 간 구분 불가)
        
        계산 요소:
        - 클러스터 내 응집도 (Intra-cluster cohesion)
        - 클러스터 간 분리도 (Inter-cluster separation)
        - 실루엣 점수 (Silhouette score)
        """,
    )

    # =================================================================
    # 시스템 메타데이터
    # =================================================================

    clustered_at = Column(DateTime, nullable=False, comment="클러스터링 실행 시점")

    created_at = Column(DateTime, default=func.now(), comment="레코드 생성 시점")

    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), comment="레코드 수정 시점"
    )

    # =================================================================
    # 인덱스 설정 (쿼리 성능 최적화)
    # =================================================================

    __table_args__ = (
        # 🆕 중복 방지: 같은 심볼, 클러스터ID, 시간대, 클러스터링 시점의 결과는 1개만
        UniqueConstraint(
            "symbol",
            "cluster_id",
            "timeframe",
            "clustered_at",
            name="uq_cluster_unique",
        ),
        # 심볼 + 시간대별 조회 최적화 (가장 많이 사용)
        Index("idx_symbol_timeframe", "symbol", "timeframe"),
        # 클러스터 ID별 조회 최적화
        Index("idx_cluster_id", "cluster_id"),
        # 클러스터링 시점별 조회 최적화 (최신 결과 조회)
        Index("idx_clustered_at", "clustered_at"),
        # 성과 분석용 인덱스
        Index("idx_performance", "avg_success_rate", "avg_confidence_score"),
        # 성향 분석용 인덱스
        Index("idx_tendency", "bullish_tendency", "bearish_tendency"),
        # 복합 인덱스: 심볼 + 클러스터링 시점 (최신 클러스터링 결과 조회)
        Index("idx_symbol_clustered_at", "symbol", "clustered_at"),
    )

    def __repr__(self):
        return f"<PatternCluster(id={self.id}, symbol={self.symbol}, cluster_name={self.cluster_name}, pattern_count={self.pattern_count})>"

    def to_dict(self):
        """
        엔티티를 딕셔너리로 변환 (API 응답용)
        """
        return {
            "id": self.id,
            "symbol": self.symbol,
            "cluster_info": {
                "cluster_id": self.cluster_id,
                "cluster_name": self.cluster_name,
                "timeframe": self.timeframe,
                "pattern_count": self.pattern_count,
            },
            "statistics": {
                "avg_success_rate": (
                    float(self.avg_success_rate) if self.avg_success_rate else None
                ),
                "avg_confidence_score": (
                    float(self.avg_confidence_score)
                    if self.avg_confidence_score
                    else None
                ),
                "avg_duration_hours": (
                    float(self.avg_duration_hours) if self.avg_duration_hours else None
                ),
            },
            "tendencies": {
                "bullish_tendency": (
                    float(self.bullish_tendency) if self.bullish_tendency else None
                ),
                "bearish_tendency": (
                    float(self.bearish_tendency) if self.bearish_tendency else None
                ),
                "dominant_signal_types": self.dominant_signal_types,
            },
            "clustering": {
                "algorithm": self.clustering_algorithm,
                "n_clusters_total": self.n_clusters_total,
                "quality_score": (
                    float(self.clustering_quality_score)
                    if self.clustering_quality_score
                    else None
                ),
                "cluster_radius": (
                    float(self.cluster_radius) if self.cluster_radius else None
                ),
            },
            "metadata": {
                "clustered_at": (
                    self.clustered_at.isoformat() if self.clustered_at else None
                ),
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            },
        }

    def get_cluster_center_vector(self) -> list:
        """
        클러스터 중심점을 리스트로 반환

        Returns:
            클러스터 중심점 좌표 리스트
        """
        if not self.cluster_center:
            return []

        try:
            import json

            return json.loads(self.cluster_center)
        except (json.JSONDecodeError, TypeError):
            return []

    def get_representative_pattern_ids(self) -> list:
        """
        대표 패턴 ID들을 리스트로 반환

        Returns:
            대표 패턴 ID 리스트
        """
        if not self.representative_patterns:
            return []

        try:
            import json

            return json.loads(self.representative_patterns)
        except (json.JSONDecodeError, TypeError):
            return []

    def get_dominant_signal_types_list(self) -> list:
        """
        주요 신호 타입들을 리스트로 반환

        Returns:
            주요 신호 타입 리스트
        """
        if not self.dominant_signal_types:
            return []

        try:
            import json

            return json.loads(self.dominant_signal_types)
        except (json.JSONDecodeError, TypeError):
            return []

    def calculate_cluster_strength(self) -> float:
        """
        클러스터의 강도를 계산 (0~100)

        Returns:
            클러스터 강도 점수

        계산 요소:
        - 평균 성공률 (가중치 40%)
        - 평균 신뢰도 점수 (가중치 30%)
        - 패턴 개수 (가중치 20%) - 많을수록 신뢰도 높음
        - 클러스터링 품질 (가중치 10%)
        """
        strength = 0.0

        # 평균 성공률 (40%)
        if self.avg_success_rate:
            strength += float(self.avg_success_rate) * 0.4

        # 평균 신뢰도 점수 (30%)
        if self.avg_confidence_score:
            strength += float(self.avg_confidence_score) * 0.3

        # 패턴 개수 (20%) - 많을수록 신뢰도 높음
        if self.pattern_count:
            pattern_score = min(self.pattern_count / 20, 1.0) * 20  # 최대 20개 기준
            strength += pattern_score

        # 클러스터링 품질 (10%)
        if self.clustering_quality_score:
            strength += float(self.clustering_quality_score) * 0.1

        return min(strength, 100.0)

    def is_bullish_cluster(self, threshold: float = 0.6) -> bool:
        """
        상승 성향 클러스터인지 판단

        Args:
            threshold: 상승 성향 임계값 (기본값: 0.6)

        Returns:
            상승 성향 클러스터 여부
        """
        if not self.bullish_tendency:
            return False

        return float(self.bullish_tendency) >= threshold

    def is_bearish_cluster(self, threshold: float = 0.6) -> bool:
        """
        하락 성향 클러스터인지 판단

        Args:
            threshold: 하락 성향 임계값 (기본값: 0.6)

        Returns:
            하락 성향 클러스터 여부
        """
        if not self.bearish_tendency:
            return False

        return float(self.bearish_tendency) >= threshold

    def get_cluster_type(self) -> str:
        """
        클러스터 타입을 반환

        Returns:
            클러스터 타입 ("bullish", "bearish", "neutral")
        """
        if self.is_bullish_cluster():
            return "bullish"
        elif self.is_bearish_cluster():
            return "bearish"
        else:
            return "neutral"
