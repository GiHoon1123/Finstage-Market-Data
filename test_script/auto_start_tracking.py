#!/usr/bin/env python3
"""
새로운 신호에 대해 자동으로 결과 추적을 시작하는 스크립트
기존 스케줄러에 통합하거나 별도로 실행할 수 있습니다.
"""

import os
import sys

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
from sqlalchemy import text


def get_untracked_signals(session):
    """
    아직 결과 추적이 시작되지 않은 신호들을 찾습니다
    """
    query = """
    SELECT s.id, s.signal_type, s.symbol, s.created_at
    FROM technical_signals s
    LEFT JOIN signal_outcomes so ON s.id = so.signal_id
    WHERE so.signal_id IS NULL
    ORDER BY s.created_at DESC
    LIMIT 100
    """

    result = session.execute(text(query))
    return result.fetchall()


def start_tracking_for_new_signals():
    """
    새로운 신호들에 대해 결과 추적을 시작합니다
    """
    print("🔍 새로운 신호 확인 중...")

    service = EnhancedOutcomeTrackingService()

    try:
        # 데이터베이스 연결
        session, _, _ = service._get_session_and_repositories()

        # 추적되지 않은 신호들 찾기
        untracked_signals = get_untracked_signals(session)

        if not untracked_signals:
            print("✅ 새로운 신호가 없습니다.")
            return 0

        print(f"📋 {len(untracked_signals)}개의 새로운 신호 발견!")

        success_count = 0

        for signal_id, signal_type, symbol, created_at in untracked_signals:
            try:
                print(f"🎯 신호 ID {signal_id} 추적 시작: {signal_type} ({symbol})")

                # 결과 추적 초기화
                outcome = service.initialize_outcome_tracking(signal_id)

                if outcome:
                    success_count += 1
                    print(f"   ✅ 추적 시작 성공!")
                else:
                    print(f"   ⚠️ 추적 시작 실패 (이미 존재하거나 오류)")

            except Exception as e:
                print(f"   ❌ 오류 발생: {e}")

        print(f"\n🎉 완료: {success_count}/{len(untracked_signals)}개 신호 추적 시작")

        # 세션 정리
        session.close()

        return success_count

    except Exception as e:
        print(f"❌ 전체 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        return 0


def main():
    """메인 함수"""
    print("🚀 자동 결과 추적 시작 스크립트")
    print("=" * 50)

    started_count = start_tracking_for_new_signals()

    if started_count > 0:
        print(f"\n💡 이제 다음 명령으로 업데이트를 실행하세요:")
        print(
            f"python automated_outcome_updater.py --mode single --batch-size {min(started_count, 20)}"
        )

    print("\n👋 완료!")


if __name__ == "__main__":
    main()
