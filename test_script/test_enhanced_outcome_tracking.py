#!/usr/bin/env python3
"""
향상된 결과 추적 서비스 테스트 스크립트 (초등학생도 이해할 수 있는 버전)

🎯 이 스크립트가 하는 일:
1. 새로운 향상된 결과 추적 서비스를 테스트합니다
2. 자세한 로그를 통해 어떤 일이 일어나는지 확인합니다
3. 시스템이 제대로 작동하는지 검증합니다

📚 테스트 순서:
1. 기존 신호에 대한 결과 추적 초기화 테스트
2. 미완료 결과들의 업데이트 테스트
3. 추적 상황 요약 정보 테스트
"""

# 필요한 라이브러리들을 가져옵니다
import traceback
from app.technical_analysis.service.enhanced_outcome_tracking_service import (
    EnhancedOutcomeTrackingService,
)
from datetime import datetime


def test_outcome_tracking_initialization():
    """
    결과 추적 초기화 기능을 테스트합니다

    🧪 이 테스트가 하는 일:
    1. 기존 신호 중 하나를 선택합니다
    2. 그 신호에 대한 결과 추적을 시작합니다
    3. 성공적으로 초기화되는지 확인합니다
    """
    print("=" * 60)
    print("🧪 테스트 1: 결과 추적 초기화")
    print("=" * 60)

    try:
        # 향상된 결과 추적 서비스 생성
        print("🏗️ 향상된 결과 추적 서비스를 생성합니다...")
        service = EnhancedOutcomeTrackingService()
        print("✅ 서비스 생성 완료!")

        # 테스트용 신호 ID (실제 존재하는 신호 ID를 사용해야 함)
        test_signal_id = 1  # 가장 첫 번째 신호로 테스트
        print(f"🎯 테스트 대상 신호 ID: {test_signal_id}")

        # 결과 추적 초기화 시도
        print(f"🚀 신호 ID {test_signal_id}의 결과 추적을 초기화합니다...")
        result = service.initialize_outcome_tracking(test_signal_id)

        if result:
            print(f"🎉 결과 추적 초기화 성공!")
            print(f"   📋 결과 ID: {result.id}")
            print(f"   🎯 신호 ID: {result.signal_id}")
            print(f"   📅 생성 시간: {result.created_at}")
        else:
            print(f"⚠️ 결과 추적 초기화 실패 (이미 존재하거나 신호를 찾을 수 없음)")

        return True

    except Exception as e:
        print(f"❌ 결과 추적 초기화 테스트 실패: {e}")
        traceback.print_exc()
        return False


def test_outcome_updates():
    """
    결과 업데이트 기능을 테스트합니다

    🧪 이 테스트가 하는 일:
    1. 미완료 결과들을 찾습니다
    2. 각 결과의 가격을 업데이트합니다
    3. 수익률을 계산합니다
    4. 업데이트 결과를 확인합니다
    """
    print("\n" + "=" * 60)
    print("🧪 테스트 2: 결과 업데이트")
    print("=" * 60)

    try:
        # 향상된 결과 추적 서비스 생성
        print("🏗️ 향상된 결과 추적 서비스를 생성합니다...")
        service = EnhancedOutcomeTrackingService()
        print("✅ 서비스 생성 완료!")

        # 미완료 결과들 업데이트 (1시간 이상 된 것들)
        print("🔄 미완료 결과들을 업데이트합니다...")
        print("⏰ 1시간 이상 된 신호들을 대상으로 합니다")

        result = service.update_outcomes_with_detailed_logging(hours_old=1)

        print(f"\n📊 업데이트 결과:")
        print(f"   ✅ 성공: {result.get('updated', 0)}개")
        print(f"   ❌ 실패: {result.get('errors', 0)}개")
        print(f"   🏁 완료: {result.get('completed', 0)}개")
        print(f"   📋 총 처리: {result.get('total_processed', 0)}개")

        if "error" in result:
            print(f"⚠️ 전체 오류: {result['error']}")
            return False

        return True

    except Exception as e:
        print(f"❌ 결과 업데이트 테스트 실패: {e}")
        traceback.print_exc()
        return False


