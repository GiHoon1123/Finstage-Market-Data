#!/usr/bin/env python3
"""
간단한 K-means 클러스터링 테스트

패턴 데이터의 실제 상황에 맞춰 클러스터링을 테스트합니다.
"""

import os
import sys
from datetime import datetime
from typing import List, Dict, Any
import json

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.common.infra.database.config.database_config import SessionLocal
from app.technical_analysis.infra.model.entity.signal_patterns import SignalPattern
from app.technical_analysis.infra.model.entity.pattern_clusters import PatternCluster
from app.technical_analysis.infra.model.repository.pattern_cluster_repository import (
    PatternClusterRepository,
)


def extract_simple_features(pattern: SignalPattern) -> List[float]:
    """패턴에서 간단한 특성 추출"""
    features = []

    # 패턴 이름 기반 특성
    name = pattern.pattern_name.lower() if pattern.pattern_name else ""

    # 1. 신호 타입별 원-핫 인코딩
    signal_types = ["ma50", "ma200", "rsi", "bb", "macd", "volume"]
    for signal_type in signal_types:
        features.append(1.0 if signal_type in name else 0.0)

    # 2. 방향성 (상승/하락)
    bullish_terms = ["up", "breakout_up", "golden", "oversold"]
    bearish_terms = ["down", "breakout_down", "dead", "overbought"]

    bullish_score = sum(1 for term in bullish_terms if term in name)
    bearish_score = sum(1 for term in bearish_terms if term in name)

    features.append(min(bullish_score / 2.0, 1.0))  # 정규화
    features.append(min(bearish_score / 2.0, 1.0))  # 정규화

    # 3. 패턴 복잡도 (이름 길이 기반)
    complexity = min(len(name.split("_")) / 10.0, 1.0)
    features.append(complexity)

    # 4. 시간적 특성
    if pattern.pattern_start:
        features.append(pattern.pattern_start.weekday() / 6.0)  # 요일
        features.append(pattern.pattern_start.month / 12.0)  # 월
    else:
        features.extend([0.5, 0.5])

    return features


