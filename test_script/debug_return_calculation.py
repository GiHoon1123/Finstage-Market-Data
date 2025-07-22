#!/usr/bin/env python3
"""
수익률 계산 디버깅 스크립트
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
    print("🔍 수익률 계산 디버깅")
    print("=" * 50)

    service = EnhancedOutcomeTrackingService()

    try:
        # 데이터베이스 연결 및 리포지토리 준비
        session, outcome_repo, signal_repo = service._get_session_and_repositories()

        # 샘플 데이터 확인
        print("📋 샘플 데이터 확인 (5개):")
        print("-" * 60)

        sample_query = """
        SELECT 
            so.id,
            s.signal_type,
            s.symbol,
            s.current_price as signal_price,
            so.price_1h_after,
            so.price_1d_after,
            so.return_1h,
            so.return_1d,
            s.created_at
        FROM signal_outcomes so
        JOIN technical_signals s ON so.signal_id = s.id
        WHERE so.is_complete = TRUE
        ORDER BY so.id DESC
        LIMIT 5
        """

        result = session.execute(text(sample_query))
        samples = result.fetchall()

        for sample in samples:
            (
                outcome_id,
                signal_type,
                symbol,
                signal_price,
                price_1h,
                price_1d,
                return_1h,
                return_1d,
                created_at,
            ) = sample

            print(f"ID: {outcome_id}")
            print(f"  신호: {signal_type} ({symbol})")
            print(f"  신호 시점 가격: ${float(signal_price or 0):.2f}")
            print(f"  1시간 후 가격: ${float(price_1h or 0):.2f}")
            print(f"  1일 후 가격: ${float(price_1d or 0):.2f}")
            print(f"  저장된 1시간 수익률: {float(return_1h or 0):.2f}%")
            print(f"  저장된 1일 수익률: {float(return_1d or 0):.2f}%")

            # 수동 계산
            if signal_price and price_1h:
                manual_return_1h = (
                    (float(price_1h) - float(signal_price)) / float(signal_price)
                ) * 100
                print(f"  수동 계산 1시간 수익률: {manual_return_1h:.2f}%")

            if signal_price and price_1d:
                manual_return_1d = (
                    (float(price_1d) - float(signal_price)) / float(signal_price)
                ) * 100
                print(f"  수동 계산 1일 수익률: {manual_return_1d:.2f}%")

            print(f"  생성 시간: {created_at}")
            print()

        # 수익률 분포 확인
        print("📊 수익률 분포 확인:")
        print("-" * 40)

        distribution_query = """
        SELECT 
            CASE 
                WHEN return_1d < -10 THEN '< -10%'
                WHEN return_1d < -5 THEN '-10% ~ -5%'
                WHEN return_1d < -1 THEN '-5% ~ -1%'
                WHEN return_1d < 0 THEN '-1% ~ 0%'
                WHEN return_1d < 1 THEN '0% ~ 1%'
                WHEN return_1d < 5 THEN '1% ~ 5%'
                WHEN return_1d < 10 THEN '5% ~ 10%'
                ELSE '> 10%'
            END as return_range,
            COUNT(*) as count
        FROM signal_outcomes so
        WHERE so.is_complete = TRUE AND so.return_1d IS NOT NULL
        GROUP BY return_range
        ORDER BY 
            CASE 
                WHEN return_range = '< -10%' THEN 1
                WHEN return_range = '-10% ~ -5%' THEN 2
                WHEN return_range = '-5% ~ -1%' THEN 3
                WHEN return_range = '-1% ~ 0%' THEN 4
                WHEN return_range = '0% ~ 1%' THEN 5
                WHEN return_range = '1% ~ 5%' THEN 6
                WHEN return_range = '5% ~ 10%' THEN 7
                ELSE 8
            END
        """

        dist_result = session.execute(text(distribution_query))
        distributions = dist_result.fetchall()

        for dist in distributions:
            range_name, count = dist
            print(f"{range_name}: {count}개")

        # 극단값 확인
        print("\n🔍 극단값 상세 확인:")
        print("-" * 30)

        extreme_detail_query = """
        SELECT 
            so.id,
            s.signal_type,
            s.symbol,
            s.current_price,
            so.price_1d_after,
            so.return_1d,
            s.created_at
        FROM signal_outcomes so
        JOIN technical_signals s ON so.signal_id = s.id
        WHERE so.is_complete = TRUE AND so.return_1d > 300
        ORDER BY so.return_1d DESC
        LIMIT 3
        """

        extreme_result = session.execute(text(extreme_detail_query))
        extremes = extreme_result.fetchall()

        print("🚀 극단적으로 높은 수익률:")
        for ext in extremes:
            (
                outcome_id,
                signal_type,
                symbol,
                signal_price,
                price_1d,
                return_1d,
                created_at,
            ) = ext
            manual_calc = (
                ((float(price_1d) - float(signal_price)) / float(signal_price)) * 100
                if signal_price and price_1d
                else 0
            )

            print(f"  ID {outcome_id}: {signal_type} ({symbol})")
            print(
                f"    신호가격: ${float(signal_price):.2f} → 1일후: ${float(price_1d):.2f}"
            )
            print(f"    저장된 수익률: {float(return_1d):.2f}%")
            print(f"    수동 계산: {manual_calc:.2f}%")
            print(f"    시간: {created_at}")
            print()

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
