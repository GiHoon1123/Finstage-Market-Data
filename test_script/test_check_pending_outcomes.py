#!/usr/bin/env python3
"""
미완료 결과 확인 스크립트

이 스크립트는 아직 완료되지 않은 결과 추적들을 확인합니다.
"""

import os
import sys
import traceback
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
from sqlalchemy import text


def main():
    print("🔍 진행 중인 결과 추적 상태 확인")
    print("=" * 50)

    service = EnhancedOutcomeTrackingService()

    try:
        # 진행 중인 결과들 조회
        print("📊 진행 중인 결과들을 조회합니다...")

        # 데이터베이스 연결 및 리포지토리 준비
        session, outcome_repo, signal_repo = service._get_session_and_repositories()

        # 진행 중인 결과들 조회 (최대 10개)
        query = """
        SELECT 
            so.id,
            so.signal_id,
            s.signal_type,
            s.symbol,
            s.created_at as signal_time,
            so.created_at as tracking_start,
            so.price_1h_after,
            so.price_4h_after,
            so.price_1d_after,
            so.price_1w_after,
            so.price_1m_after,
            so.is_complete
        FROM signal_outcomes so
        JOIN technical_signals s ON so.signal_id = s.id
        WHERE so.is_complete = FALSE
        ORDER BY so.created_at DESC
        LIMIT 10
        """

        result = session.execute(text(query))
        results = result.fetchall()

        if not results:
            print("✅ 진행 중인 결과가 없습니다!")
            return

        print(f"📋 진행 중인 결과 {len(results)}개:")
        print("-" * 80)

        for i, row in enumerate(results, 1):
            (
                outcome_id,
                signal_id,
                signal_type,
                symbol,
                signal_time,
                tracking_start,
                price_1h,
                price_4h,
                price_1d,
                price_1w,
                price_1m,
                is_complete,
            ) = row

            # 경과 시간 계산
            now = datetime.now(timezone.utc)
            if isinstance(signal_time, str):
                signal_time = datetime.fromisoformat(signal_time.replace("Z", "+00:00"))
            elif signal_time.tzinfo is None:
                signal_time = signal_time.replace(tzinfo=timezone.utc)

            elapsed_hours = (now - signal_time).total_seconds() / 3600

            print(f"[{i}] 결과 ID: {outcome_id}")
            print(f"    📊 신호: {signal_type} ({symbol})")
            print(f"    🕐 신호 시간: {signal_time}")
            print(f"    ⏰ 경과 시간: {elapsed_hours:.1f}시간")
            print(f"    💰 가격 추적:")
            print(f"        1시간 후: {'✅' if price_1h else '⏳'}")
            print(f"        4시간 후: {'✅' if price_4h else '⏳'}")
            print(f"        1일 후: {'✅' if price_1d else '⏳'}")
            print(f"        1주 후: {'✅' if price_1w else '⏳'}")
            print(f"        1달 후: {'✅' if price_1m else '⏳'}")
            print()

        # 시간대별 완료 통계
        print("📈 시간대별 완료 통계:")
        print("-" * 40)

        stats_query = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN price_1h_after IS NOT NULL THEN 1 ELSE 0 END) as has_1h,
            SUM(CASE WHEN price_4h_after IS NOT NULL THEN 1 ELSE 0 END) as has_4h,
            SUM(CASE WHEN price_1d_after IS NOT NULL THEN 1 ELSE 0 END) as has_1d,
            SUM(CASE WHEN price_1w_after IS NOT NULL THEN 1 ELSE 0 END) as has_1w,
            SUM(CASE WHEN price_1m_after IS NOT NULL THEN 1 ELSE 0 END) as has_1m
        FROM signal_outcomes 
        WHERE is_complete = FALSE
        """

        stats_result = session.execute(text(stats_query))
        total, has_1h, has_4h, has_1d, has_1w, has_1m = stats_result.fetchone()

        print(f"총 진행중: {total}개")
        print(f"1시간 후 완료: {has_1h}개 ({has_1h/total*100:.1f}%)")
        print(f"4시간 후 완료: {has_4h}개 ({has_4h/total*100:.1f}%)")
        print(f"1일 후 완료: {has_1d}개 ({has_1d/total*100:.1f}%)")
        print(f"1주 후 완료: {has_1w}개 ({has_1w/total*100:.1f}%)")
        print(f"1달 후 완료: {has_1m}개 ({has_1m/total*100:.1f}%)")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        traceback.print_exc()
    finally:
        # 세션 정리
        if "session" in locals():
            session.close()


if __name__ == "__main__":
    main()
