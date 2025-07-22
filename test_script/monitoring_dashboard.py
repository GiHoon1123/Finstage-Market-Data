#!/usr/bin/env python3
"""
실시간 모니터링 대시보드
"""

import os
import sys
import time
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


def clear_screen():
    """화면을 지웁니다"""
    os.system("clear" if os.name == "posix" else "cls")


def get_dashboard_data(session):
    """대시보드 데이터를 가져옵니다"""

    # 1. 전체 통계
    stats_query = """
    SELECT 
        COUNT(*) as total_outcomes,
        SUM(CASE WHEN is_complete = TRUE THEN 1 ELSE 0 END) as completed,
        SUM(CASE WHEN is_complete = FALSE THEN 1 ELSE 0 END) as pending,
        AVG(CASE WHEN is_complete = TRUE THEN return_1d END) as avg_return_1d
    FROM signal_outcomes
    """

    stats_result = session.execute(text(stats_query))
    total, completed, pending, avg_return = stats_result.fetchone()

    # 2. 최근 신호 (5개)
    recent_query = """
    SELECT 
        s.signal_type,
        s.symbol,
        s.current_price,
        s.created_at,
        so.return_1d,
        so.is_complete
    FROM technical_signals s
    LEFT JOIN signal_outcomes so ON s.id = so.signal_id
    ORDER BY s.created_at DESC
    LIMIT 5
    """

    recent_result = session.execute(text(recent_query))
    recent_signals = recent_result.fetchall()

    # 3. 최고 성과 신호 (3개)
    top_query = """
    SELECT 
        s.signal_type,
        s.symbol,
        so.return_1d,
        s.created_at
    FROM signal_outcomes so
    JOIN technical_signals s ON so.signal_id = s.id
    WHERE so.is_complete = TRUE AND so.return_1d IS NOT NULL
    ORDER BY so.return_1d DESC
    LIMIT 3
    """

    top_result = session.execute(text(top_query))
    top_performers = top_result.fetchall()

    # 4. 진행 중인 추적 상태
    tracking_query = """
    SELECT 
        SUM(CASE WHEN price_1h_after IS NOT NULL THEN 1 ELSE 0 END) as has_1h,
        SUM(CASE WHEN price_4h_after IS NOT NULL THEN 1 ELSE 0 END) as has_4h,
        SUM(CASE WHEN price_1d_after IS NOT NULL THEN 1 ELSE 0 END) as has_1d,
        SUM(CASE WHEN price_1w_after IS NOT NULL THEN 1 ELSE 0 END) as has_1w,
        SUM(CASE WHEN price_1m_after IS NOT NULL THEN 1 ELSE 0 END) as has_1m
    FROM signal_outcomes
    WHERE is_complete = FALSE
    """

    tracking_result = session.execute(text(tracking_query))
    tracking_stats = tracking_result.fetchone()

    return {
        "stats": {
            "total": total,
            "completed": completed,
            "pending": pending,
            "avg_return": avg_return,
        },
        "recent_signals": recent_signals,
        "top_performers": top_performers,
        "tracking_stats": tracking_stats,
    }


def display_dashboard(data):
    """대시보드를 화면에 표시합니다"""

    print("🚀 기술적 분석 결과 추적 대시보드")
    print("=" * 80)
    print(f"📅 업데이트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 전체 통계
    stats = data["stats"]
    completion_rate = (
        (stats["completed"] / stats["total"] * 100) if stats["total"] > 0 else 0
    )
    avg_return = stats["avg_return"] or 0

    print("📊 전체 통계")
    print("-" * 40)
    print(f"총 결과 추적: {stats['total']:,}개")
    print(f"완료: {stats['completed']:,}개 ({completion_rate:.1f}%)")
    print(f"진행중: {stats['pending']:,}개")
    print(f"평균 1일 수익률: {float(avg_return):.2f}%")
    print()

    # 진행 중인 추적 상태
    tracking = data["tracking_stats"]
    pending = stats["pending"]

    if pending > 0:
        print("⏳ 진행 중인 추적 상태")
        print("-" * 40)
        print(f"1시간 후: {tracking[0]}/{pending} ({tracking[0]/pending*100:.1f}%)")
        print(f"4시간 후: {tracking[1]}/{pending} ({tracking[1]/pending*100:.1f}%)")
        print(f"1일 후: {tracking[2]}/{pending} ({tracking[2]/pending*100:.1f}%)")
        print(f"1주 후: {tracking[3]}/{pending} ({tracking[3]/pending*100:.1f}%)")
        print(f"1달 후: {tracking[4]}/{pending} ({tracking[4]/pending*100:.1f}%)")
        print()

    # 최근 신호
    print("🔔 최근 신호 (5개)")
    print("-" * 60)
    for signal in data["recent_signals"]:
        signal_type, symbol, price, created_at, return_1d, is_complete = signal
        status = "✅ 완료" if is_complete else "⏳ 진행중"
        return_str = f"{float(return_1d):.2f}%" if return_1d else "계산중"

        print(f"{signal_type} ({symbol})")
        print(f"  💰 ${float(price or 0):.2f} | {status} | 수익률: {return_str}")
        print(f"  🕐 {created_at}")
        print()

    # 최고 성과
    print("🏆 최고 성과 신호 (3개)")
    print("-" * 50)
    for i, performer in enumerate(data["top_performers"], 1):
        signal_type, symbol, return_1d, created_at = performer
        print(f"{i}. {signal_type} ({symbol}): +{float(return_1d):.2f}%")
        print(f"   📅 {created_at}")
        print()

    print("=" * 80)
    print("🔄 자동 새로고침 중... (Ctrl+C로 종료)")


def main():
    """메인 함수"""
    print("🚀 모니터링 대시보드 시작...")

    service = EnhancedOutcomeTrackingService()

    try:
        while True:
            try:
                # 데이터베이스 연결
                session, _, _ = service._get_session_and_repositories()

                # 데이터 가져오기
                data = get_dashboard_data(session)

                # 화면 지우고 대시보드 표시
                clear_screen()
                display_dashboard(data)

                # 세션 정리
                session.close()

                # 30초 대기
                time.sleep(30)

            except KeyboardInterrupt:
                print("\n👋 대시보드를 종료합니다.")
                break
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                time.sleep(10)  # 오류 시 10초 대기 후 재시도

    except KeyboardInterrupt:
        print("\n👋 대시보드를 종료합니다.")
    finally:
        # 정리
        pass


if __name__ == "__main__":
    main()