def simple_kmeans(
    feature_vectors: List[List[float]], n_clusters: int = 6
) -> List[List[int]]:
    """간단한 K-means 클러스터링"""
    if not feature_vectors or n_clusters <= 0:
        return []

    n_features = len(feature_vectors[0])
    n_points = len(feature_vectors)

    if n_points < n_clusters:
        n_clusters = max(2, n_points // 2)

    # 초기 중심점 설정 (더 나은 초기화)
    import random

    random.seed(42)

    centroids = []
    for i in range(n_clusters):
        # 데이터 범위 내에서 랜덤 중심점 생성
        centroid = []
        for j in range(n_features):
            feature_values = [vec[j] for vec in feature_vectors]
            min_val, max_val = min(feature_values), max(feature_values)
            centroid.append(random.uniform(min_val, max_val))
        centroids.append(centroid)

    # K-means 반복
    for iteration in range(100):
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
                # 빈 클러스터는 기존 중심점 유지
                new_centroids.append(centroids[len(new_centroids)])

        # 수렴 체크
        converged = True
        for old, new in zip(centroids, new_centroids):
            distance = sum((o - n) ** 2 for o, n in zip(old, new)) ** 0.5
            if distance > 0.001:
                converged = False
                break

        centroids = new_centroids

        if converged:
            print(f"✅ K-means 수렴 완료 (반복: {iteration + 1}회)")
            break

    return clusters


def analyze_cluster(
    cluster_patterns: List[SignalPattern], cluster_features: List[List[float]]
) -> Dict[str, Any]:
    """클러스터 특성 분석"""
    if not cluster_patterns:
        return {}

    # 패턴 이름 분석
    pattern_names = [p.pattern_name for p in cluster_patterns if p.pattern_name]

    # 공통 용어 찾기
    all_terms = []
    for name in pattern_names:
        all_terms.extend(name.lower().split("_"))

    term_counts = {}
    for term in all_terms:
        term_counts[term] = term_counts.get(term, 0) + 1

    # 가장 빈번한 용어들
    common_terms = sorted(term_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    # 방향성 분석
    bullish_count = sum(
        1
        for name in pattern_names
        if any(term in name.lower() for term in ["up", "breakout_up"])
    )
    bearish_count = sum(
        1
        for name in pattern_names
        if any(term in name.lower() for term in ["down", "breakout_down"])
    )

    bullish_tendency = bullish_count / len(pattern_names) if pattern_names else 0
    bearish_tendency = bearish_count / len(pattern_names) if pattern_names else 0

    # 성공률 추정 (간단한 휴리스틱)
    if bullish_tendency > 0.6:
        success_rate = 65.0  # 상승 패턴은 높은 성공률
    elif bearish_tendency > 0.6:
        success_rate = 60.0  # 하락 패턴도 높은 성공률
    else:
        success_rate = 50.0  # 중립 패턴

    return {
        "pattern_count": len(cluster_patterns),
        "common_terms": [term for term, count in common_terms],
        "bullish_tendency": bullish_tendency,
        "bearish_tendency": bearish_tendency,
        "avg_success_rate": success_rate,
        "dominant_signal_types": list(
            set(term for term, count in common_terms if count > 1)
        ),
    }


def generate_cluster_name(cluster_stats: Dict[str, Any], cluster_id: int) -> str:
    """클러스터 이름 생성"""
    common_terms = cluster_stats.get("common_terms", [])
    bullish_tendency = cluster_stats.get("bullish_tendency", 0)
    bearish_tendency = cluster_stats.get("bearish_tendency", 0)

    # 주요 용어 기반 이름 생성
    if common_terms:
        main_term = common_terms[0]
        if bullish_tendency > 0.6:
            return f"{main_term.upper()}_상승_패턴"
        elif bearish_tendency > 0.6:
            return f"{main_term.upper()}_하락_패턴"
        else:
            return f"{main_term.upper()}_중립_패턴"
    else:
        return f"클러스터_{cluster_id}"


def save_cluster_results(
    symbol: str,
    clusters: List[List[int]],
    patterns: List[SignalPattern],
    feature_vectors: List[List[float]],
) -> int:
    """클러스터링 결과를 DB에 저장"""
    session = SessionLocal()
    cluster_repo = PatternClusterRepository(session)

    saved_count = 0
    clustered_at = datetime.utcnow()

    try:
        for cluster_id, cluster_indices in enumerate(clusters):
            if not cluster_indices:
                continue

            # 클러스터 패턴들
            cluster_patterns = [patterns[i] for i in cluster_indices]
            cluster_features = [feature_vectors[i] for i in cluster_indices]

            # 클러스터 분석
            cluster_stats = analyze_cluster(cluster_patterns, cluster_features)
            cluster_name = generate_cluster_name(cluster_stats, cluster_id)

            # 클러스터 중심점 계산
            if cluster_features:
                n_features = len(cluster_features[0])
                cluster_center = []
                for j in range(n_features):
                    avg = sum(features[j] for features in cluster_features) / len(
                        cluster_features
                    )
                    cluster_center.append(avg)
            else:
                cluster_center = []

            # 대표 패턴 선택 (최대 5개)
            representative_patterns = [p.id for p in cluster_patterns[:5]]

            # PatternCluster 엔티티 생성
            pattern_cluster = PatternCluster(
                symbol=symbol,
                cluster_id=cluster_id,
                cluster_name=cluster_name,
                timeframe="1day",
                pattern_count=len(cluster_patterns),
                avg_success_rate=cluster_stats.get("avg_success_rate", 50.0),
                avg_confidence_score=75.0,  # 기본값
                avg_duration_hours=0.0,  # 현재 데이터에서는 0
                bullish_tendency=cluster_stats.get("bullish_tendency", 0.0),
                bearish_tendency=cluster_stats.get("bearish_tendency", 0.0),
                dominant_signal_types=json.dumps(
                    cluster_stats.get("dominant_signal_types", [])
                ),
                cluster_center=json.dumps(cluster_center),
                cluster_radius=0.5,  # 기본값
                representative_patterns=json.dumps(representative_patterns),
                pattern_examples=json.dumps(
                    {
                        "main_patterns": [p.pattern_name for p in cluster_patterns[:3]],
                        "cluster_description": f"{cluster_name} - {len(cluster_patterns)}개 패턴",
                    }
                ),
                clustering_algorithm="kmeans",
                n_clusters_total=len(clusters),
                clustering_quality_score=80.0,  # 기본값
                clustered_at=clustered_at,
            )

            # DB에 저장
            cluster_repo.save(pattern_cluster)
            saved_count += 1

            print(
                f"  ✅ {cluster_name}: {len(cluster_patterns)}개 패턴 (성공률: {cluster_stats.get('avg_success_rate', 50.0):.1f}%)"
            )

        session.commit()
        return saved_count

    except Exception as e:
        session.rollback()
        print(f"❌ 클러스터 저장 실패: {e}")
        return 0
    finally:
        session.close()


def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("🧠 간단한 K-means 클러스터링 테스트")
    print("=" * 80)

    symbols = ["^IXIC", "^GSPC"]

    for symbol in symbols:
        print(f"\n🔄 {symbol} 클러스터링 시작...")

        # 세션 생성
        session = SessionLocal()

        try:
            # 패턴 데이터 조회
            patterns = (
                session.query(SignalPattern)
                .filter(SignalPattern.symbol == symbol)
                .all()
            )

            if len(patterns) < 10:
                print(f"⚠️ {symbol}: 패턴이 부족합니다 ({len(patterns)}개)")
                continue

            print(f"📊 {symbol}: {len(patterns)}개 패턴 발견")

            # 특성 벡터 추출
            feature_vectors = []
            valid_patterns = []

            for pattern in patterns:
                features = extract_simple_features(pattern)
                if features and len(features) == 11:  # 예상 특성 개수
                    feature_vectors.append(features)
                    valid_patterns.append(pattern)

            print(f"✅ {symbol}: {len(feature_vectors)}개 패턴의 특성 벡터 생성")

            if len(feature_vectors) < 6:
                print(f"⚠️ {symbol}: 클러스터링을 위한 패턴이 부족합니다")
                continue

            # K-means 클러스터링 실행
            print(f"🧠 {symbol} K-means 클러스터링 실행...")
            clusters = simple_kmeans(feature_vectors, n_clusters=6)

            # 결과 출력
            non_empty_clusters = [c for c in clusters if c]
            print(f"✅ {symbol}: {len(non_empty_clusters)}개 클러스터 생성")

            for i, cluster_indices in enumerate(clusters):
                if cluster_indices:
                    print(f"  - 클러스터 {i}: {len(cluster_indices)}개 패턴")

            # DB에 저장
            print(f"💾 {symbol} 클러스터링 결과 저장...")
            saved_count = save_cluster_results(
                symbol, clusters, valid_patterns, feature_vectors
            )
            print(f"✅ {symbol}: {saved_count}개 클러스터 저장 완료")

        except Exception as e:
            print(f"❌ {symbol} 클러스터링 실패: {e}")
        finally:
            session.close()

    print("\n" + "=" * 80)
    print("🎉 클러스터링 테스트 완료!")
    print("=" * 80)


if __name__ == "__main__":
    main()
