#!/usr/bin/env python3
"""
텔레그램 전송 테스트 스크립트
"""

import os
from dotenv import load_dotenv
from app.common.utils.telegram_notifier import send_telegram_message

# 환경변수 로드
mode = os.getenv("ENV_MODE", "dev")
env_file = f".env.{mode}"
load_dotenv(dotenv_path=env_file)

print(f"🔍 ENV_MODE: {mode}")
print(f"🔍 env_file: {env_file}")
print(
    f"🔍 TELEGRAM_BOT_TOKEN: {os.getenv('TELEGRAM_BOT_TOKEN')[:20] if os.getenv('TELEGRAM_BOT_TOKEN') else 'None'}..."
)
print(f"🔍 TELEGRAM_CHAT_ID: {os.getenv('TELEGRAM_CHAT_ID')}")

# 테스트 메시지 전송
test_message = """🧪 텔레그램 연결 테스트

이 메시지가 보이면 텔레그램 연결이 정상 작동 중입니다!

📅 테스트 시간: 2025-07-29 08:31
🔧 테스트 목적: 일일 리포트 시스템 검증"""

print("📨 테스트 메시지 전송 중...")
send_telegram_message(test_message)
print("✅ 테스트 완료")
