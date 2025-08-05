"""
패턴 클러스터링 결과 리포지토리

이 파일은 패턴 클러스터링 결과에 대한 데이터베이스 접근을 담당합니다.

주요 기능:
1. 클러스터링 결과 저장
2. 심볼별 최신 클러스터링 결과 조회
3. 클러스터별 통계 정보 조회
4. 성향별 클러스터 필터링
5. 클러스터링 품질 분석
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_
from app.technical_analysis.infra.model.entity.pattern_clusters import PatternCluster


class PatternClusterRepository:
    """
    패턴 클러스터링 결과 리포지토리

    K-means 클러스터링 결과의 저장, 조회, 분석을 담당합니다.
    """

    def __init__(self, session: Session):
        """
        리포지토리 초기화

        Args:
            session: SQLAlchemy 세션
        """
        self.session = session

    # =================================================================
    # 기본 CRUD 작업
    # =================================================================

    def save(self, cluster: PatternCluster) -> PatternCluster:
        """
        클러스터링 결과 저장

        Args:
            cluster: 저장할 클러스터 엔티티

        Returns:
            저장된 클러스터 엔티티
        """
        self.session.add(cluster)
        self.session.commit()
        self.session.refresh(cluster)
        return cluster

    def save_all(self, clusters: List[PatternCluster]) -> List[PatternCluster]:
        """
        여러 클러스터링 결과를 배치로 저장

        Args:
            clusters: 저장할 클러스터 엔티티 리스트

        Returns:
            저장된 클러스터 엔티티 리스트
        """
        self.session.add_all(clusters)
        self.session.commit()
        for cluster in clusters:
            self.session.refresh(cluster)
        return clusters

    def find_by_id(self, cluster_id: int) -> Optional[PatternCluster]:
        """
        ID로 클러스터 조회

        Args:
            cluster_id: 클러스터 ID

        Returns:
            클러스터 엔티티 또는 None
        """
        return (
            self.session.query(PatternCluster)
            .filter(PatternCluster.id == cluster_id)
            .first()
        )

    def delete_by_id(self, cluster_id: int) -> bool:
        """
        ID로 클러스터 삭제

        Args:
            cluster_id: 삭제할 클러스터 ID

        Returns:
            삭제 성공 여부
        """
        cluster = self.find_by_id(cluster_id)
        if cluster:
            self.session.delete(cluster)
            self.session.commit()
            return True
        return False

    # =================================================================
    # 심볼별 조회
    # =================================================================

    def find_latest_by_symbol(
        self, symbol: str, timeframe: str = "1day"
    ) -> List[PatternCluster]:
        """
        심볼의 최신 클러스터링 결과 조회

        Args:
            symbol: 심볼 (예: ^IXIC, ^GSPC)
            timeframe: 시간대 (기본값: 1day)

        Returns:
            최신 클러스터링 결과 리스트
        """
        # 해당 심볼의 가장 최근 클러스터링 시점 찾기
        latest_clustered_at = (
            self.session.query(func.max(PatternCluster.clustered_at))
            .filter(
                and_(
                    PatternCluster.symbol == symbol,
                    PatternCluster.timeframe == timeframe,
                )
            )
            .scalar()
        )

        if not latest_clustered_at:
            return []

        # 해당 시점의 모든 클러스터 조회
        return (
            self.session.query(PatternCluster)
            .filter(
                and_(
                    PatternCluster.symbol == symbol,
                    PatternCluster.timeframe == timeframe,
                    PatternCluster.clustered_at == latest_clustered_at,
                )
            )
            .order_by(PatternCluster.cluster_id)
            .all()
        )

    def find_by_symbol_and_date_range(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1day",
    ) -> List[PatternCluster]:
        """
        심볼의 특정 기간 클러스터링 결과 조회

        Args:
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜
            timeframe: 시간대

        Returns:
            해당 기간의 클러스터링 결과 리스트
        """
        return (
            self.session.query(PatternCluster)
            .filter(
                and_(
                    PatternCluster.symbol == symbol,
                    PatternCluster.timeframe == timeframe,
                    PatternCluster.clustered_at >= start_date,
                    PatternCluster.clustered_at <= end_date,
                )
            )
            .order_by(PatternCluster.clustered_at.desc(), PatternCluster.cluster_id)
            .all()
        )

    # =================================================================
    # 클러스터 특성별 조회
    # =================================================================

    def find_bullish_clusters(
        self, symbol: str, threshold: float = 0.6, timeframe: str = "1day"
    ) -> List[PatternCluster]:
        """
        상승 성향 클러스터들 조회

        Args:
            symbol: 심볼
            threshold: 상승 성향 임계값 (기본값: 0.6)
            timeframe: 시간대

        Returns:
            상승 성향 클러스터 리스트
        """
        latest_clusters = self.find_latest_by_symbol(symbol, timeframe)
        return [
            cluster
            for cluster in latest_clusters
            if cluster.bullish_tendency and float(cluster.bullish_tendency) >= threshold
        ]

    def find_bearish_clusters(
        self, symbol: str, threshold: float = 0.6, timeframe: str = "1day"
    ) -> List[PatternCluster]:
        """
        하락 성향 클러스터들 조회

        Args:
            symbol: 심볼
            threshold: 하락 성향 임계값 (기본값: 0.6)
            timeframe: 시간대

        Returns:
            하락 성향 클러스터 리스트
        """
        latest_clusters = self.find_latest_by_symbol(symbol, timeframe)
        return [
            cluster
            for cluster in latest_clusters
            if cluster.bearish_tendency and float(cluster.bearish_tendency) >= threshold
        ]

    def find_high_performance_clusters(
        self, symbol: str, min_success_rate: float = 70.0, timeframe: str = "1day"
    ) -> List[PatternCluster]:
        """
        고성과 클러스터들 조회

        Args:
            symbol: 심볼
            min_success_rate: 최소 성공률 (기본값: 70%)
            timeframe: 시간대

        Returns:
            고성과 클러스터 리스트
        """
        latest_clusters = self.find_latest_by_symbol(symbol, timeframe)
        return [
            cluster
            for cluster in latest_clusters
            if cluster.avg_success_rate
            and float(cluster.avg_success_rate) >= min_success_rate
        ]

    # =================================================================
    # 통계 및 분석
    # =================================================================

    def get_clustering_summary(
        self, symbol: str, timeframe: str = "1day"
    ) -> Dict[str, Any]:
        """
        심볼의 클러스터링 요약 정보 조회

        Args:
            symbol: 심볼
            timeframe: 시간대

        Returns:
            클러스터링 요약 정보
        """
        latest_clusters = self.find_latest_by_symbol(symbol, timeframe)

        if not latest_clusters:
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "total_clusters": 0,
                "total_patterns": 0,
                "error": "클러스터링 결과가 없습니다",
            }

        # 통계 계산
        total_patterns = sum(cluster.pattern_count for cluster in latest_clusters)
        bullish_clusters = len([c for c in latest_clusters if c.is_bullish_cluster()])
        bearish_clusters = len([c for c in latest_clusters if c.is_bearish_cluster()])
        neutral_clusters = len(latest_clusters) - bullish_clusters - bearish_clusters

        # 평균 성과 계산
        success_rates = [
            float(c.avg_success_rate) for c in latest_clusters if c.avg_success_rate
        ]
        avg_success_rate = (
            sum(success_rates) / len(success_rates) if success_rates else 0
        )

        # 최고 성과 클러스터
        best_cluster = max(
            latest_clusters,
            key=lambda c: float(c.avg_success_rate) if c.avg_success_rate else 0,
        )

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "clustering_info": {
                "total_clusters": len(latest_clusters),
                "total_patterns": total_patterns,
                "clustered_at": (
                    latest_clusters[0].clustered_at.isoformat()
                    if latest_clusters
                    else None
                ),
            },
            "cluster_distribution": {
                "bullish_clusters": bullish_clusters,
                "bearish_clusters": bearish_clusters,
                "neutral_clusters": neutral_clusters,
            },
            "performance": {
                "avg_success_rate": round(avg_success_rate, 2),
                "best_cluster": {
                    "name": best_cluster.cluster_name,
                    "success_rate": (
                        float(best_cluster.avg_success_rate)
                        if best_cluster.avg_success_rate
                        else 0
                    ),
                    "pattern_count": best_cluster.pattern_count,
                },
            },
        }

    def get_cluster_performance_comparison(
        self, symbol: str, timeframe: str = "1day"
    ) -> List[Dict[str, Any]]:
        """
        클러스터별 성과 비교 정보

        Args:
            symbol: 심볼
            timeframe: 시간대

        Returns:
            클러스터별 성과 비교 리스트
        """
        latest_clusters = self.find_latest_by_symbol(symbol, timeframe)

        comparison = []
        for cluster in latest_clusters:
            comparison.append(
                {
                    "cluster_id": cluster.cluster_id,
                    "cluster_name": cluster.cluster_name,
                    "pattern_count": cluster.pattern_count,
                    "avg_success_rate": (
                        float(cluster.avg_success_rate)
                        if cluster.avg_success_rate
                        else 0
                    ),
                    "avg_confidence_score": (
                        float(cluster.avg_confidence_score)
                        if cluster.avg_confidence_score
                        else 0
                    ),
                    "cluster_type": cluster.get_cluster_type(),
                    "cluster_strength": cluster.calculate_cluster_strength(),
                    "dominant_signals": cluster.get_dominant_signal_types_list(),
                }
            )

        # 성과순으로 정렬
        comparison.sort(key=lambda x: x["avg_success_rate"], reverse=True)
        return comparison

    # =================================================================
    # 데이터 관리
    # =================================================================

    def delete_old_clustering_results(
        self, symbol: str, keep_days: int = 30, timeframe: str = "1day"
    ) -> int:
        """
        오래된 클러스터링 결과 삭제

        Args:
            symbol: 심볼
            keep_days: 보관할 일수 (기본값: 30일)
            timeframe: 시간대

        Returns:
            삭제된 레코드 수
        """
        cutoff_date = datetime.utcnow() - timedelta(days=keep_days)

        deleted_count = (
            self.session.query(PatternCluster)
            .filter(
                and_(
                    PatternCluster.symbol == symbol,
                    PatternCluster.timeframe == timeframe,
                    PatternCluster.clustered_at < cutoff_date,
                )
            )
            .delete()
        )

        self.session.commit()
        return deleted_count

    def count_by_symbol(self, symbol: str, timeframe: str = "1day") -> int:
        """
        심볼별 클러스터링 결과 개수 조회

        Args:
            symbol: 심볼
            timeframe: 시간대

        Returns:
            클러스터링 결과 개수
        """
        return (
            self.session.query(PatternCluster)
            .filter(
                and_(
                    PatternCluster.symbol == symbol,
                    PatternCluster.timeframe == timeframe,
                )
            )
            .count()
        )

    def get_clustering_history(
        self, symbol: str, limit: int = 10, timeframe: str = "1day"
    ) -> List[Dict[str, Any]]:
        """
        클러스터링 실행 이력 조회

        Args:
            symbol: 심볼
            limit: 조회할 개수 (기본값: 10)
            timeframe: 시간대

        Returns:
            클러스터링 실행 이력 리스트
        """
        # 클러스터링 시점별로 그룹화하여 조회
        clustering_dates = (
            self.session.query(PatternCluster.clustered_at)
            .filter(
                and_(
                    PatternCluster.symbol == symbol,
                    PatternCluster.timeframe == timeframe,
                )
            )
            .distinct()
            .order_by(PatternCluster.clustered_at.desc())
            .limit(limit)
            .all()
        )

        history = []
        for (clustered_at,) in clustering_dates:
            # 해당 시점의 클러스터링 결과 요약
            clusters = (
                self.session.query(PatternCluster)
                .filter(
                    and_(
                        PatternCluster.symbol == symbol,
                        PatternCluster.timeframe == timeframe,
                        PatternCluster.clustered_at == clustered_at,
                    )
                )
                .all()
            )

            total_patterns = sum(c.pattern_count for c in clusters)
            avg_quality = (
                sum(
                    float(c.clustering_quality_score)
                    for c in clusters
                    if c.clustering_quality_score
                )
                / len(clusters)
                if clusters
                else 0
            )

            history.append(
                {
                    "clustered_at": clustered_at.isoformat(),
                    "n_clusters": len(clusters),
                    "total_patterns": total_patterns,
                    "avg_quality_score": round(avg_quality, 2),
                }
            )

        return history

    def get_latest_clusters_by_symbol(
        self, symbol: str, timeframe: str = "1day"
    ) -> List[PatternCluster]:
        """
        심볼별 최신 클러스터링 결과 조회

        Args:
            symbol: 조회할 심볼
            timeframe: 시간대 (기본값: "1day")

        Returns:
            최신 클러스터링 결과 리스트
        """
        # 최신 클러스터링 시점 조회
        latest_clustered_at = (
            self.session.query(func.max(PatternCluster.clustered_at))
            .filter(
                and_(
                    PatternCluster.symbol == symbol,
                    PatternCluster.timeframe == timeframe,
                )
            )
            .scalar()
        )

        if not latest_clustered_at:
            return []

        # 최신 시점의 모든 클러스터 조회
        return (
            self.session.query(PatternCluster)
            .filter(
                and_(
                    PatternCluster.symbol == symbol,
                    PatternCluster.timeframe == timeframe,
                    PatternCluster.clustered_at == latest_clustered_at,
                )
            )
            .order_by(PatternCluster.cluster_id)
            .all()
        )
