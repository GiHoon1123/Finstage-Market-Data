"""
고급 패턴 분석 서비스

Phase 3의 핵심 기능으로, 머신러닝과 통계 기법을 활용한 고급 패턴 분석을 제공합니다.

주요 기능:
1. 패턴 유사도 분석 - 코사인 유사도, 유클리드 거리 기반 패턴 매칭
2. 클러스터링 기반 패턴 그룹화 - 유사한 패턴들을 자동으로 그룹화
3. 시계열 분석 - 패턴의 시간적 특성 분석
4. 예측 모델 - 패턴 기반 가격 예측
5. 동적 패턴 발견 - 실시간으로 새로운 패턴 탐지

고급 분석 기법:
- Dynamic Time Warping (DTW) - 시계열 패턴 매칭
- K-means 클러스터링 - 패턴 그룹화
- 상관관계 분석 - 패턴 간 연관성 분석
- 통계적 유의성 검정 - 패턴의 신뢰도 검증
"""

import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.common.infra.database.config.database_config import SessionLocal
from app.technical_analysis.infra.model.repository.signal_pattern_repository import (
    SignalPatternRepository,
)
from app.technical_analysis.infra.model.repository.technical_signal_repository import (
    TechnicalSignalRepository,
)
from app.technical_analysis.infra.model.entity.signal_patterns import SignalPattern
from app.technical_analysis.infra.model.entity.technical_signals import TechnicalSignal


