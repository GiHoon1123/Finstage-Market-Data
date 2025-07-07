import os
import requests
from datetime import datetime


def send_telegram_message(title: str, summary: str, url: str, published_at: datetime) -> None:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM 환경변수가 설정되지 않았습니다.")
        return

    # 날짜 문자열 포맷팅
    published_str = published_at.strftime("%Y-%m-%d %H:%M:%S") if published_at else "날짜 없음"

    # 텔레그램 메시지 HTML 템플릿
    message = f"""📰 <b>{title}</b>

{summary or "요약 없음"}

📅 <i>{published_str}</i>
🔗 <a href="{url}">기사 보러가기</a>
"""

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"❌ 텔레그램 전송 실패: {response.status_code} - {response.text}")
        else:
            print(f"📨 텔레그램 전송 완료: {title}")
    except Exception as e:
        print(f"❌ 텔레그램 전송 중 예외 발생: {e}")
