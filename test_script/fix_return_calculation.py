#!/usr/bin/env python3
"""
수익률 계산 수정 스크립트
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


def main():
    print("🔧 수익률 계산 수정")
    print("=" * 50)

    service = EnhancedOutcomeTrackingService()

    try:
        # 데이터베이스 연결 및 리포지토리 준비
        session, outcome_repo, signal_repo = service._get_session_and_repositories()

        # 1. 문제가 있는 데이터 확인
        print("🔍 문제가 있는 데이터 확인:")
        print("-" * 40)

        problem_query = """
        SELECT 
            COUNT(*) as total_outcomes,
            COUNT(CASE WHEN so.return_1d > 50 THEN 1 END) as high_returns,
            COUNT(CASE WHEN s.current_price < 5000 AND so.price_1d_after > 15000 THEN 1 END) as suspicious_price_jumps
        FROM signal_outcomes so
        JOIN technical_signals s ON so.signal_id = s.id
        WHERE so.is_complete = TRUE
        """

        problem_result = session.execute(text(problem_query))
        total, high_returns, suspicious = problem_result.fetchone()

        print(f"총 완료된 결과: {total}개")
        print(f"50% 이상 수익률: {high_returns}개 ({high_returns/total*100:.1f}%)")
        print(f"의심스러운 가격 점프: {suspicious}개")

        # 2. 수익률 재계산 (샘플)
        print("\n🔄 수익률 재계산 (샘플 10개):")
        print("-" * 50)

        sample_query = """
        SELECT 
            so.id,
            s.current_price as signal_price,
            so.price_1h_after,
            so.price_1d_after,
            so.return_1h,
            so.return_1d
        FROM signal_outcomes so
        JOIN technical_signals s ON so.signal_id = s.id
        WHERE so.is_complete = TRUE
        AND so.price_1d_after IS NOT NULL
        AND s.current_price IS NOT NULL
        ORDER BY so.id DESC
        LIMIT 10
        """

        sample_result = session.execute(text(sample_query))
        samples = sample_result.fetchall()

        updates_needed = []

        for sample in samples:
            (
                outcome_id,
                signal_price,
                price_1h,
                price_1d,
                stored_return_1h,
                stored_return_1d,
            ) = sample

            # 올바른 수익률 계산
            correct_return_1h = None
            correct_return_1d = None

            if signal_price and price_1h:
                correct_return_1h = (
                    (float(price_1h) - float(signal_price)) / float(signal_price)
                ) * 100

            if signal_price and price_1d:
                correct_return_1d = (
                    (float(price_1d) - float(signal_price)) / float(signal_price)
                ) * 100

            print(f"ID {outcome_id}:")
            print(f"  신호가격: ${float(signal_price):.2f}")
            print(f"  1일후가격: ${float(price_1d):.2f}")
            print(f"  저장된 수익률: {float(stored_return_1d or 0):.2f}%")
            print(f"  올바른 수익률: {correct_return_1d:.2f}%")

            # 차이가 큰 경우 업데이트 대상에 추가
            if abs(float(stored_return_1d or 0) - correct_return_1d) > 1.0:
                updates_needed.append(
                    {
                        "id": outcome_id,
                        "correct_return_1h": correct_return_1h,
                        "correct_return_1d": correct_return_1d,
                    }
                )
                print(f"  ⚠️ 수정 필요!")
            else:
                print(f"  ✅ 정상")
            print()

        # 3. 실제 업데이트 수행 여부 확인
        if updates_needed:
            print(f"🔧 {len(updates_needed)}개의 레코드가 수정이 필요합니다.")

            # 사용자 확인
            response = input("수익률을 수정하시겠습니까? (y/N): ")

            if response.lower() == "y":
                print("🔄 수익률 수정 중...")

                for update in updates_needed:
                    update_query = """
                    UPDATE signal_outcomes 
                    SET 
                        return_1h = :return_1h,
                        return_1d = :return_1d,
                        updated_at = NOW()
                    WHERE id = :id
                    """

                    session.execute(
                        text(update_query),
                        {
                            "id": update["id"],
                            "return_1h": update["correct_return_1h"],
                            "return_1d": update["correct_return_1d"],
                        },
                    )

                session.commit()
                print(f"✅ {len(updates_needed)}개 레코드 수정 완료!")
            else:
                print("❌ 수정을 취소했습니다.")
        else:
            print("✅ 수정이 필요한 레코드가 없습니다.")

        # 4. 전체 수익률 재계산 제안
        print("\n💡 전체 데이터 수익률 재계산:")
        print("-" * 40)
        print("모든 데이터의 수익률을 재계산하려면 다음 SQL을 실행하세요:")
        print(
            """
UPDATE signal_outcomes so
JOIN technical_signals s ON so.signal_id = s.id
SET 
    so.return_1h = CASE 
        WHEN so.price_1h_after IS NOT NULL AND s.current_price IS NOT NULL AND s.current_price > 0
        THEN ((so.price_1h_after - s.current_price) / s.current_price) * 100
        ELSE NULL
    END,
    so.return_4h = CASE 
        WHEN so.price_4h_after IS NOT NULL AND s.current_price IS NOT NULL AND s.current_price > 0
        THEN ((so.price_4h_after - s.current_price) / s.current_price) * 100
        ELSE NULL
    END,
    so.return_1d = CASE 
        WHEN so.price_1d_after IS NOT NULL AND s.current_price IS NOT NULL AND s.current_price > 0
        THEN ((so.price_1d_after - s.current_price) / s.current_price) * 100
        ELSE NULL
    END,
    so.return_1w = CASE 
        WHEN so.price_1w_after IS NOT NULL AND s.current_price IS NOT NULL AND s.current_price > 0
        THEN ((so.price_1w_after - s.current_price) / s.current_price) * 100
        ELSE NULL
    END,
    so.return_1m = CASE 
        WHEN so.price_1m_after IS NOT NULL AND s.current_price IS NOT NULL AND s.current_price > 0
        THEN ((so.price_1m_after - s.current_price) / s.current_price) * 100
        ELSE NULL
    END,
    so.updated_at = NOW()
WHERE so.is_complete = TRUE;
        """
        )

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # 세션 정리
        if "session" in locals():
            session.close()


if __name__ == "__main__":
    main()
