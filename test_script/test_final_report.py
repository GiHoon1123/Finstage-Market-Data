#!/usr/bin/env python3
"""
최종 리포트 테스트
"""

import os
from dotenv import load_dotenv

# 테스트 환경 설정
os.environ["ENV_MODE"] = "test"
mode = os.getenv("ENV_MODE", "test")
env_file = f".env.{mode}"
load_dotenv(dotenv_path=env_file)

from app.technical_analysis.service.daily_comprehensive_report_service import (
    DailyComprehensiveReportService,
)

print("🚀 최종 일일 리포트 테스트")
print("=" * 50)

try:
    service = DailyComprehensiveReportService()

    print("📊 리포트 생성 중...")
    result = service.generate_daily_report()

    if "error" in result:
        print(f"❌ 리포트 생성 실패: {result['error']}")
    else:
        print("✅ 리포트 생성 성공!")
        print(f"   - 메시지 길이: {result['message_length']}자")
        print(f"   - 분석 모듈: {result['analysis_modules']}")
        print(f"   - 생성 시간: {result['timestamp']}")

        # 각 모듈별 상태 확인
        modules = result["analysis_modules"]
        print("\n📋 모듈별 상태:")
        print(f"   - 백테스팅: {modules['backtesting']}개 심볼 분석")
        print(f"   - 패턴 분석: {modules['patterns']}개 심볼 분석")
        print(f"   - 머신러닝: {modules['ml_analysis']}개 심볼 분석")
        print(f"   - 투자 인사이트: {modules['insights']}개 항목")

        print("\n🎉 모든 기능이 정상 작동합니다!")

except Exception as e:
    print(f"❌ 테스트 실패: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 50)
print("테스트 완료")
