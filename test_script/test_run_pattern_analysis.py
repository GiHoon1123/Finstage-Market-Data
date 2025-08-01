#!/usr/bin/env python3
"""
과거 신호 패턴 분석 실행 스크립트

사용법:
    python run_pattern_analysis.py

이 스크립트는 scripts/historical_pattern_analysis.py를 실행합니다.
"""

import subprocess
import sys
import os


def main():
    """패턴 분석 스크립트 실행"""
    print("🚀 과거 신호 패턴 분석 시작...")

    try:
        # 스크립트 경로
        script_path = os.path.join("scripts", "historical_pattern_analysis.py")

        # Python 스크립트 실행
        result = subprocess.run(
            [sys.executable, script_path], capture_output=True, text=True
        )

        # 출력 결과 표시
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        # 종료 코드 반환
        sys.exit(result.returncode)

    except Exception as e:
        print(f"❌ 스크립트 실행 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
