import os
import requests
from datetime import datetime, timezone, timedelta
from app.common.constants.symbol_names import (
    SYMBOL_CATEGORY_MAP,
    SYMBOL_NAME_MAP,
    SYMBOL_PRICE_MAP,
)
import traceback
import httpx


def format_time_with_kst(utc_time: datetime) -> str:
    """
    UTC 시간을 UTC + KST 형태로 포맷팅

    Args:
        utc_time: UTC 기준 datetime 객체

    Returns:
        "2025-01-16 14:30:15 UTC (23:30:15 KST)" 형태의 문자열
    """
    # UTC 시간 포맷팅
    utc_str = utc_time.strftime("%Y-%m-%d %H:%M:%S")

    # 한국 시간 계산 (UTC + 9시간)
    kst_time = utc_time + timedelta(hours=9)
    kst_str = kst_time.strftime("%H:%M:%S")

    return f"{utc_str} UTC ({kst_str} KST)"


# -----------------------------
# 🗞 뉴스 전송 함수
# -----------------------------


def send_news_telegram_message(
    title: str, summary: str, url: str, published_at: datetime, symbol: str
) -> None:
    display_name = SYMBOL_NAME_MAP.get(symbol, "알 수 없는 대상")
    published_str = (
        published_at.strftime("%Y-%m-%d %H:%M:%S") if published_at else "날짜 없음"
    )

    message = f"""📰 <b>{title}</b>

{summary or "요약 없음"}

📅 <i>{published_str}</i>
🔗 <a href="{url}">기사 보러가기</a>
"""
    _send_basic(symbol, message, is_news=True)


# -----------------------------
# 📈 가격 알림 메시지 함수들
# -----------------------------


def send_price_rise_message(
    symbol: str, current_price: float, prev_close: float, percent: float, now: datetime
):
    name = SYMBOL_PRICE_MAP.get(symbol, symbol)
    message = (
        f"📈 <b>{name}({symbol}) 전일 대비 상승!</b>\n\n"
        f"💵 현재가: {current_price:.2f}\n"
        f"📅 전일 종가: {prev_close:.2f}\n"
        f"📊 변동률: <b>+{percent:.2f}%</b>\n"
        f"🕒 {format_time_with_kst(now)}"
    )
    _send_basic(symbol, message)


def send_price_drop_message(
    symbol: str, current_price: float, prev_close: float, percent: float, now: datetime
):
    name = SYMBOL_PRICE_MAP.get(symbol, symbol)
    message = (
        f"📉 <b>{name}({symbol}) 전일 대비 하락!</b>\n\n"
        f"💵 현재가: {current_price:.2f}\n"
        f"📅 전일 종가: {prev_close:.2f}\n"
        f"📊 변동률: <b>{percent:.2f}%</b>\n"
        f"🕒 {format_time_with_kst(now)}"
    )
    _send_basic(symbol, message)


def send_break_previous_high(
    symbol: str, current_price: float, previous_high: float, now: datetime
):
    name = SYMBOL_PRICE_MAP.get(symbol, symbol)
    percent_gain = ((current_price - previous_high) / previous_high) * 100
    message = (
        f"🚨 <b>{name}({symbol}) 전일 고점 돌파!</b>\n\n"
        f"💵 현재가: {current_price:.2f}\n"
        f"🔺 전일 고점: {previous_high:.2f}\n"
        f"📊 돌파폭: <b>+{percent_gain:.2f}%</b>\n"
        f"🕒 돌파 시점: {format_time_with_kst(now)}"
    )
    _send_basic(symbol, message)


def send_break_previous_low(
    symbol: str, current_price: float, previous_low: float, now: datetime
):
    name = SYMBOL_PRICE_MAP.get(symbol, symbol)
    percent_drop = ((current_price - previous_low) / previous_low) * 100
    message = (
        f"⚠️ <b>{name}({symbol}) 전일 저점 하회!</b>\n\n"
        f"💵 현재가: {current_price:.2f}\n"
        f"🔻 전일 저점: {previous_low:.2f}\n"
        f"📊 하회폭: <b>{percent_drop:.2f}%</b>\n"
        f"🕒 하회 시점: {format_time_with_kst(now)}"
    )
    _send_basic(symbol, message)


def send_new_high_message(symbol: str, current_price: float, now: datetime):
    name = SYMBOL_PRICE_MAP.get(symbol, symbol)
    message = (
        f"🚀 <b>{name}({symbol}) 최고가 갱신!</b>\n\n"
        f"📈 새로운 최고가: <b>{current_price:.2f}</b>\n"
        f"🕒 갱신 시점: {format_time_with_kst(now)}"
    )
    _send_basic(symbol, message)


