#!/usr/bin/env python3
"""
자동화된 결과 업데이트 스크립트
주기적으로 실행하여 미완료 결과들을 업데이트합니다.
"""

import os
import sys
import time
import argparse
from datetime import datetime, timezone

# 환경 변수 설정
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5432"
os.environ["DB_NAME"] = "finstage_dev"
os.environ["DB_USER"] = "postgres"
os.environ["DB_PASSWORD"] = "password"

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.technical_analysis.service.enhanced_outcome_tracking_service import (
    EnhancedOutcomeTrackingService,
)


def run_update_cycle(service, batch_size=10, verbose=True):
    """
    한 번의 업데이트 사이클을 실행합니다

    Args:
        service: EnhancedOutcomeTrackingService 인스턴스
        batch_size: 한 번에 처리할 결과 개수
        verbose: 상세 로그 출력 여부

    Returns:
        dict: 업데이트 결과 통계
    """

    if verbose:
        print(
            f"🔄 업데이트 사이클 시작 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(f"📦 배치 크기: {batch_size}개")

    try:
        # 결과 업데이트 실행
        result = service.update_outcomes_with_detailed_logging(hours_old=1)

        if verbose:
            print(f"✅ 업데이트 완료:")
            print(f"   처리된 결과: {result.get('processed_count', 0)}개")
            print(f"   업데이트된 결과: {result.get('updated_count', 0)}개")
            print(f"   소요 시간: {result.get('duration', 0):.2f}초")

        return result

    except Exception as e:
        if verbose:
            print(f"❌ 업데이트 실패: {e}")
        return {"error": str(e), "processed_count": 0, "updated_count": 0}


def run_continuous_mode(service, interval_minutes=5, batch_size=10):
    """
    연속 모드로 실행합니다 (주기적으로 업데이트)

    Args:
        service: EnhancedOutcomeTrackingService 인스턴스
        interval_minutes: 업데이트 간격 (분)
        batch_size: 한 번에 처리할 결과 개수
    """

    print(f"🚀 연속 모드 시작")
    print(f"⏰ 업데이트 간격: {interval_minutes}분")
    print(f"📦 배치 크기: {batch_size}개")
    print(f"🛑 종료하려면 Ctrl+C를 누르세요")
    print("=" * 60)

    cycle_count = 0
    total_processed = 0
    total_updated = 0

    try:
        while True:
            cycle_count += 1
            print(f"\n🔄 사이클 #{cycle_count}")

            # 업데이트 실행
            result = run_update_cycle(service, batch_size, verbose=True)

            # 통계 누적
            total_processed += result.get("processed_count", 0)
            total_updated += result.get("updated_count", 0)

            # 전체 통계 출력
            print(f"📊 누적 통계:")
            print(f"   총 처리: {total_processed}개")
            print(f"   총 업데이트: {total_updated}개")
            print(f"   사이클: {cycle_count}회")

            # 다음 업데이트까지 대기
            print(f"⏳ {interval_minutes}분 대기 중...")
            time.sleep(interval_minutes * 60)

    except KeyboardInterrupt:
        print(f"\n👋 연속 모드 종료")
        print(f"📊 최종 통계:")
        print(f"   총 처리: {total_processed}개")
        print(f"   총 업데이트: {total_updated}개")
        print(f"   실행 사이클: {cycle_count}회")


def run_single_mode(service, batch_size=10):
    """
    단일 모드로 실행합니다 (한 번만 업데이트)

    Args:
        service: EnhancedOutcomeTrackingService 인스턴스
        batch_size: 한 번에 처리할 결과 개수
    """

    print(f"🎯 단일 모드 실행")
    result = run_update_cycle(service, batch_size, verbose=True)

    if "error" in result:
        print(f"❌ 실행 실패")
        return False
    else:
        print(f"✅ 실행 완료")
        return True


def main():
    """메인 함수"""

    # 명령행 인수 파싱
    parser = argparse.ArgumentParser(description="자동화된 결과 업데이트 스크립트")
    parser.add_argument(
        "--mode",
        choices=["single", "continuous"],
        default="single",
        help="실행 모드 (single: 한 번만, continuous: 연속)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="연속 모드에서 업데이트 간격 (분, 기본값: 5)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="한 번에 처리할 결과 개수 (기본값: 10)",
    )
    parser.add_argument("--quiet", action="store_true", help="상세 로그 출력 안함")

    args = parser.parse_args()

    # 서비스 초기화
    print("🔧 서비스 초기화 중...")
    service = EnhancedOutcomeTrackingService()

    try:
        if args.mode == "single":
            # 단일 모드
            success = run_single_mode(service, args.batch_size)
            sys.exit(0 if success else 1)

        elif args.mode == "continuous":
            # 연속 모드
            run_continuous_mode(service, args.interval, args.batch_size)

    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
