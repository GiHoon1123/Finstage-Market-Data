#!/usr/bin/env python3
"""
기술적 분석 시스템 테스트 스크립트
"""

from app.technical_analysis.service.technical_monitor_service import (
    TechnicalMonitorService,
)
from app.technical_analysis.service.signal_storage_service import SignalStorageService
from app.technical_analysis.service.outcome_tracking_service import (
    OutcomeTrackingService,
)
from datetime import datetime


def test_technical_monitoring():
    """기술적 분석 모니터링 테스트"""
    print("=== 기술적 분석 모니터링 테스트 ===")

    try:
        service = TechnicalMonitorService()

        print("1. 나스닥 지수 일봉 분석 테스트...")
        service.check_nasdaq_index_daily()

        print("2. S&P 500 지수 일봉 분석 테스트...")
        service.check_sp500_index_daily()

        print("✅ 기술적 분석 모니터링 테스트 완료")

    except Exception as e:
        print(f"❌ 기술적 분석 모니터링 테스트 실패: {e}")
        import traceback

        traceback.print_exc()


def test_signal_storage():
    """신호 저장 테스트"""
    print("\n=== 신호 저장 테스트 ===")

    try:
        service = SignalStorageService()

        # 테스트 신호 저장
        print("1. MA 돌파 신호 저장 테스트...")
        signal = service.save_ma_breakout_signal(
            symbol="^IXIC",
            timeframe="1day",
            ma_period=50,
            current_price=20000.0,
            ma_value=19900.0,
            signal_type="breakout_up",
            triggered_at=datetime.utcnow(),
        )

        if signal:
            print(f"✅ 신호 저장 성공: ID {signal.id}")

            # 결과 추적 초기화 테스트
            print("2. 결과 추적 초기화 테스트...")
            outcome_service = OutcomeTrackingService()
            outcome = outcome_service.initialize_outcome_tracking(signal.id)

            if outcome:
                print(f"✅ 결과 추적 초기화 성공: ID {outcome.id}")
            else:
                print("❌ 결과 추적 초기화 실패")
        else:
            print("❌ 신호 저장 실패")

    except Exception as e:
        print(f"❌ 신호 저장 테스트 실패: {e}")
        import traceback

        traceback.print_exc()


def test_outcome_tracking():
    """결과 추적 테스트"""
    print("\n=== 결과 추적 테스트 ===")

    try:
        service = OutcomeTrackingService()

        print("1. 미완료 결과 업데이트 테스트...")
        result = service.update_outcomes(hours_old=1)

        print(f"✅ 결과 추적 업데이트 완료:")
        print(f"   - 업데이트: {result.get('updated', 0)}개")
        print(f"   - 완료: {result.get('completed', 0)}개")
        print(f"   - 오류: {result.get('errors', 0)}개")

    except Exception as e:
        print(f"❌ 결과 추적 테스트 실패: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("🧪 고급 기술 분석 시스템 테스트 시작\n")

    # 1. 기술적 분석 모니터링 테스트
    test_technical_monitoring()

    # 2. 신호 저장 테스트
    test_signal_storage()

    # 3. 결과 추적 테스트
    test_outcome_tracking()

    print("\n🎉 모든 테스트 완료")
