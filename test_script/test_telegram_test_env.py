#!/usr/bin/env python3
"""
테스트 환경에서 텔레그램 전송 테스트
"""

import os
from dotenv import load_dotenv

# 테스트 환경 설정
os.environ["ENV_MODE"] = "test"
mode = os.getenv("ENV_MODE", "test")
env_file = f".env.{mode}"
load_dotenv(dotenv_path=env_file)

print(f"🔍 ENV_MODE: {mode}")
print(f"🔍 env_file: {env_file}")
print(
    f"🔍 TELEGRAM_BOT_TOKEN: {os.getenv('TELEGRAM_BOT_TOKEN')[:20] if os.getenv('TELEGRAM_BOT_TOKEN') else 'None'}..."
)
print(f"🔍 TELEGRAM_CHAT_ID: {os.getenv('TELEGRAM_CHAT_ID')}")

from app.common.utils.telegram_notifier import send_telegram_message

# 테스트 메시지 전송
test_message = """🧪 테스트 환경 텔레그램 연결 테스트

이 메시지가 보이면 테스트 환경에서 텔레그램 연결이 정상 작동 중입니다!

📅 테스트 시간: 2025-07-29 08:36
🔧 테스트 목적: 테스트 환경 일일 리포트 시스템 검증
🌐 환경: ENV_MODE=test"""

print("📨 테스트 환경에서 메시지 전송 중...")
send_telegram_message(test_message)
print("✅ 테스트 완료")

# 일일 리포트도 테스트
print("\n📊 테스트 환경에서 일일 리포트 생성 테스트...")
from app.technical_analysis.service.daily_comprehensive_report_service import (
    DailyComprehensiveReportService,
)

try:
    service = DailyComprehensiveReportService()
    result = service.generate_daily_report()
    print(f"리포트 생성 결과: {result}")
except Exception as e:
    print(f"❌ 리포트 생성 실패: {e}")
    import traceback

    traceback.print_exc()
