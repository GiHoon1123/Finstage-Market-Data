#!/usr/bin/env python3
"""
리포트 서비스 텔레그램 전송 테스트
"""

import os
from dotenv import load_dotenv

# 환경변수 로드
mode = os.getenv("ENV_MODE", "dev")
env_file = f".env.{mode}"
load_dotenv(dotenv_path=env_file)

from app.technical_analysis.service.daily_comprehensive_report_service import (
    DailyComprehensiveReportService,
)

print("🧪 리포트 서비스 텔레그램 전송 테스트")

# 서비스 인스턴스 생성
service = DailyComprehensiveReportService()

# 간단한 테스트 메시지 생성
test_message = """🧪 리포트 서비스 테스트

이 메시지는 DailyComprehensiveReportService에서 직접 전송한 테스트 메시지입니다.

📅 테스트 시간: 2025-07-29 08:33
🔧 목적: 리포트 서비스 내 텔레그램 전송 기능 검증"""

print("📨 리포트 서비스에서 텔레그램 전송 중...")

# 텔레그램 전송 함수 직접 호출
from app.common.utils.telegram_notifier import send_telegram_message

send_telegram_message(test_message)

print("✅ 테스트 완료")

# 실제 리포트 생성도 테스트
print("\n📊 실제 리포트 생성 테스트...")
try:
    result = service.generate_daily_report()
    print(f"리포트 생성 결과: {result}")
except Exception as e:
    print(f"❌ 리포트 생성 실패: {e}")
    import traceback

    traceback.print_exc()
