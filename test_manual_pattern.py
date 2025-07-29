#!/usr/bin/env python3
"""
수동 패턴 생성 테스트

서버 환경에서 직접 패턴 생성 함수를 호출합니다.
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_pattern_creation():
    """패턴 생성 테스트"""
    print("🔍 수동 패턴 생성 테스트 시작...")

    try:
        # 스케줄러 함수 직접 호출
        from app.scheduler.scheduler_runner import run_pattern_discovery

        print("📊 패턴 발견 함수 실행 중...")
        run_pattern_discovery()

        print("✅ 패턴 생성 테스트 완료!")

    except Exception as e:
        print(f"❌ 패턴 생성 실패: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_pattern_creation()
