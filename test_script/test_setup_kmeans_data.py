#!/usr/bin/env python3
"""
K-means 클러스터링을 위한 데이터 준비 스크립트

실행 순서:
1. 과거 데이터 수집 (2년치)
2. 기술적 신호 생성
3. 패턴 발견
4. K-means 클러스터링 실행
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 환경 설정
mode = os.getenv("ENV_MODE", "dev")
env_file = f".env.{mode}"
load_dotenv(dotenv_path=env_file)

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.technical_analysis.service.historical_data_service import HistoricalDataService
from app.technical_analysis.service.signal_generator_service import (
    SignalGeneratorService,
)
from app.technical_analysis.service.pattern_analysis_service import (
    PatternAnalysisService,
)
from app.technical_analysis.service.advanced_pattern_service import (
    AdvancedPatternService,
)


def step1_collect_data():
    """1단계: 과거 데이터 수집"""
    print("🔄 1단계: 과거 데이터 수집 시작...")

    service = HistoricalDataService()
    result = service.collect_10_years_data(
        symbols=["^IXIC", "^GSPC"], start_year=2022  # 2년치 데이터
    )

    if "error" in result:
        print(f"❌ 데이터 수집 실패: {result['error']}")
        return False
    else:
        print(f"✅ 데이터 수집 완료!")
        print(f"   - 총 저장: {result['summary']['total_saved']}개")
        return True


def step2_generate_signals():
    """2단계: 기술적 신호 생성"""
    print("🔄 2단계: 기술적 신호 생성 시작...")

    service = SignalGeneratorService()
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=365 * 2)  # 2년치

    result = service.generate_all_signals(
        symbols=["^IXIC", "^GSPC"], start_date=start_date, end_date=end_date
    )

    if "error" in result:
        print(f"❌ 신호 생성 실패: {result['error']}")
        return False
    else:
        print(f"✅ 신호 생성 완료!")
        print(f"   - 총 신호: {result['summary']['total_signals']}개")
        return True


def step3_discover_patterns():
    """3단계: 패턴 발견"""
    print("🔄 3단계: 패턴 발견 시작...")

    service = PatternAnalysisService()
    total_patterns = 0

    for symbol in ["^IXIC", "^GSPC"]:
        print(f"   📊 {symbol} 패턴 분석 중...")
        result = service.discover_patterns(symbol, "1day")

        if "error" in result:
            print(f"   ❌ {symbol} 패턴 발견 실패: {result['error']}")
        else:
            pattern_count = result.get("total_patterns", 0)
            total_patterns += pattern_count
            print(f"   ✅ {symbol}: {pattern_count}개 패턴 발견")

    print(f"✅ 패턴 발견 완료: 총 {total_patterns}개")
    return total_patterns > 0


def step4_run_clustering():
    """4단계: K-means 클러스터링 실행"""
    print("🔄 4단계: K-means 클러스터링 시작...")

    service = AdvancedPatternService()

    for symbol in ["^IXIC", "^GSPC"]:
        print(f"   🧠 {symbol} 클러스터링 중...")
        result = service.cluster_patterns(symbol=symbol, n_clusters=6, min_patterns=10)

        if "error" in result:
            print(f"   ❌ {symbol} 클러스터링 실패: {result['error']}")
        else:
            clusters = result.get("n_clusters", 0)
            total_patterns = result.get("total_patterns", 0)
            print(
                f"   ✅ {symbol}: {total_patterns}개 패턴을 {clusters}개 그룹으로 분류"
            )

            # 클러스터 정보 출력
            for cluster in result.get("clusters", []):
                print(
                    f"      - {cluster['cluster_name']}: {cluster['pattern_count']}개"
                )

    print("✅ K-means 클러스터링 완료!")


def main():
    """전체 프로세스 실행"""
    print("🚀 K-means 클러스터링 데이터 준비 시작")
    print("=" * 60)

    try:
        # 1단계: 데이터 수집
        if not step1_collect_data():
            print("❌ 1단계 실패로 중단")
            return

        # 2단계: 신호 생성
        if not step2_generate_signals():
            print("❌ 2단계 실패로 중단")
            return

        # 3단계: 패턴 발견
        if not step3_discover_patterns():
            print("❌ 3단계 실패로 중단")
            return

        # 4단계: 클러스터링
        step4_run_clustering()

        print("\n" + "=" * 60)
        print("🎉 모든 단계 완료!")
        print("이제 일일 리포트에서 실제 K-means 결과를 볼 수 있습니다.")

    except Exception as e:
        print(f"❌ 전체 프로세스 실패: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
