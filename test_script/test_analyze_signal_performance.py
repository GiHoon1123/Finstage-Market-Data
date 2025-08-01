#!/usr/bin/env python3
"""
신호 성과 분석 스크립트
"""

import os
import sys
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
    print("📊 신호 성과 분석")
    print("=" * 50)

    service = EnhancedOutcomeTrackingService()

    try:
        # 데이터베이스 연결 및 리포지토리 준비
        session, outcome_repo, signal_repo = service._get_session_and_repositories()

        # 1. 신호 타입별 성과 분석
        print("🎯 신호 타입별 성과 분석 (완료된 결과만):")
        print("-" * 60)

        performance_query = """
        SELECT 
            s.signal_type,
            COUNT(*) as total_signals,
            AVG(so.return_1h) as avg_return_1h,
            AVG(so.return_4h) as avg_return_4h,
            AVG(so.return_1d) as avg_return_1d,
            AVG(so.return_1w) as avg_return_1w,
            SUM(CASE WHEN so.return_1h > 0 THEN 1 ELSE 0 END) as positive_1h,
            SUM(CASE WHEN so.return_1d > 0 THEN 1 ELSE 0 END) as positive_1d,
            SUM(CASE WHEN so.return_1w > 0 THEN 1 ELSE 0 END) as positive_1w
        FROM signal_outcomes so
        JOIN technical_signals s ON so.signal_id = s.id
        WHERE so.is_complete = TRUE
        GROUP BY s.signal_type
        ORDER BY avg_return_1d DESC
        LIMIT 15
        """

        result = session.execute(text(performance_query))
        performances = result.fetchall()

        for perf in performances:
            (
                signal_type,
                total,
                avg_1h,
                avg_4h,
                avg_1d,
                avg_1w,
                pos_1h,
                pos_1d,
                pos_1w,
            ) = perf

            print(f"📈 {signal_type}")
            print(f"   총 신호: {total}개")
            print(f"   평균 수익률:")
            print(f"     1시간: {float(avg_1h or 0):.2f}%")
            print(f"     4시간: {float(avg_4h or 0):.2f}%")
            print(f"     1일: {float(avg_1d or 0):.2f}%")
            print(f"     1주: {float(avg_1w or 0):.2f}%")
            print(f"   성공률:")
            print(f"     1시간: {pos_1h}/{total} ({pos_1h/total*100:.1f}%)")
            print(f"     1일: {pos_1d}/{total} ({pos_1d/total*100:.1f}%)")
            if pos_1w > 0:
                print(f"     1주: {pos_1w}/{total} ({pos_1w/total*100:.1f}%)")
            print()

        # 2. 심볼별 성과 분석
        print("🏢 심볼별 성과 분석 (상위 10개):")
        print("-" * 50)

        symbol_query = """
        SELECT 
            s.symbol,
            COUNT(*) as total_signals,
            AVG(so.return_1d) as avg_return_1d,
            SUM(CASE WHEN so.return_1d > 0 THEN 1 ELSE 0 END) as positive_1d
        FROM signal_outcomes so
        JOIN technical_signals s ON so.signal_id = s.id
        WHERE so.is_complete = TRUE AND so.return_1d IS NOT NULL
        GROUP BY s.symbol
        HAVING COUNT(*) >= 10
        ORDER BY avg_return_1d DESC
        LIMIT 10
        """

        symbol_result = session.execute(text(symbol_query))
        symbols = symbol_result.fetchall()

        for sym in symbols:
            symbol, total, avg_return, positive = sym
            print(
                f"📊 {symbol}: {float(avg_return):.2f}% (성공률: {positive}/{total} = {positive/total*100:.1f}%)"
            )

        # 3. 최근 성과 트렌드
        print("\n📅 최근 7일간 일별 성과:")
        print("-" * 40)

        trend_query = """
        SELECT 
            DATE(s.created_at) as signal_date,
            COUNT(*) as total_signals,
            AVG(so.return_1d) as avg_return_1d,
            SUM(CASE WHEN so.return_1d > 0 THEN 1 ELSE 0 END) as positive_signals
        FROM signal_outcomes so
        JOIN technical_signals s ON so.signal_id = s.id
        WHERE so.is_complete = TRUE 
        AND so.return_1d IS NOT NULL
        AND s.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        GROUP BY DATE(s.created_at)
        ORDER BY signal_date DESC
        """

        trend_result = session.execute(text(trend_query))
        trends = trend_result.fetchall()

        for trend in trends:
            date, total, avg_return, positive = trend
            success_rate = positive / total * 100 if total > 0 else 0
            print(
                f"{date}: {total}개 신호, 평균 {float(avg_return or 0):.2f}%, 성공률 {success_rate:.1f}%"
            )

        # 4. 극단적 성과 분석
        print("\n🎯 극단적 성과 분석:")
        print("-" * 30)

        extreme_query = """
        SELECT 
            s.signal_type,
            s.symbol,
            so.return_1d,
            s.created_at
        FROM signal_outcomes so
        JOIN technical_signals s ON so.signal_id = s.id
        WHERE so.is_complete = TRUE AND so.return_1d IS NOT NULL
        ORDER BY so.return_1d DESC
        LIMIT 5
        """

        extreme_result = session.execute(text(extreme_query))
        extremes = extreme_result.fetchall()

        print("🚀 최고 성과 5개:")
        for i, ext in enumerate(extremes, 1):
            signal_type, symbol, return_1d, created_at = ext
            print(
                f"  {i}. {signal_type} ({symbol}): +{float(return_1d):.2f}% @ {created_at}"
            )

        # 최악 성과
        worst_query = """
        SELECT 
            s.signal_type,
            s.symbol,
            so.return_1d,
            s.created_at
        FROM signal_outcomes so
        JOIN technical_signals s ON so.signal_id = s.id
        WHERE so.is_complete = TRUE AND so.return_1d IS NOT NULL
        ORDER BY so.return_1d ASC
        LIMIT 5
        """

        worst_result = session.execute(text(worst_query))
        worsts = worst_result.fetchall()

        print("\n📉 최악 성과 5개:")
        for i, worst in enumerate(worsts, 1):
            signal_type, symbol, return_1d, created_at = worst
            print(
                f"  {i}. {signal_type} ({symbol}): {float(return_1d):.2f}% @ {created_at}"
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
