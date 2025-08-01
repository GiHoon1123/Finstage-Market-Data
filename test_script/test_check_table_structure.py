#!/usr/bin/env python3
"""
테이블 구조 확인 스크립트
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
    print("🔍 테이블 구조 확인")
    print("=" * 50)

    service = EnhancedOutcomeTrackingService()

    try:
        # 데이터베이스 연결 및 리포지토리 준비
        session, outcome_repo, signal_repo = service._get_session_and_repositories()

        # signal_outcomes 테이블 구조 확인
        print("📊 signal_outcomes 테이블 구조:")
        print("-" * 40)

        describe_query = "DESCRIBE signal_outcomes"
        result = session.execute(text(describe_query))
        columns = result.fetchall()

        for column in columns:
            print(f"  {column[0]} - {column[1]}")

        print("\n📊 technical_signals 테이블 구조:")
        print("-" * 40)

        describe_query2 = "DESCRIBE technical_signals"
        result2 = session.execute(text(describe_query2))
        columns2 = result2.fetchall()

        for column in columns2:
            print(f"  {column[0]} - {column[1]}")

        # 샘플 데이터 확인
        print("\n📋 signal_outcomes 샘플 데이터 (5개):")
        print("-" * 50)

        sample_query = "SELECT * FROM signal_outcomes LIMIT 5"
        sample_result = session.execute(text(sample_query))
        samples = sample_result.fetchall()

        for i, sample in enumerate(samples, 1):
            print(f"[{i}] {sample}")

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
