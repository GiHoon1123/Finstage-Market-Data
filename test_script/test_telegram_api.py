#!/usr/bin/env python3
"""
텔레그램 API 테스트 스크립트

이 스크립트는 텔레그램 API를 직접 호출하여 알림 기능을 테스트합니다.
환경 변수 설정 및 API 연결 상태를 확인할 수 있습니다.
"""

import os
import sys
import requests
from datetime import datetime

# 상위 디렉토리를 파이썬 경로에 추가 (상대 임포트를 위해)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_telegram_env():
    """텔레그램 환경 변수 설정을 확인합니다."""
    print("🔍 텔레그램 환경 변수 확인 중...")

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token:
        print("❌ TELEGRAM_BOT_TOKEN이 설정되지 않았습니다.")
        return False

    if not chat_id:
        print("❌ TELEGRAM_CHAT_ID가 설정되지 않았습니다.")
        return False

    print(f"✅ 텔레그램 환경 변수 설정 확인 완료!")
    print(f"   - 봇 토큰: {token[:5]}...{token[-5:]}")
    print(f"   - 채팅 ID: {chat_id}")

    return True


def send_test_message():
    """간단한 테스트 메시지를 텔레그램으로 전송합니다."""
    print("📤 테스트 메시지 전송 중...")

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("❌ 환경 변수가 설정되지 않았습니다.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"""🧪 <b>텔레그램 API 테스트</b>

이 메시지는 텔레그램 API 연결을 테스트하기 위해 전송되었습니다.

⏰ 전송 시간: {now}
🖥️ 호스트: {os.uname().nodename}
🔧 환경: {os.getenv('ENV_MODE', '알 수 없음')}

✅ 텔레그램 API가 정상적으로 작동 중입니다!
"""

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        response = requests.post(url, data=payload)

        if response.status_code == 200:
            print("✅ 테스트 메시지 전송 성공!")
            print(f"   응답: {response.json()}")
            return True
        else:
            print(f"❌ 테스트 메시지 전송 실패: {response.status_code}")
            print(f"   응답: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 테스트 메시지 전송 중 오류 발생: {e}")
        return False


def check_bot_info():
    """봇 정보를 확인합니다."""
    print("🤖 봇 정보 확인 중...")

    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        print("❌ TELEGRAM_BOT_TOKEN이 설정되지 않았습니다.")
        return False

    url = f"https://api.telegram.org/bot{token}/getMe"

    try:
        response = requests.get(url)

        if response.status_code == 200:
            bot_info = response.json()["result"]
            print("✅ 봇 정보 확인 성공!")
            print(f"   - 봇 이름: {bot_info['first_name']}")
            print(f"   - 사용자명: @{bot_info['username']}")
            print(f"   - 봇 ID: {bot_info['id']}")
            return True
        else:
            print(f"❌ 봇 정보 확인 실패: {response.status_code}")
            print(f"   응답: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 봇 정보 확인 중 오류 발생: {e}")
        return False


def main():
    """메인 함수"""
    print("🚀 텔레그램 API 테스트 시작...")

    # 환경 변수 확인
    if not check_telegram_env():
        print("❌ 환경 변수 설정을 확인하세요.")
        sys.exit(1)

    # 봇 정보 확인
    if not check_bot_info():
        print("❌ 봇 정보를 확인할 수 없습니다. 토큰이 유효한지 확인하세요.")
        sys.exit(1)

    # 테스트 메시지 전송
    if not send_test_message():
        print("❌ 테스트 메시지 전송에 실패했습니다.")
        sys.exit(1)

    print("🎉 모든 텔레그램 API 테스트가 성공적으로 완료되었습니다!")


if __name__ == "__main__":
    main()
