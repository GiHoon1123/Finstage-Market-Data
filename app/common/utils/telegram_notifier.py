import os
import requests
from datetime import datetime
from app.common.constants.symbol_names import SYMBOL_CATEGORY_MAP, SYMBOL_NAME_MAP, SYMBOL_PRICE_MAP
import traceback


# -----------------------------
# 🗞 뉴스 전송 함수
# -----------------------------

def send_news_telegram_message(title: str, summary: str, url: str, published_at: datetime, symbol: str) -> None:
    display_name = SYMBOL_NAME_MAP.get(symbol, "알 수 없는 대상")
    published_str = published_at.strftime("%Y-%m-%d %H:%M:%S") if published_at else "날짜 없음"

    message = f"""📰 <b>{title}</b>

{summary or "요약 없음"}

📅 <i>{published_str}</i>
🔗 <a href="{url}">기사 보러가기</a>
"""
    _send_basic(symbol, message, is_news=True)


# -----------------------------
# 📈 가격 알림 메시지 함수들
# -----------------------------

def send_price_rise_message(symbol: str, current_price: float, prev_close: float, percent: float, now: datetime):
    name = SYMBOL_PRICE_MAP.get(symbol, symbol)
    message = (
        f"📈 <b>{name}({symbol}) 전일 대비 상승!</b>\n\n"
        f"💵 현재가: {current_price:.2f}\n"
        f"📅 전일 종가: {prev_close:.2f}\n"
        f"📊 변동률: <b>+{percent:.2f}%</b>\n"
        f"🕒 {now.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    _send_basic(symbol, message)


def send_price_drop_message(symbol: str, current_price: float, prev_close: float, percent: float, now: datetime):
    name = SYMBOL_PRICE_MAP.get(symbol, symbol)
    message = (
        f"📉 <b>{name}({symbol}) 전일 대비 하락!</b>\n\n"
        f"💵 현재가: {current_price:.2f}\n"
        f"📅 전일 종가: {prev_close:.2f}\n"
        f"📊 변동률: <b>{percent:.2f}%</b>\n"
        f"🕒 {now.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    _send_basic(symbol, message)


def send_new_high_message(symbol: str, current_price: float, now: datetime):
    name = SYMBOL_PRICE_MAP.get(symbol, symbol)
    message = (
        f"🚀 <b>{name}({symbol}) 최고가 갱신!</b>\n\n"
        f"📈 새로운 최고가: <b>{current_price:.2f}</b>\n"
        f"🕒 {now.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    _send_basic(symbol, message)


def send_drop_from_high_message(symbol: str, current_price: float, high_price: float, percent: float, now: datetime):
    name = SYMBOL_PRICE_MAP.get(symbol, symbol)
    message = (
        f"🔻 <b>{name}({symbol}) 최고가 대비 하락</b>\n\n"
        f"📉 현재가: {current_price:.2f}\n"
        f"📈 최고가: {high_price:.2f}\n"
        f"📊 낙폭: <b>{percent:.2f}%</b>\n"
        f"🕒 {now.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    _send_basic(symbol, message)


# -----------------------------
# 공통 전송 함수
# -----------------------------

def _send_basic(symbol: str, message: str, is_news: bool = False):
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM 환경변수가 설정되지 않았습니다.")
        return

    display_name = SYMBOL_NAME_MAP.get(symbol, symbol)
    category = SYMBOL_CATEGORY_MAP.get(symbol, "기타")
    prefix = "🗞️" if is_news else "📌"
    header = f"{prefix} <b>[{symbol}] {display_name} ({category})</b>\n\n"

    full_message = header + message

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": full_message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"❌ 텔레그램 전송 실패: {response.status_code} - {response.text}")
        else:
            print(f"📨 텔레그램 전송 완료: {symbol}")
    except Exception as e:
        print(f"❌ 텔레그램 전송 중 예외 발생: {e}")
        traceback.print_exc()
