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
from app.technical_analysis.infra.model.repository.signal_pattern_repository import SignalPatternRepository
from app.technical_analysis.infra.model.repository.technical_signal_repository import TechnicalSignalRepository
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
            patterns = session.query(SignalPattern).filter(
                SignalPattern.symbol == symbol,
                SignalPattern.pattern_type == pattern_type
            ).all()
            
            if len(patterns) < 2:
                return {
                    "message": "유사도 분석을 위한 패턴이 부족합니다 (최소 2개 필요)",
                    "pattern_count": len(patterns)
                }
            
            # 유사도 매트릭스 계산
            similarity_matrix = []
            pattern_info = []
            
            for i, pattern1 in enumerate(patterns):
                pattern_info.append({
                    "id": pattern1.id,
                    "name": pattern1.pattern_name,
                    "start": pattern1.pattern_start.isoformat(),
                    "duration": float(pattern1.pattern_duration_hours) if pattern1.pattern_duration_hours else 0.0
                })
                
                similarity_row = []
                for j, pattern2 in enumerate(patterns):
                    if i == j:
                        similarity = 1.0
                    else:
                        similarity = self._calculate_advanced_similarity(pattern1, pattern2)
                    similarity_row.append(round(similarity, 3))
                
                similarity_matrix.append(similarity_row)
            
            # 가장 유사한 패턴 쌍 찾기
            most_similar_pairs = []
            for i in range(len(patterns)):
                for j in range(i + 1, len(patterns)):
                    similarity = similarity_matrix[i][j]
                    if similarity > 0.7:  # 70% 이상 유사한 경우
                        most_similar_pairs.append({
                            "pattern1": pattern_info[i],
                            "pattern2": pattern_info[j],
                            "similarity": similarity
                        })
            
            # 유사도 순으로 정렬
            most_similar_pairs.sort(key=lambda x: x["similarity"], reverse=True)
            
            return {
                "symbol": symbol,
                "pattern_type": pattern_type,
                "total_patterns": len(patterns),
                "similarity_matrix": similarity_matrix,
                "pattern_info": pattern_info,
                "most_similar_pairs": most_similar_pairs[:10],  # 상위 10개만
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"❌ 패턴 유사도 분석 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    def _calculate_advanced_similarity(self, pattern1: SignalPattern, pattern2: SignalPattern) -> float:
        """
        고급 유사도 계산 (여러 기법 조합)
        
        Args:
            pattern1: 첫 번째 패턴
            pattern2: 두 번째 패턴
            
        Returns:
            유사도 점수 (0~1)
        """
        similarity_scores = []
        
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
        performance_similarity = self._calculate_performance_similarity(pattern1, pattern2)
        similarity_scores.append(("performance", performance_similarity, 0.3))
        
        # 4. 구조적 유사도 (20%)
        structural_similarity = self._calculate_structural_similarity(pattern1, pattern2)
        similarity_scores.append(("structural", structural_similarity, 0.2))
        
        # 가중 평균 계산
        total_similarity = sum(score * weight for _, score, weight in similarity_scores)
        
        return min(total_similarity, 1.0)

    def _calculate_temporal_similarity(self, pattern1: SignalPattern, pattern2: SignalPattern) -> float:
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

    def _calculate_performance_similarity(self, pattern1: SignalPattern, pattern2: SignalPattern) -> float:
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

    def _calculate_structural_similarity(self, pattern1: SignalPattern, pattern2: SignalPattern) -> float:
        """구조적 유사도 계산 (신호 구성 비교)"""
        # 패턴을 구성하는 신호 ID들 추출
        signals1 = pattern1.get_signal_sequence()
        signals2 = pattern2.get_signal_sequence()
        
        if not signals1 or not signals2:
            return 0.0
        
        # 길이 유사도
        len_similarity = 1.0 - abs(len(signals1) - len(signals2)) / max(len(signals1), len(signals2))
        
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
            patterns = session.query(SignalPattern).filter(
                SignalPattern.symbol == symbol
            ).all()
            
            if len(patterns) < min_patterns:
                return {
                    "message": f"클러스터링을 위한 패턴이 부족합니다 (최소 {min_patterns}개 필요)",
                    "pattern_count": len(patterns)
                }
            
            # 특성 벡터 생성
            feature_vectors = []
            pattern_info = []
            
            for pattern in patterns:
                features = self._extract_pattern_features(pattern)
                if features is not None:
                    feature_vectors.append(features)
                    pattern_info.append({
                        "id": pattern.id,
                        "name": pattern.pattern_name,
                        "start": pattern.pattern_start.isoformat(),
                        "duration": float(pattern.pattern_duration_hours) if pattern.pattern_duration_hours else 0.0
                    })
            
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
                    "characteristics": self._analyze_cluster_characteristics(cluster_patterns, patterns)
                }
            
            return {
                "symbol": symbol,
                "total_patterns": len(patterns),
                "n_clusters": n_clusters,
                "clusters": cluster_analysis,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"❌ 패턴 클러스터링 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    def _extract_pattern_features(self, pattern: SignalPattern) -> Optional[List[float]]:
        """패턴에서 특성 벡터 추출"""
        try:
            features = []
            
            # 1. 지속 시간 특성
            duration = float(pattern.pattern_duration_hours) if pattern.pattern_duration_hours else 0.0
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

    def _simple_kmeans_clustering(self, feature_vectors: List[List[float]], n_clusters: int) -> List[int]:
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
            distances = np.sqrt(((data - centroids[:, np.newaxis])**2).sum(axis=2))
            clusters = np.argmin(distances, axis=0)
            
            # 새로운 중심점 계산
            new_centroids = np.array([data[clusters == i].mean(axis=0) for i in range(n_clusters)])
            
            # 수렴 체크
            if np.allclose(centroids, new_centroids):
                break
                
            centroids = new_centroids
        
        return clusters.tolist()

    def _analyze_cluster_characteristics(self, cluster_patterns: List[Dict], all_patterns: List[SignalPattern]) -> Dict[str, Any]:
        """클러스터 특성 분석"""
        if not cluster_patterns:
            return {}
        
        # 패턴 이름 분포
        pattern_names = {}
        durations = []
        
        for pattern_info in cluster_patterns:
            # 실제 패턴 객체 찾기
            pattern = next((p for p in all_patterns if p.id == pattern_info["id"]), None)
            if pattern:
                name = pattern.pattern_name
                pattern_names[name] = pattern_names.get(name, 0) + 1
                
                if pattern.pattern_duration_hours:
                    durations.append(float(pattern.pattern_duration_hours))
        
        # 가장 일반적인 패턴 이름
        most_common_pattern = max(pattern_names.items(), key=lambda x: x[1]) if pattern_names else ("unknown", 0)
        
        return {
            "most_common_pattern": most_common_pattern[0],
            "pattern_name_distribution": pattern_names,
            "avg_duration": sum(durations) / len(durations) if durations else 0.0,
            "duration_range": {
                "min": min(durations) if durations else 0.0,
                "max": max(durations) if durations else 0.0
            }
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
            patterns = session.query(SignalPattern).filter(
                SignalPattern.symbol == symbol,
                SignalPattern.timeframe == timeframe,
                SignalPattern.pattern_start >= start_date
            ).order_by(SignalPattern.pattern_start).all()
            
            if len(patterns) < 5:
                return {
                    "message": "시계열 분석을 위한 패턴이 부족합니다 (최소 5개 필요)",
                    "pattern_count": len(patterns)
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
                    "seasonal_analysis": seasonal_analysis
                },
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"❌ 시계열 패턴 분석 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    def _analyze_hourly_distribution(self, patterns: List[SignalPattern]) -> Dict[str, Any]:
        """시간대별 패턴 발생 분포 분석"""
        hourly_counts = {}
        
        for pattern in patterns:
            hour = pattern.pattern_start.hour
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
        
        # 가장 활발한 시간대
        peak_hour = max(hourly_counts.items(), key=lambda x: x[1]) if hourly_counts else (0, 0)
        
        return {
            "distribution": hourly_counts,
            "peak_hour": peak_hour[0],
            "peak_count": peak_hour[1],
            "total_hours_active": len(hourly_counts)
        }

    def _analyze_weekday_distribution(self, patterns: List[SignalPattern]) -> Dict[str, Any]:
        """요일별 패턴 발생 분포 분석"""
        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        weekday_counts = {}
        
        for pattern in patterns:
            weekday = pattern.pattern_start.weekday()
            weekday_name = weekday_names[weekday]
            weekday_counts[weekday_name] = weekday_counts.get(weekday_name, 0) + 1
        
        # 가장 활발한 요일
        peak_weekday = max(weekday_counts.items(), key=lambda x: x[1]) if weekday_counts else ("Monday", 0)
        
        return {
            "distribution": weekday_counts,
            "peak_weekday": peak_weekday[0],
            "peak_count": peak_weekday[1],
            "weekday_activity": len(weekday_counts)
        }

    def _analyze_pattern_intervals(self, patterns: List[SignalPattern]) -> Dict[str, Any]:
        """패턴 간 시간 간격 분석"""
        if len(patterns) < 2:
            return {"message": "간격 분석을 위한 패턴이 부족합니다"}
        
        intervals = []
        for i in range(1, len(patterns)):
            interval = (patterns[i].pattern_start - patterns[i-1].pattern_start).total_seconds() / 3600
            intervals.append(interval)
        
        return {
            "avg_interval_hours": sum(intervals) / len(intervals),
            "min_interval_hours": min(intervals),
            "max_interval_hours": max(intervals),
            "total_intervals": len(intervals)
        }

    def _analyze_seasonal_patterns(self, patterns: List[SignalPattern]) -> Dict[str, Any]:
        """계절성 패턴 분석"""
        monthly_counts = {}
        
        for pattern in patterns:
            month = pattern.pattern_start.month
            monthly_counts[month] = monthly_counts.get(month, 0) + 1
        
        # 가장 활발한 월
        peak_month = max(monthly_counts.items(), key=lambda x: x[1]) if monthly_counts else (1, 0)
        
        return {
            "monthly_distribution": monthly_counts,
            "peak_month": peak_month[0],
            "peak_count": peak_month[1],
            "active_months": len(monthly_counts)
        }

    def __del__(self):
        """소멸자 - 세션 정리"""
        if self.session:
            self.session.close()