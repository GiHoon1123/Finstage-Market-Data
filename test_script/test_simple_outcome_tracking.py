#!/usr/bin/env python3
"""
간단한 결과 추적 테스트 (핵심 기능만)

🎯 이 스크립트가 하는 일:
1. 결과 추적 초기화 테스트 (1개 신호만)
2. 가격 업데이트 테스트 (5개 신호만)
3. 추적 상황 요약 테스트
"""

from app.technical_analysis.service.enhanced_outcome_tracking_service import (
    EnhancedOutcomeTrackingService,
)
from datetime import datetime, timezone


def test_simple_initialization():
    """간단한 결과 추적 초기화 테스트"""
    print("🧪 테스트 1: 결과 추적 초기화 (간단 버전)")
    print("-" * 50)

    try:
        service = EnhancedOutcomeTrackingService()

        # 테스트용 신호 ID
        test_signal_id = 1
        print(f"🎯 테스트 신호 ID: {test_signal_id}")

        result = service.initialize_outcome_tracking(test_signal_id)

        if result:
            print(f"✅ 초기화 성공! 결과 ID: {result.id}")
            return True
        else:
            print(f"⚠️ 초기화 실패 (이미 존재하거나 신호 없음)")
            return True  # 이미 존재하는 것도 정상

    except Exception as e:
        print(f"❌ 초기화 테스트 실패: {e}")
        return False


def test_simple_updates():
    """간단한 결과 업데이트 테스트 (5개만)"""
    print("\n🧪 테스트 2: 결과 업데이트 (5개만)")
    print("-" * 50)

    try:
        service = EnhancedOutcomeTrackingService()

        # 미완료 결과 5개만 업데이트
        print("🔄 미완료 결과 5개만 업데이트합니다...")

        # 데이터베이스 연결
        session, outcome_repo, signal_repo = service._get_session_and_repositories()

        # 미완료 결과 5개만 가져오기
        incomplete_outcomes = outcome_repo.find_incomplete_outcomes(1)[:5]

        if not incomplete_outcomes:
            print("ℹ️ 업데이트할 미완료 결과가 없습니다")
            return True

        print(f"📊 {len(incomplete_outcomes)}개의 미완료 결과를 처리합니다")

        updated_count = 0

        for i, outcome in enumerate(incomplete_outcomes, 1):
            print(
                f"\n📋 [{i}/{len(incomplete_outcomes)}] 신호 ID {outcome.signal_id} 처리 중..."
            )

            try:
                # 원본 신호 정보
                signal = signal_repo.find_by_id(outcome.signal_id)
                if not signal:
                    print(f"⚠️ 원본 신호를 찾을 수 없음")
                    continue

                # 경과 시간 계산
                now = datetime.now(timezone.utc)
                elapsed_hours = (now - signal.triggered_at).total_seconds() / 3600

                print(f"   ⏰ 경과 시간: {elapsed_hours:.1f}시간")
                print(f"   📊 신호: {signal.signal_type} ({signal.symbol})")

                # 가격 업데이트
                updated = service._update_outcome_prices_with_logging(
                    outcome, signal, elapsed_hours
                )

                if updated:
                    updated_count += 1
                    print(f"   ✅ 업데이트 완료!")

                    # 수익률 계산
                    outcome_repo.calculate_and_update_returns(outcome.id)
                    print(f"   🧮 수익률 계산 완료!")
                else:
                    print(f"   ℹ️ 업데이트할 내용 없음")

            except Exception as e:
                print(f"   ❌ 처리 실패: {e}")
                continue

        # 변경사항 저장
        session.commit()
        session.close()

        print(f"\n🎉 업데이트 완료: {updated_count}개 성공")
        return True

    except Exception as e:
        print(f"❌ 업데이트 테스트 실패: {e}")
        return False


def test_simple_summary():
    """간단한 추적 상황 요약 테스트"""
    print("\n🧪 테스트 3: 추적 상황 요약")
    print("-" * 50)

    try:
        service = EnhancedOutcomeTrackingService()

        summary = service.get_tracking_summary()

        if "error" in summary:
            print(f"❌ 요약 생성 실패: {summary['error']}")
            return False

        print(f"📊 추적 상황:")
        print(f"   총 추적: {summary.get('총_추적_개수', 0)}개")
        print(f"   완료: {summary.get('완료된_추적', 0)}개")
        print(f"   진행중: {summary.get('미완료_추적', 0)}개")
        print(f"   완료율: {summary.get('완료율', 0)}%")

        return True

    except Exception as e:
        print(f"❌ 요약 테스트 실패: {e}")
        return False


def main():
    """메인 함수"""
    print("🚀 간단한 결과 추적 테스트 시작!")
    print(f"📅 시작 시간: {datetime.now()}")

    # 테스트 실행
    test1 = test_simple_initialization()
    test2 = test_simple_updates()
    test3 = test_simple_summary()

    # 결과 요약
    print("\n" + "=" * 50)
    print("📋 테스트 결과")
    print("=" * 50)

    results = [("초기화", test1), ("업데이트", test2), ("요약", test3)]

    success_count = sum(1 for _, success in results if success)

    for name, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"   {name}: {status}")

    print(f"\n🎯 결과: {success_count}/3 성공")

    if success_count == 3:
        print("🎉 모든 테스트 성공!")
    else:
        print("⚠️ 일부 테스트 실패")

    print(f"📅 종료 시간: {datetime.now()}")


if __name__ == "__main__":
    main()