def send_drop_from_high_message(
    symbol: str,
    current_price: float,
    high_price: float,
    percent: float,
    now: datetime,
    high_recorded_at: datetime,
):
    name = SYMBOL_PRICE_MAP.get(symbol, symbol)
    message = (
        f"🔻 <b>{name}({symbol}) 최고가 대비 하락</b>\n\n"
        f"📉 현재가: {current_price:.2f}\n"
        f"📈 최고가: {high_price:.2f} ({format_time_with_kst(high_recorded_at)})\n"
        f"📊 낙폭: <b>{percent:.2f}%</b>\n"
        f"🕒 하락 시점: {format_time_with_kst(now)}"
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
        "disable_web_page_preview": False,
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


async def send_text_message_async(message: str):
    """📨 비동기로 텍스트 메시지를 텔레그램에 전송"""
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM 환경변수가 설정되지 않았습니다.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                print(
                    f"❌ 비동기 텔레그램 전송 실패: {response.status_code} - {response.text}"
                )
            else:
                print("📨 비동기 텔레그램 전송 완료")
        except Exception as e:
            print(f"❌ 비동기 텔레그램 전송 중 예외 발생: {e}")


# -----------------------------
# 📊 기술적 지표 알림 메시지 함수들
# -----------------------------


def send_ma_breakout_message(
    symbol: str,
    timeframe: str,
    ma_period: int,
    current_price: float,
    ma_value: float,
    signal_type: str,
    now: datetime,
):
    """
    이동평균선 돌파/이탈 알림

    Args:
        symbol: 심볼 (NQ=F, ^IXIC)
        timeframe: 시간대 (1min, 15min, 1day)
        ma_period: 이동평균 기간 (20, 50, 200)
        current_price: 현재 가격
        ma_value: 이동평균값
        signal_type: breakout_up(상향돌파) 또는 breakout_down(하향돌파)
        now: 신호 발생 시점 (UTC)
    """
    name = SYMBOL_PRICE_MAP.get(symbol, symbol)

    # 시간대별 표시명
    timeframe_name = {"1min": "1분봉", "15min": "15분봉", "1day": "일봉"}.get(
        timeframe, timeframe
    )

    # 신호 타입별 이모지와 메시지
    if signal_type == "breakout_up":
        emoji = "🚀"
        action = "상향 돌파"
        percent = ((current_price - ma_value) / ma_value) * 100
        percent_text = f"+{percent:.2f}%"
    else:  # breakout_down
        emoji = "📉"
        action = "하향 이탈"
        percent = ((current_price - ma_value) / ma_value) * 100
        percent_text = f"{percent:.2f}%"

    message = (
        f"{emoji} <b>{name}({symbol}) {ma_period}선 {action}!</b>\n\n"
        f"📊 시간대: {timeframe_name}\n"
        f"💵 현재가: {current_price:.2f}\n"
        f"📈 {ma_period}일선: {ma_value:.2f}\n"
        f"📊 돌파폭: <b>{percent_text}</b>\n"
        f"🕒 돌파 시점: {format_time_with_kst(now)}"
    )
    _send_basic(symbol, message)


def send_rsi_alert_message(
    symbol: str,
    timeframe: str,
    current_rsi: float,
    signal_type: str,
    now: datetime,
):
    """
    RSI 과매수/과매도 알림

    Args:
        symbol: 심볼
        timeframe: 시간대
        current_rsi: 현재 RSI 값
        signal_type: overbought, oversold, bullish, bearish
        now: 신호 발생 시점 (UTC)
    """
    name = SYMBOL_PRICE_MAP.get(symbol, symbol)

    timeframe_name = {"1min": "1분봉", "15min": "15분봉", "1day": "일봉"}.get(
        timeframe, timeframe
    )

    # 신호 타입별 메시지
    signal_info = {
        "overbought": {
            "emoji": "🔴",
            "title": "과매수 진입",
            "description": "RSI 70 돌파 → 조정 가능성",
            "action": "매도 고려",
        },
        "oversold": {
            "emoji": "🟢",
            "title": "과매도 진입",
            "description": "RSI 30 이탈 → 반등 가능성",
            "action": "매수 고려",
        },
        "bullish": {
            "emoji": "📈",
            "title": "상승 모멘텀",
            "description": "RSI 50 돌파 → 상승 추세",
            "action": "상승 추세 확인",
        },
        "bearish": {
            "emoji": "📉",
            "title": "하락 모멘텀",
            "description": "RSI 50 이탈 → 하락 추세",
            "action": "하락 추세 확인",
        },
    }

    info = signal_info.get(signal_type, signal_info["overbought"])

    message = (
        f"{info['emoji']} <b>{name}({symbol}) RSI {info['title']}!</b>\n\n"
        f"📊 시간대: {timeframe_name}\n"
        f"📈 현재 RSI: <b>{current_rsi:.1f}</b>\n"
        f"💡 의미: {info['description']}\n"
        f"🎯 전략: {info['action']}\n"
        f"🕒 신호 시점: {format_time_with_kst(now)}"
    )
    _send_basic(symbol, message)


def send_bollinger_alert_message(
    symbol: str,
    timeframe: str,
    current_price: float,
    upper_band: float,
    lower_band: float,
    signal_type: str,
    now: datetime,
):
    """
    볼린저 밴드 터치/돌파 알림

    Args:
        symbol: 심볼
        timeframe: 시간대
        current_price: 현재 가격
        upper_band: 상단 밴드
        lower_band: 하단 밴드
        signal_type: touch_upper, touch_lower, break_upper, break_lower
        now: 신호 발생 시점 (UTC)
    """
    name = SYMBOL_PRICE_MAP.get(symbol, symbol)

    timeframe_name = {"1min": "1분봉", "15min": "15분봉", "1day": "일봉"}.get(
        timeframe, timeframe
    )

    # 신호 타입별 메시지
    signal_info = {
        "touch_upper": {
            "emoji": "🔴",
            "title": "상단 밴드 터치",
            "description": "과매수 신호 → 조정 가능성",
            "band_price": upper_band,
            "band_name": "상단 밴드",
        },
        "touch_lower": {
            "emoji": "🟢",
            "title": "하단 밴드 터치",
            "description": "과매도 신호 → 반등 가능성",
            "band_price": lower_band,
            "band_name": "하단 밴드",
        },
        "break_upper": {
            "emoji": "🚀",
            "title": "상단 밴드 돌파",
            "description": "강한 상승 신호 → 추가 상승 기대",
            "band_price": upper_band,
            "band_name": "상단 밴드",
        },
        "break_lower": {
            "emoji": "💥",
            "title": "하단 밴드 이탈",
            "description": "강한 하락 신호 → 추가 하락 우려",
            "band_price": lower_band,
            "band_name": "하단 밴드",
        },
    }

    info = signal_info.get(signal_type, signal_info["touch_upper"])

    message = (
        f"{info['emoji']} <b>{name}({symbol}) 볼린저 {info['title']}!</b>\n\n"
        f"📊 시간대: {timeframe_name}\n"
        f"💵 현재가: {current_price:.2f}\n"
        f"📈 {info['band_name']}: {info['band_price']:.2f}\n"
        f"💡 의미: {info['description']}\n"
        f"🕒 신호 시점: {format_time_with_kst(now)}"
    )
    _send_basic(symbol, message)


def send_golden_cross_message(
    symbol: str,
    ma_50: float,
    ma_200: float,
    now: datetime,
):
    """
    골든크로스 알림 (50일선이 200일선 상향돌파)

    Args:
        symbol: 심볼
        ma_50: 50일 이동평균값
        ma_200: 200일 이동평균값
        now: 신호 발생 시점 (UTC)
    """
    name = SYMBOL_PRICE_MAP.get(symbol, symbol)

    # 50일선이 200일선보다 얼마나 위에 있는지 계산
    percent_diff = ((ma_50 - ma_200) / ma_200) * 100

    message = (
        f"🚀 <b>{name}({symbol}) 골든크로스 발생!</b>\n\n"
        f"📊 시간대: 일봉\n"
        f"📈 50일선: {ma_50:.2f}\n"
        f"📈 200일선: {ma_200:.2f}\n"
        f"📊 차이: <b>+{percent_diff:.2f}%</b>\n"
        f"💡 의미: 강력한 상승 신호! 장기 상승 추세 시작 가능성\n"
        f"🎯 전략: 매수 포지션 고려\n"
        f"🕒 발생 시점: {format_time_with_kst(now)}"
    )
    _send_basic(symbol, message)


def send_dead_cross_message(
    symbol: str,
    ma_50: float,
    ma_200: float,
    now: datetime,
):
    """
    데드크로스 알림 (50일선이 200일선 하향이탈)

    Args:
        symbol: 심볼
        ma_50: 50일 이동평균값
        ma_200: 200일 이동평균값
        now: 신호 발생 시점 (UTC)
    """
    name = SYMBOL_PRICE_MAP.get(symbol, symbol)

    # 50일선이 200일선보다 얼마나 아래에 있는지 계산
    percent_diff = ((ma_50 - ma_200) / ma_200) * 100

    message = (
        f"💀 <b>{name}({symbol}) 데드크로스 발생!</b>\n\n"
        f"📊 시간대: 일봉\n"
        f"📉 50일선: {ma_50:.2f}\n"
        f"📈 200일선: {ma_200:.2f}\n"
        f"📊 차이: <b>{percent_diff:.2f}%</b>\n"
        f"💡 의미: 강력한 하락 신호! 장기 하락 추세 시작 가능성\n"
        f"🎯 전략: 매도 포지션 고려\n"
        f"🕒 발생 시점: {format_time_with_kst(now)}"
    )
    _send_basic(symbol, message)