def test_tracking_summary():
    """
    추적 상황 요약 기능을 테스트합니다

    🧪 이 테스트가 하는 일:
    1. 현재 추적 중인 모든 신호들의 상황을 요약합니다
    2. 완료율, 시간대별 데이터 수집 현황 등을 확인합니다
    3. 전체적인 시스템 상태를 파악합니다
    """
    print("\n" + "=" * 60)
    print("🧪 테스트 3: 추적 상황 요약")
    print("=" * 60)

    try:
        # 향상된 결과 추적 서비스 생성
        print("🏗️ 향상된 결과 추적 서비스를 생성합니다...")
        service = EnhancedOutcomeTrackingService()
        print("✅ 서비스 생성 완료!")

        # 추적 상황 요약 정보 가져오기
        print("📊 추적 상황 요약 정보를 생성합니다...")
        summary = service.get_tracking_summary()

        if "error" in summary:
            print(f"❌ 요약 정보 생성 실패: {summary['error']}")
            return False

        print(f"\n📋 추적 상황 요약:")
        print(f"   📊 총 추적 개수: {summary.get('총_추적_개수', 0)}개")
        print(f"   ✅ 완료된 추적: {summary.get('완료된_추적', 0)}개")
        print(f"   🔄 미완료 추적: {summary.get('미완료_추적', 0)}개")
        print(f"   📈 완료율: {summary.get('완료율', 0)}%")

        print(f"\n⏰ 시간대별 데이터 수집 현황:")
        time_data = summary.get("시간대별_데이터_수집현황", {})
        print(f"   1시간 후: {time_data.get('1시간_후', 0)}개")
        print(f"   4시간 후: {time_data.get('4시간_후', 0)}개")
        print(f"   1일 후: {time_data.get('1일_후', 0)}개")
        print(f"   1주일 후: {time_data.get('1주일_후', 0)}개")
        print(f"   1개월 후: {time_data.get('1개월_후', 0)}개")

        print(f"\n📅 생성 시간: {summary.get('생성_시간', 'N/A')}")

        return True

    except Exception as e:
        print(f"❌ 추적 상황 요약 테스트 실패: {e}")
        traceback.print_exc()
        return False


def main():
    """
    메인 함수 - 모든 테스트를 순서대로 실행합니다

    🎯 실행 순서:
    1. 결과 추적 초기화 테스트
    2. 결과 업데이트 테스트
    3. 추적 상황 요약 테스트
    4. 전체 결과 요약
    """
    print("🚀 향상된 결과 추적 서비스 테스트를 시작합니다!")
    print(f"📅 테스트 시작 시간: {datetime.now()}")

    # 테스트 결과를 저장할 변수들
    test_results = []

    # 테스트 1: 결과 추적 초기화
    result1 = test_outcome_tracking_initialization()
    test_results.append(("결과 추적 초기화", result1))

    # 테스트 2: 결과 업데이트
    result2 = test_outcome_updates()
    test_results.append(("결과 업데이트", result2))

    # 테스트 3: 추적 상황 요약
    result3 = test_tracking_summary()
    test_results.append(("추적 상황 요약", result3))

    # 전체 결과 요약
    print("\n" + "=" * 60)
    print("📋 전체 테스트 결과 요약")
    print("=" * 60)

    success_count = 0
    total_count = len(test_results)

    for test_name, success in test_results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"   {test_name}: {status}")
        if success:
            success_count += 1

    print(f"\n🎯 전체 결과: {success_count}/{total_count} 성공")
    print(f"📈 성공률: {(success_count/total_count*100):.1f}%")

    if success_count == total_count:
        print("🎉 모든 테스트가 성공했습니다!")
    else:
        print("⚠️ 일부 테스트가 실패했습니다. 로그를 확인해주세요.")

    print(f"📅 테스트 종료 시간: {datetime.now()}")


if __name__ == "__main__":
    main()