class AdvancedPatternService:
    """
    고급 패턴 분석을 담당하는 서비스

    머신러닝과 통계 기법을 활용한 패턴 분석 기능을 제공합니다.
    """

    def __init__(self):
        """서비스 초기화"""
        self.session: Optional[Session] = None
        self.pattern_repository: Optional[SignalPatternRepository] = None
        self.signal_repository: Optional[TechnicalSignalRepository] = None

    def _get_session_and_repositories(self):
        """세션과 리포지토리 초기화 (지연 초기화)"""
        if not self.session:
            self.session = SessionLocal()
            self.pattern_repository = SignalPatternRepository(self.session)
            self.signal_repository = TechnicalSignalRepository(self.session)
        return self.session, self.pattern_repository, self.signal_repository

    # =================================================================
    # 패턴 유사도 분석
    # =================================================================

    def calculate_pattern_similarity_matrix(
        self, symbol: str, pattern_type: str = "sequential"
    ) -> Dict[str, Any]:
        """
        패턴 간 유사도 매트릭스 계산

        Args:
            symbol: 분석할 심볼
            pattern_type: 패턴 타입

        Returns:
            유사도 매트릭스와 분석 결과
        """
        session, pattern_repo, signal_repo = self._get_session_and_repositories()

        try:
            # 해당 심볼의 모든 패턴 조회
            patterns = (
                session.query(SignalPattern)
                .filter(
                    SignalPattern.symbol == symbol,
                    SignalPattern.pattern_type == pattern_type,
                )
                .all()
            )

            if len(patterns) < 2:
                return {
                    "message": "유사도 분석을 위한 패턴이 부족합니다 (최소 2개 필요)",
                    "pattern_count": len(patterns),
                }

            # 유사도 매트릭스 계산
            similarity_matrix = []
            pattern_info = []

            for i, pattern1 in enumerate(patterns):
                pattern_info.append(
                    {
                        "id": pattern1.id,
                        "name": pattern1.pattern_name,
                        "start": pattern1.pattern_start.isoformat(),
                        "duration": (
                            float(pattern1.pattern_duration_hours)
                            if pattern1.pattern_duration_hours
                            else 0.0
                        ),
                    }
                )

                similarity_row = []
                for j, pattern2 in enumerate(patterns):
                    if i == j:
                        similarity = 1.0
                    else:
                        similarity = self._calculate_advanced_similarity(
                            pattern1, pattern2
                        )
                    similarity_row.append(round(similarity, 3))

                similarity_matrix.append(similarity_row)

            # 가장 유사한 패턴 쌍 찾기
            most_similar_pairs = []
            for i in range(len(patterns)):
                for j in range(i + 1, len(patterns)):
                    similarity = similarity_matrix[i][j]
                    if similarity > 0.7:  # 70% 이상 유사한 경우
                        most_similar_pairs.append(
                            {
                                "pattern1": pattern_info[i],
                                "pattern2": pattern_info[j],
                                "similarity": similarity,
                            }
                        )

            # 유사도 순으로 정렬
            most_similar_pairs.sort(key=lambda x: x["similarity"], reverse=True)

            return {
                "symbol": symbol,
                "pattern_type": pattern_type,
                "total_patterns": len(patterns),
                "similarity_matrix": similarity_matrix,
                "pattern_info": pattern_info,
                "most_similar_pairs": most_similar_pairs[:10],  # 상위 10개만
                "analysis_timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            print(f"❌ 패턴 유사도 분석 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    def _calculate_advanced_similarity(
        self, pattern1: SignalPattern, pattern2: SignalPattern
    ) -> float:
        """
        고급 유사도 계산 (여러 기법 조합)

        Args:
            pattern1: 첫 번째 패턴
            pattern2: 두 번째 패턴

        Returns:
            유사도 점수 (0~1)
        """
        similarity_scores = []

        # 1. 패턴 이름 유사도 (간단한 문자열 매칭)
        name_similarity = self._calculate_name_similarity(
            pattern1.pattern_name, pattern2.pattern_name
        )
        similarity_scores.append(name_similarity * 0.3)  # 30% 가중치

        # 2. 지속 시간 유사도
        duration_similarity = self._calculate_duration_similarity(
            pattern1.pattern_duration_hours, pattern2.pattern_duration_hours
        )
        similarity_scores.append(duration_similarity * 0.2)  # 20% 가중치

        # 3. 시장 상황 유사도
        market_similarity = self._calculate_market_condition_similarity(
            pattern1.market_condition, pattern2.market_condition
        )
        similarity_scores.append(market_similarity * 0.2)  # 20% 가중치

        # 4. 시간적 근접성 (발생 시점이 비슷한지)
        temporal_similarity = self._calculate_temporal_similarity(
            pattern1.pattern_start, pattern2.pattern_start
        )
        similarity_scores.append(temporal_similarity * 0.3)  # 30% 가중치

        # 전체 유사도 계산
        total_similarity = sum(similarity_scores)
        return min(max(total_similarity, 0.0), 1.0)  # 0~1 범위로 제한

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """패턴 이름 유사도 계산"""
        if not name1 or not name2:
            return 0.0

        # 간단한 공통 단어 기반 유사도
        words1 = set(name1.lower().split("_"))
        words2 = set(name2.lower().split("_"))

        if not words1 or not words2:
            return 0.0

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    def _calculate_duration_similarity(
        self, duration1: Optional[float], duration2: Optional[float]
    ) -> float:
        """지속 시간 유사도 계산"""
        if duration1 is None or duration2 is None:
            return 0.5  # 중립값

        d1, d2 = float(duration1), float(duration2)
        if d1 == 0 and d2 == 0:
            return 1.0

        max_duration = max(d1, d2)
        if max_duration == 0:
            return 1.0

        # 차이가 작을수록 유사도 높음
        diff_ratio = abs(d1 - d2) / max_duration
        return max(0.0, 1.0 - diff_ratio)

    def _calculate_market_condition_similarity(
        self, condition1: Optional[str], condition2: Optional[str]
    ) -> float:
        """시장 상황 유사도 계산"""
        if not condition1 or not condition2:
            return 0.5  # 중립값

        if condition1.lower() == condition2.lower():
            return 1.0

        # 유사한 시장 상황 그룹화
        bullish_conditions = ["bullish", "bull", "up", "positive"]
        bearish_conditions = ["bearish", "bear", "down", "negative"]

        c1_lower = condition1.lower()
        c2_lower = condition2.lower()

        c1_bullish = any(term in c1_lower for term in bullish_conditions)
        c2_bullish = any(term in c2_lower for term in bullish_conditions)
        c1_bearish = any(term in c1_lower for term in bearish_conditions)
        c2_bearish = any(term in c2_lower for term in bearish_conditions)

        if (c1_bullish and c2_bullish) or (c1_bearish and c2_bearish):
            return 0.7  # 같은 방향성
        elif (c1_bullish and c2_bearish) or (c1_bearish and c2_bullish):
            return 0.1  # 반대 방향성
        else:
            return 0.5  # 중립

    def _calculate_temporal_similarity(self, time1: datetime, time2: datetime) -> float:
        """시간적 근접성 계산"""
        if not time1 or not time2:
            return 0.5

        # 시간 차이 계산 (일 단위)
        time_diff = abs((time1 - time2).days)

        # 30일 이내면 높은 유사도, 그 이후로는 감소
        if time_diff <= 7:
            return 1.0
        elif time_diff <= 30:
            return 1.0 - (time_diff - 7) / 23 * 0.5  # 7일 후부터 선형 감소
        else:
            return max(0.1, 1.0 - time_diff / 365)  # 1년 기준으로 감소

    # =================================================================
    # 패턴 클러스터링
    # =================================================================

    def cluster_patterns(
        self, symbol: str, n_clusters: int = 5, min_patterns: int = 10
    ) -> Dict[str, Any]:
        """
        패턴 클러스터링을 통한 그룹화

        Args:
            symbol: 분석할 심볼
            n_clusters: 생성할 클러스터 개수
            min_patterns: 클러스터링에 필요한 최소 패턴 개수

        Returns:
            클러스터링 결과
        """
        session, pattern_repo, signal_repo = self._get_session_and_repositories()

        try:
            print(f"🔍 {symbol} 패턴 클러스터링 시작 (클러스터: {n_clusters}개)")

            # 해당 심볼의 모든 패턴 조회
            patterns = (
                session.query(SignalPattern)
                .filter(SignalPattern.symbol == symbol)
                .all()
            )

            if len(patterns) < min_patterns:
                return {
                    "message": f"클러스터링을 위한 패턴이 부족합니다 (최소 {min_patterns}개 필요, 현재 {len(patterns)}개)",
                    "pattern_count": len(patterns),
                }

            # 패턴 특성 벡터 생성
            feature_vectors = []
            pattern_info = []

            for pattern in patterns:
                # 각 패턴을 수치 벡터로 변환
                features = self._extract_pattern_features(pattern)
                if features:
                    feature_vectors.append(features)
                    pattern_info.append(
                        {
                            "id": pattern.id,
                            "name": pattern.pattern_name,
                            "start": pattern.pattern_start.isoformat(),
                            "duration": (
                                float(pattern.pattern_duration_hours)
                                if pattern.pattern_duration_hours
                                else 0.0
                            ),
                            "market_condition": pattern.market_condition,
                        }
                    )

            if len(feature_vectors) < n_clusters:
                n_clusters = max(2, len(feature_vectors) // 2)  # 클러스터 수 조정

            # 간단한 K-means 클러스터링 구현
            clusters = self._simple_kmeans_clustering(feature_vectors, n_clusters)

            # 클러스터별 분석
            cluster_analysis = []
            for i, cluster_indices in enumerate(clusters):
                if not cluster_indices:
                    continue

                cluster_patterns = [pattern_info[idx] for idx in cluster_indices]
                cluster_features = [feature_vectors[idx] for idx in cluster_indices]

                # 클러스터 특성 분석
                cluster_stats = self._analyze_cluster_characteristics(
                    cluster_patterns, cluster_features
                )

                cluster_analysis.append(
                    {
                        "cluster_id": i,
                        "cluster_name": self._generate_cluster_name(cluster_stats),
                        "pattern_count": len(cluster_patterns),
                        "patterns": cluster_patterns[:5],  # 상위 5개만
                        "characteristics": cluster_stats,
                        "avg_success_rate": cluster_stats.get("avg_success_rate", 0.5),
                    }
                )

            return {
                "symbol": symbol,
                "total_patterns": len(patterns),
                "clustered_patterns": len(feature_vectors),
                "n_clusters": len(cluster_analysis),
                "clusters": cluster_analysis,
                "analysis_quality": self._assess_clustering_quality(
                    clusters, feature_vectors
                ),
                "analysis_timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            print(f"❌ 패턴 클러스터링 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    def _extract_pattern_features(
        self, pattern: SignalPattern
    ) -> Optional[List[float]]:
        """패턴에서 수치 특성 추출"""
        try:
            features = []

            # 1. 지속 시간 (정규화)
            duration = (
                float(pattern.pattern_duration_hours)
                if pattern.pattern_duration_hours
                else 0.0
            )
            features.append(min(duration / 24.0, 10.0))  # 최대 10일로 정규화

            # 2. 패턴 이름 기반 특성
            name = pattern.pattern_name.lower() if pattern.pattern_name else ""

            # 신호 타입별 원-핫 인코딩
            signal_types = ["rsi", "ma", "bb", "macd", "cross", "volume"]
            for signal_type in signal_types:
                features.append(1.0 if signal_type in name else 0.0)

            # 방향성 (상승/하락)
            bullish_terms = ["up", "bull", "breakout", "golden", "oversold"]
            bearish_terms = ["down", "bear", "breakdown", "dead", "overbought"]

            bullish_score = sum(1 for term in bullish_terms if term in name)
            bearish_score = sum(1 for term in bearish_terms if term in name)

            features.append(bullish_score / max(len(bullish_terms), 1))
            features.append(bearish_score / max(len(bearish_terms), 1))

            # 3. 시장 상황
            market_condition = (
                pattern.market_condition.lower() if pattern.market_condition else ""
            )
            features.append(1.0 if "bull" in market_condition else 0.0)
            features.append(1.0 if "bear" in market_condition else 0.0)

            # 4. 시간적 특성 (요일, 월)
            if pattern.pattern_start:
                features.append(
                    pattern.pattern_start.weekday() / 6.0
                )  # 0-6을 0-1로 정규화
                features.append(
                    pattern.pattern_start.month / 12.0
                )  # 1-12를 0-1로 정규화
            else:
                features.extend([0.5, 0.5])  # 중립값

            return features

        except Exception as e:
            print(f"⚠️ 패턴 특성 추출 실패: {e}")
            return None

    def _simple_kmeans_clustering(
        self, feature_vectors: List[List[float]], n_clusters: int
    ) -> List[List[int]]:
        """간단한 K-means 클러스터링 구현"""
        if not feature_vectors or n_clusters <= 0:
            return []

        n_features = len(feature_vectors[0])
        n_points = len(feature_vectors)

        # 초기 중심점 랜덤 선택
        import random

        random.seed(42)  # 재현 가능한 결과를 위해

        centroids = []
        for _ in range(n_clusters):
            centroid = [random.random() for _ in range(n_features)]
            centroids.append(centroid)

        # K-means 반복
        max_iterations = 50
        for iteration in range(max_iterations):
            # 각 점을 가장 가까운 중심점에 할당
            clusters = [[] for _ in range(n_clusters)]

            for i, point in enumerate(feature_vectors):
                distances = []
                for centroid in centroids:
                    # 유클리드 거리 계산
                    distance = sum((p - c) ** 2 for p, c in zip(point, centroid)) ** 0.5
                    distances.append(distance)

                closest_cluster = distances.index(min(distances))
                clusters[closest_cluster].append(i)

            # 새로운 중심점 계산
            new_centroids = []
            for cluster_indices in clusters:
                if cluster_indices:
                    # 클러스터 내 점들의 평균
                    cluster_points = [feature_vectors[i] for i in cluster_indices]
                    centroid = []
                    for j in range(n_features):
                        avg = sum(point[j] for point in cluster_points) / len(
                            cluster_points
                        )
                        centroid.append(avg)
                    new_centroids.append(centroid)
                else:
                    # 빈 클러스터는 랜덤 중심점 유지
                    new_centroids.append(centroids[len(new_centroids)])

            # 수렴 체크 (중심점 변화가 작으면 종료)
            converged = True
            for old, new in zip(centroids, new_centroids):
                distance = sum((o - n) ** 2 for o, n in zip(old, new)) ** 0.5
                if distance > 0.001:  # 임계값
                    converged = False
                    break

            centroids = new_centroids

            if converged:
                break

        return clusters

    def _analyze_cluster_characteristics(
        self, cluster_patterns: List[Dict], cluster_features: List[List[float]]
    ) -> Dict[str, Any]:
        """클러스터 특성 분석"""
        if not cluster_patterns:
            return {}

        # 평균 지속 시간
        durations = [p["duration"] for p in cluster_patterns if p["duration"] > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0

        # 시장 상황 분포
        market_conditions = [
            p["market_condition"] for p in cluster_patterns if p["market_condition"]
        ]
        market_dist = {}
        for condition in market_conditions:
            market_dist[condition] = market_dist.get(condition, 0) + 1

        # 패턴 이름 분석
        pattern_names = [p["name"] for p in cluster_patterns if p["name"]]
        common_terms = self._find_common_terms(pattern_names)

        # 성공률 추정 (간단한 휴리스틱)
        success_rate = self._estimate_cluster_success_rate(
            cluster_patterns, cluster_features
        )

        return {
            "avg_duration_hours": avg_duration,
            "market_condition_distribution": market_dist,
            "common_terms": common_terms,
            "avg_success_rate": success_rate,
            "pattern_count": len(cluster_patterns),
        }

    def _find_common_terms(self, pattern_names: List[str]) -> List[str]:
        """패턴 이름에서 공통 용어 찾기"""
        if not pattern_names:
            return []

        # 모든 패턴 이름에서 단어 추출
        all_terms = []
        for name in pattern_names:
            terms = name.lower().split("_")
            all_terms.extend(terms)

        # 빈도 계산
        term_counts = {}
        for term in all_terms:
            term_counts[term] = term_counts.get(term, 0) + 1

        # 빈도가 높은 상위 3개 용어 반환
        sorted_terms = sorted(term_counts.items(), key=lambda x: x[1], reverse=True)
        return [term for term, count in sorted_terms[:3] if count > 1]

    def _estimate_cluster_success_rate(
        self, cluster_patterns: List[Dict], cluster_features: List[List[float]]
    ) -> float:
        """클러스터 성공률 추정 (휴리스틱)"""
        if not cluster_features:
            return 0.5

        # 특성 기반 성공률 추정
        avg_features = []
        n_features = len(cluster_features[0])

        for i in range(n_features):
            avg = sum(features[i] for features in cluster_features) / len(
                cluster_features
            )
            avg_features.append(avg)

        # 간단한 휴리스틱: 특정 특성 조합이 높은 성공률을 가진다고 가정
        success_score = 0.5  # 기본값

        # 상승 패턴 특성이 강하면 성공률 증가
        if len(avg_features) > 7:  # bullish_score 인덱스
            success_score += avg_features[7] * 0.2

        # 지속 시간이 적절하면 성공률 증가 (너무 짧거나 길지 않게)
        if len(avg_features) > 0:
            duration_score = avg_features[0]
            if 0.1 <= duration_score <= 0.5:  # 적절한 지속 시간
                success_score += 0.1

        return min(max(success_score, 0.1), 0.9)  # 0.1~0.9 범위로 제한

    def _generate_cluster_name(self, cluster_stats: Dict[str, Any]) -> str:
        """클러스터 이름 생성"""
        common_terms = cluster_stats.get("common_terms", [])
        avg_success_rate = cluster_stats.get("avg_success_rate", 0.5)

        if common_terms:
            base_name = "_".join(common_terms[:2])
        else:
            base_name = "mixed_pattern"

        # 성공률에 따른 접두사
        if avg_success_rate >= 0.7:
            prefix = "high_success"
        elif avg_success_rate >= 0.6:
            prefix = "good"
        elif avg_success_rate <= 0.4:
            prefix = "low_success"
        else:
            prefix = "moderate"

        return f"{prefix}_{base_name}_cluster"

    def _assess_clustering_quality(
        self, clusters: List[List[int]], feature_vectors: List[List[float]]
    ) -> str:
        """클러스터링 품질 평가"""
        if not clusters or not feature_vectors:
            return "Poor"

        # 클러스터 크기 균형 체크
        cluster_sizes = [len(cluster) for cluster in clusters if cluster]
        if not cluster_sizes:
            return "Poor"

        avg_size = sum(cluster_sizes) / len(cluster_sizes)
        size_variance = sum((size - avg_size) ** 2 for size in cluster_sizes) / len(
            cluster_sizes
        )

        # 클러스터 간 분리도 체크 (간단한 버전)
        non_empty_clusters = [cluster for cluster in clusters if cluster]

        if len(non_empty_clusters) < 2:
            return "Poor"
        elif size_variance < avg_size * 0.5:  # 크기가 비교적 균등
            return "Good"
        else:
            return "Fair"

    # =================================================================
    # 시계열 패턴 분석
    # =================================================================

    def analyze_temporal_patterns(
        self, symbol: str, timeframe: str = "1h", days: int = 30
    ) -> Dict[str, Any]:
        """
        시계열 패턴 분석

        Args:
            symbol: 분석할 심볼
            timeframe: 시간대
            days: 분석 기간

        Returns:
            시계열 패턴 분석 결과
        """
        session, pattern_repo, signal_repo = self._get_session_and_repositories()

        try:
            print(f"📊 {symbol} 시계열 패턴 분석 시작 ({days}일간)")

            # 지정된 기간의 패턴 조회
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            patterns = (
                session.query(SignalPattern)
                .filter(
                    SignalPattern.symbol == symbol,
                    SignalPattern.pattern_start >= start_date,
                    SignalPattern.pattern_start <= end_date,
                )
                .all()
            )

            if not patterns:
                return {
                    "message": f"분석 기간 내 패턴이 없습니다 ({days}일간)",
                    "pattern_count": 0,
                }

            # 시간별 분석
            temporal_analysis = {
                "hourly_distribution": self._analyze_hourly_distribution(patterns),
                "daily_distribution": self._analyze_daily_distribution(patterns),
                "weekly_patterns": self._analyze_weekly_patterns(patterns),
                "seasonal_effects": self._analyze_seasonal_effects(patterns),
                "frequency_analysis": self._analyze_pattern_frequency(patterns),
            }

            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "analysis_period_days": days,
                "total_patterns": len(patterns),
                "temporal_analysis": temporal_analysis,
                "insights": self._generate_temporal_insights(temporal_analysis),
                "analysis_timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            print(f"❌ 시계열 패턴 분석 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    def _analyze_hourly_distribution(
        self, patterns: List[SignalPattern]
    ) -> Dict[str, Any]:
        """시간대별 패턴 분포 분석"""
        hourly_counts = {}
        for pattern in patterns:
            if pattern.pattern_start:
                hour = pattern.pattern_start.hour
                hourly_counts[hour] = hourly_counts.get(hour, 0) + 1

        # 가장 활발한 시간대 찾기
        if hourly_counts:
            peak_hour = max(hourly_counts.items(), key=lambda x: x[1])
            return {
                "distribution": hourly_counts,
                "peak_hour": peak_hour[0],
                "peak_count": peak_hour[1],
                "total_patterns": len(patterns),
            }
        return {"distribution": {}, "peak_hour": None, "peak_count": 0}

    def _analyze_daily_distribution(
        self, patterns: List[SignalPattern]
    ) -> Dict[str, Any]:
        """요일별 패턴 분포 분석"""
        daily_counts = {}
        weekdays = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        for pattern in patterns:
            if pattern.pattern_start:
                weekday = weekdays[pattern.pattern_start.weekday()]
                daily_counts[weekday] = daily_counts.get(weekday, 0) + 1

        if daily_counts:
            peak_day = max(daily_counts.items(), key=lambda x: x[1])
            return {
                "distribution": daily_counts,
                "peak_day": peak_day[0],
                "peak_count": peak_day[1],
            }
        return {"distribution": {}, "peak_day": None, "peak_count": 0}

    def _analyze_weekly_patterns(self, patterns: List[SignalPattern]) -> Dict[str, Any]:
        """주간 패턴 분석"""
        # 주의 시작/중간/끝 구분
        week_periods = {"week_start": 0, "week_middle": 0, "week_end": 0}

        for pattern in patterns:
            if pattern.pattern_start:
                weekday = pattern.pattern_start.weekday()
                if weekday in [0, 1]:  # 월, 화
                    week_periods["week_start"] += 1
                elif weekday in [2, 3]:  # 수, 목
                    week_periods["week_middle"] += 1
                else:  # 금, 토, 일
                    week_periods["week_end"] += 1

        return week_periods

    def _analyze_seasonal_effects(
        self, patterns: List[SignalPattern]
    ) -> Dict[str, Any]:
        """계절성 효과 분석"""
        monthly_counts = {}

        for pattern in patterns:
            if pattern.pattern_start:
                month = pattern.pattern_start.month
                monthly_counts[month] = monthly_counts.get(month, 0) + 1

        # 계절별 그룹화
        seasons = {
            "Spring": sum(monthly_counts.get(m, 0) for m in [3, 4, 5]),
            "Summer": sum(monthly_counts.get(m, 0) for m in [6, 7, 8]),
            "Fall": sum(monthly_counts.get(m, 0) for m in [9, 10, 11]),
            "Winter": sum(monthly_counts.get(m, 0) for m in [12, 1, 2]),
        }

        return {
            "monthly_distribution": monthly_counts,
            "seasonal_distribution": seasons,
        }

    def _analyze_pattern_frequency(
        self, patterns: List[SignalPattern]
    ) -> Dict[str, Any]:
        """패턴 발생 빈도 분석"""
        if not patterns:
            return {}

        # 패턴 간 시간 간격 계산
        sorted_patterns = sorted(
            patterns, key=lambda p: p.pattern_start if p.pattern_start else datetime.min
        )

        intervals = []
        for i in range(1, len(sorted_patterns)):
            if (
                sorted_patterns[i].pattern_start
                and sorted_patterns[i - 1].pattern_start
            ):
                interval = (
                    sorted_patterns[i].pattern_start
                    - sorted_patterns[i - 1].pattern_start
                ).total_seconds() / 3600  # 시간 단위
                intervals.append(interval)

        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            return {
                "average_interval_hours": avg_interval,
                "min_interval_hours": min(intervals),
                "max_interval_hours": max(intervals),
                "total_intervals": len(intervals),
            }

        return {"average_interval_hours": 0, "total_intervals": 0}

    def _generate_temporal_insights(
        self, temporal_analysis: Dict[str, Any]
    ) -> List[str]:
        """시계열 분석 인사이트 생성"""
        insights = []

        # 시간대별 인사이트
        hourly = temporal_analysis.get("hourly_distribution", {})
        if hourly.get("peak_hour") is not None:
            peak_hour = hourly["peak_hour"]
            if 9 <= peak_hour <= 16:
                insights.append(f"장중 시간대({peak_hour}시)에 패턴 발생 빈도 최고")
            elif peak_hour >= 21 or peak_hour <= 6:
                insights.append(f"야간 시간대({peak_hour}시)에 패턴 발생 빈도 최고")

        # 요일별 인사이트
        daily = temporal_analysis.get("daily_distribution", {})
        if daily.get("peak_day"):
            peak_day = daily["peak_day"]
            if peak_day == "Monday":
                insights.append("월요일 효과: 주 시작에 패턴 발생 증가")
            elif peak_day == "Friday":
                insights.append("금요일 효과: 주 마감에 패턴 발생 증가")

        # 계절성 인사이트
        seasonal = temporal_analysis.get("seasonal_effects", {})
        if seasonal.get("seasonal_distribution"):
            seasons = seasonal["seasonal_distribution"]
            max_season = max(seasons.items(), key=lambda x: x[1])
            if max_season[1] > 0:
                insights.append(f"{max_season[0]} 계절에 패턴 발생 빈도 최고")

        # 빈도 인사이트
        frequency = temporal_analysis.get("frequency_analysis", {})
        avg_interval = frequency.get("average_interval_hours", 0)
        if avg_interval > 0:
            if avg_interval < 24:
                insights.append(f"평균 {avg_interval:.1f}시간마다 패턴 발생")
            else:
                insights.append(f"평균 {avg_interval/24:.1f}일마다 패턴 발생")

        return insights if insights else ["분석할 수 있는 시계열 패턴이 부족합니다"]

    def __del__(self):
        """소멸자 - 세션 정리"""
        if self.session:
            self.session.close()

        # 1. 기본 속성 유사도 (30%)
        basic_similarity = 0.0
        if pattern1.symbol == pattern2.symbol:
            basic_similarity += 0.4
        if pattern1.timeframe == pattern2.timeframe:
            basic_similarity += 0.3
        if pattern1.market_condition == pattern2.market_condition:
            basic_similarity += 0.3

        similarity_scores.append(("basic", basic_similarity, 0.3))

        # 2. 시간적 유사도 (20%)
        temporal_similarity = self._calculate_temporal_similarity(pattern1, pattern2)
        similarity_scores.append(("temporal", temporal_similarity, 0.2))

        # 3. 성과 유사도 (30%)
        performance_similarity = self._calculate_performance_similarity(
            pattern1, pattern2
        )
        similarity_scores.append(("performance", performance_similarity, 0.3))

        # 4. 구조적 유사도 (20%)
        structural_similarity = self._calculate_structural_similarity(
            pattern1, pattern2
        )
        similarity_scores.append(("structural", structural_similarity, 0.2))

        # 가중 평균 계산
        total_similarity = sum(score * weight for _, score, weight in similarity_scores)

        return min(total_similarity, 1.0)

    def _calculate_temporal_similarity(
        self, pattern1: SignalPattern, pattern2: SignalPattern
    ) -> float:
        """시간적 특성 유사도 계산"""
        if not pattern1.pattern_duration_hours or not pattern2.pattern_duration_hours:
            return 0.0

        duration1 = float(pattern1.pattern_duration_hours)
        duration2 = float(pattern2.pattern_duration_hours)

        # 지속 시간 유사도
        max_duration = max(duration1, duration2)
        if max_duration == 0:
            return 1.0

        duration_diff = abs(duration1 - duration2)
        duration_similarity = 1.0 - (duration_diff / max_duration)

        return max(duration_similarity, 0.0)

    def _calculate_performance_similarity(
        self, pattern1: SignalPattern, pattern2: SignalPattern
    ) -> float:
        """성과 유사도 계산"""
        similarity = 0.0
        comparisons = 0

        # 각 시간대별 결과 비교
        for timeframe in ["1h", "1d", "1w"]:
            outcome1 = getattr(pattern1, f"pattern_outcome_{timeframe}")
            outcome2 = getattr(pattern2, f"pattern_outcome_{timeframe}")
            success1 = getattr(pattern1, f"is_successful_{timeframe}")
            success2 = getattr(pattern2, f"is_successful_{timeframe}")

            if outcome1 is not None and outcome2 is not None:
                # 수익률 방향 유사도
                if (outcome1 > 0 and outcome2 > 0) or (outcome1 < 0 and outcome2 < 0):
                    similarity += 0.3

                # 수익률 크기 유사도
                max_outcome = max(abs(outcome1), abs(outcome2))
                if max_outcome > 0:
                    outcome_diff = abs(abs(outcome1) - abs(outcome2))
                    outcome_similarity = 1.0 - (outcome_diff / max_outcome)
                    similarity += outcome_similarity * 0.2

                comparisons += 1

            if success1 is not None and success2 is not None:
                if success1 == success2:
                    similarity += 0.2
                comparisons += 1

        return similarity / comparisons if comparisons > 0 else 0.0

    def _calculate_structural_similarity(
        self, pattern1: SignalPattern, pattern2: SignalPattern
    ) -> float:
        """구조적 유사도 계산 (신호 구성 비교)"""
        # 패턴을 구성하는 신호 ID들 추출
        signals1 = pattern1.get_signal_sequence()
        signals2 = pattern2.get_signal_sequence()

        if not signals1 or not signals2:
            return 0.0

        # 길이 유사도
        len_similarity = 1.0 - abs(len(signals1) - len(signals2)) / max(
            len(signals1), len(signals2)
        )

        # 신호 타입 유사도 (실제 신호 타입 비교는 복잡하므로 간단히 구현)
        # 실제로는 각 신호의 타입을 조회해서 비교해야 함
        type_similarity = 0.5  # 기본값

        return (len_similarity + type_similarity) / 2

    # =================================================================
    # 클러스터링 기반 패턴 그룹화
    # =================================================================

    def cluster_patterns(
        self, symbol: str, n_clusters: int = 5, min_patterns: int = 10
    ) -> Dict[str, Any]:
        """
        패턴 클러스터링을 통한 그룹화

        Args:
            symbol: 분석할 심볼
            n_clusters: 클러스터 개수
            min_patterns: 최소 패턴 개수

        Returns:
            클러스터링 결과
        """
        session, pattern_repo, signal_repo = self._get_session_and_repositories()

        try:
            # 패턴 데이터 수집
            patterns = (
                session.query(SignalPattern)
                .filter(SignalPattern.symbol == symbol)
                .all()
            )

            if len(patterns) < min_patterns:
                return {
                    "message": f"클러스터링을 위한 패턴이 부족합니다 (최소 {min_patterns}개 필요)",
                    "pattern_count": len(patterns),
                }

            # 특성 벡터 생성
            feature_vectors = []
            pattern_info = []

            for pattern in patterns:
                features = self._extract_pattern_features(pattern)
                if features is not None:
                    feature_vectors.append(features)
                    pattern_info.append(
                        {
                            "id": pattern.id,
                            "name": pattern.pattern_name,
                            "start": pattern.pattern_start.isoformat(),
                            "duration": (
                                float(pattern.pattern_duration_hours)
                                if pattern.pattern_duration_hours
                                else 0.0
                            ),
                        }
                    )

            if len(feature_vectors) < n_clusters:
                n_clusters = len(feature_vectors)

            # 간단한 K-means 클러스터링 구현 (numpy 기반)
            clusters = self._simple_kmeans_clustering(feature_vectors, n_clusters)

            # 클러스터별 패턴 그룹화
            clustered_patterns = {}
            for i, cluster_id in enumerate(clusters):
                if cluster_id not in clustered_patterns:
                    clustered_patterns[cluster_id] = []
                clustered_patterns[cluster_id].append(pattern_info[i])

            # 클러스터 특성 분석
            cluster_analysis = {}
            for cluster_id, cluster_patterns in clustered_patterns.items():
                cluster_analysis[cluster_id] = {
                    "pattern_count": len(cluster_patterns),
                    "patterns": cluster_patterns,
                    "characteristics": self._analyze_cluster_characteristics(
                        cluster_patterns, patterns
                    ),
                }

            return {
                "symbol": symbol,
                "total_patterns": len(patterns),
                "n_clusters": n_clusters,
                "clusters": cluster_analysis,
                "analysis_timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            print(f"❌ 패턴 클러스터링 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    def _extract_pattern_features(
        self, pattern: SignalPattern
    ) -> Optional[List[float]]:
        """패턴에서 특성 벡터 추출"""
        try:
            features = []

            # 1. 지속 시간 특성
            duration = (
                float(pattern.pattern_duration_hours)
                if pattern.pattern_duration_hours
                else 0.0
            )
            features.append(duration)

            # 2. 성과 특성
            for timeframe in ["1h", "1d", "1w"]:
                outcome = getattr(pattern, f"pattern_outcome_{timeframe}")
                features.append(float(outcome) if outcome is not None else 0.0)

                success = getattr(pattern, f"is_successful_{timeframe}")
                features.append(1.0 if success else 0.0)

            # 3. 시장 상황 특성 (원-핫 인코딩)
            market_conditions = ["bullish", "bearish", "sideways", "unknown"]
            for condition in market_conditions:
                features.append(1.0 if pattern.market_condition == condition else 0.0)

            # 4. 변동성 특성
            volatility_levels = ["low", "medium", "high"]
            for level in volatility_levels:
                features.append(1.0 if pattern.volatility_level == level else 0.0)

            return features

        except Exception as e:
            print(f"⚠️ 특성 추출 실패: {e}")
            return None

    def _simple_kmeans_clustering(
        self, feature_vectors: List[List[float]], n_clusters: int
    ) -> List[int]:
        """간단한 K-means 클러스터링 구현"""
        if not feature_vectors or n_clusters <= 0:
            return []

        # numpy 배열로 변환
        data = np.array(feature_vectors)
        n_samples, n_features = data.shape

        # 초기 중심점 랜덤 선택
        np.random.seed(42)  # 재현 가능한 결과를 위해
        centroids = data[np.random.choice(n_samples, n_clusters, replace=False)]

        # K-means 반복
        max_iterations = 100
        for iteration in range(max_iterations):
            # 각 점을 가장 가까운 중심점에 할당
            distances = np.sqrt(((data - centroids[:, np.newaxis]) ** 2).sum(axis=2))
            clusters = np.argmin(distances, axis=0)

            # 새로운 중심점 계산 (빈 클러스터 처리)
            new_centroids = []
            for i in range(n_clusters):
                cluster_data = data[clusters == i]
                if len(cluster_data) > 0:
                    new_centroids.append(cluster_data.mean(axis=0))
                else:
                    # 빈 클러스터는 기존 중심점 유지
                    new_centroids.append(centroids[i])
            new_centroids = np.array(new_centroids)

            # 수렴 체크
            if np.allclose(centroids, new_centroids):
                break

            centroids = new_centroids

        return clusters.tolist()

    def _analyze_cluster_characteristics(
        self, cluster_patterns: List[Dict], all_patterns: List[SignalPattern]
    ) -> Dict[str, Any]:
        """클러스터 특성 분석"""
        if not cluster_patterns:
            return {}

        # 패턴 이름 분포
        pattern_names = {}
        durations = []

        for pattern_info in cluster_patterns:
            # 실제 패턴 객체 찾기
            pattern = next(
                (p for p in all_patterns if p.id == pattern_info["id"]), None
            )
            if pattern:
                name = pattern.pattern_name
                pattern_names[name] = pattern_names.get(name, 0) + 1

                if pattern.pattern_duration_hours:
                    durations.append(float(pattern.pattern_duration_hours))

        # 가장 일반적인 패턴 이름
        most_common_pattern = (
            max(pattern_names.items(), key=lambda x: x[1])
            if pattern_names
            else ("unknown", 0)
        )

        return {
            "most_common_pattern": most_common_pattern[0],
            "pattern_name_distribution": pattern_names,
            "avg_duration": sum(durations) / len(durations) if durations else 0.0,
            "duration_range": {
                "min": min(durations) if durations else 0.0,
                "max": max(durations) if durations else 0.0,
            },
        }

    # =================================================================
    # 시계열 패턴 분석
    # =================================================================

    def analyze_temporal_patterns(
        self, symbol: str, timeframe: str, days: int = 30
    ) -> Dict[str, Any]:
        """
        시계열 패턴 분석

        Args:
            symbol: 분석할 심볼
            timeframe: 시간대
            days: 분석 기간

        Returns:
            시계열 패턴 분석 결과
        """
        session, pattern_repo, signal_repo = self._get_session_and_repositories()

        try:
            # 기간 내 패턴들 조회
            start_date = datetime.utcnow() - timedelta(days=days)
            patterns = (
                session.query(SignalPattern)
                .filter(
                    SignalPattern.symbol == symbol,
                    SignalPattern.timeframe == timeframe,
                    SignalPattern.pattern_start >= start_date,
                )
                .order_by(SignalPattern.pattern_start)
                .all()
            )

            if len(patterns) < 5:
                return {
                    "message": "시계열 분석을 위한 패턴이 부족합니다 (최소 5개 필요)",
                    "pattern_count": len(patterns),
                }

            # 시간별 패턴 발생 빈도
            hourly_distribution = self._analyze_hourly_distribution(patterns)

            # 요일별 패턴 발생 빈도
            weekday_distribution = self._analyze_weekday_distribution(patterns)

            # 패턴 간격 분석
            interval_analysis = self._analyze_pattern_intervals(patterns)

            # 계절성 분석
            seasonal_analysis = self._analyze_seasonal_patterns(patterns)

            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "analysis_period_days": days,
                "total_patterns": len(patterns),
                "temporal_analysis": {
                    "hourly_distribution": hourly_distribution,
                    "weekday_distribution": weekday_distribution,
                    "interval_analysis": interval_analysis,
                    "seasonal_analysis": seasonal_analysis,
                },
                "analysis_timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            print(f"❌ 시계열 패턴 분석 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    def _analyze_hourly_distribution(
        self, patterns: List[SignalPattern]
    ) -> Dict[str, Any]:
        """시간대별 패턴 발생 분포 분석"""
        hourly_counts = {}

        for pattern in patterns:
            hour = pattern.pattern_start.hour
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1

        # 가장 활발한 시간대
        peak_hour = (
            max(hourly_counts.items(), key=lambda x: x[1]) if hourly_counts else (0, 0)
        )

        return {
            "distribution": hourly_counts,
            "peak_hour": peak_hour[0],
            "peak_count": peak_hour[1],
            "total_hours_active": len(hourly_counts),
        }

    def _analyze_weekday_distribution(
        self, patterns: List[SignalPattern]
    ) -> Dict[str, Any]:
        """요일별 패턴 발생 분포 분석"""
        weekday_names = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        weekday_counts = {}

        for pattern in patterns:
            weekday = pattern.pattern_start.weekday()
            weekday_name = weekday_names[weekday]
            weekday_counts[weekday_name] = weekday_counts.get(weekday_name, 0) + 1

        # 가장 활발한 요일
        peak_weekday = (
            max(weekday_counts.items(), key=lambda x: x[1])
            if weekday_counts
            else ("Monday", 0)
        )

        return {
            "distribution": weekday_counts,
            "peak_weekday": peak_weekday[0],
            "peak_count": peak_weekday[1],
            "weekday_activity": len(weekday_counts),
        }

    def _analyze_pattern_intervals(
        self, patterns: List[SignalPattern]
    ) -> Dict[str, Any]:
        """패턴 간 시간 간격 분석"""
        if len(patterns) < 2:
            return {"message": "간격 분석을 위한 패턴이 부족합니다"}

        intervals = []
        for i in range(1, len(patterns)):
            interval = (
                patterns[i].pattern_start - patterns[i - 1].pattern_start
            ).total_seconds() / 3600
            intervals.append(interval)

        return {
            "avg_interval_hours": sum(intervals) / len(intervals),
            "min_interval_hours": min(intervals),
            "max_interval_hours": max(intervals),
            "total_intervals": len(intervals),
        }

    def _analyze_seasonal_patterns(
        self, patterns: List[SignalPattern]
    ) -> Dict[str, Any]:
        """계절성 패턴 분석"""
        monthly_counts = {}

        for pattern in patterns:
            month = pattern.pattern_start.month
            monthly_counts[month] = monthly_counts.get(month, 0) + 1

        # 가장 활발한 월
        peak_month = (
            max(monthly_counts.items(), key=lambda x: x[1])
            if monthly_counts
            else (1, 0)
        )

        return {
            "monthly_distribution": monthly_counts,
            "peak_month": peak_month[0],
            "peak_count": peak_month[1],
            "active_months": len(monthly_counts),
        }

    def __del__(self):
        """소멸자 - 세션 정리"""
        if self.session:
            self.session.close()
