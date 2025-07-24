"""
테스트용 API 라우터

이 파일은 테스트 목적으로 사용되는 API 엔드포인트들을 정의합니다.
개발 및 디버깅 과정에서 유용하게 사용할 수 있습니다.
"""

from fastapi import APIRouter, HTTPException, Query, Path
from typing import Dict, Any, List, Optional

from app.technical_analysis.service.technical_monitor_service import (
    TechnicalMonitorService,
)
from app.common.utils.telegram_notifier import (
    send_ma_breakout_message,
    send_rsi_alert_message,
    send_bollinger_alert_message,
    send_golden_cross_message,
    send_dead_cross_message,
)
from datetime import datetime

# 라우터 생성
router = APIRouter()


@router.post("/telegram-alerts/all", summary="모든 텔레그램 알림 테스트")
async def test_all_alerts():
    """
    모든 유형의 텔레그램 알림을 테스트합니다.

    이 엔드포인트는 TechnicalMonitorService의 test_all_technical_alerts 메서드를 호출하여
    다양한 유형의 기술적 분석 알림을 테스트합니다.
    """
    try:
        service = TechnicalMonitorService()
        service.test_all_technical_alerts()

        return {
            "success": True,
            "message": "모든 텔레그램 알림 테스트가 성공적으로 실행되었습니다.",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 테스트 실패: {str(e)}")


@router.post("/telegram-alerts/ma-breakout", summary="이동평균선 돌파 알림 테스트")
async def test_ma_breakout_alert(
    symbol: str = Query("^IXIC", description="심볼 (예: ^IXIC, ^GSPC)"),
    ma_period: int = Query(
        200, description="이동평균 기간 (예: 5, 10, 21, 50, 100, 200)"
    ),
    ma_type: str = Query("SMA", description="이동평균 유형 (SMA, EMA)"),
    direction: str = Query("up", description="돌파 방향 (up 또는 down)"),
):
    """
    이동평균선 돌파 알림을 테스트합니다.

    Args:
        symbol: 심볼 (예: ^IXIC, ^GSPC)
        ma_period: 이동평균 기간 (예: 50, 200)
        direction: 돌파 방향 (up 또는 down)
    """
    try:
        now = datetime.utcnow()

        # 방향에 따라 가격과 이동평균값 설정
        if direction == "up":
            current_price = 20950.50 if symbol == "^IXIC" else 6350.75
            ma_value = 20900.25 if symbol == "^IXIC" else 6300.50
            signal_type = "breakout_up"
        else:
            current_price = 20850.50 if symbol == "^IXIC" else 6250.75
            ma_value = 20900.25 if symbol == "^IXIC" else 6300.50
            signal_type = "breakout_down"

        # 알림 전송
        send_ma_breakout_message(
            symbol=symbol,
            timeframe="1day",
            ma_period=ma_period,
            current_price=current_price,
            ma_value=ma_value,
            signal_type=signal_type,
            now=now,
        )

        return {
            "success": True,
            "message": f"{symbol} {ma_period}일선 {direction} 돌파 알림 테스트가 성공적으로 실행되었습니다.",
            "timestamp": now.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 테스트 실패: {str(e)}")


@router.post("/telegram-alerts/rsi", summary="RSI 알림 테스트")
async def test_rsi_alert(
    symbol: str = Query("^IXIC", description="심볼 (예: ^IXIC, ^GSPC)"),
    signal_type: str = Query(
        "overbought", description="신호 유형 (overbought 또는 oversold)"
    ),
):
    """
    RSI 과매수/과매도 알림을 테스트합니다.

    Args:
        symbol: 심볼 (예: ^IXIC, ^GSPC)
        signal_type: 신호 유형 (overbought 또는 oversold)
    """
    try:
        now = datetime.utcnow()

        # 신호 유형에 따라 RSI 값 설정
        current_rsi = 75.8 if signal_type == "overbought" else 28.3

        # 알림 전송
        send_rsi_alert_message(
            symbol=symbol,
            timeframe="1day",
            current_rsi=current_rsi,
            signal_type=signal_type,
            now=now,
        )

        return {
            "success": True,
            "message": f"{symbol} RSI {signal_type} 알림 테스트가 성공적으로 실행되었습니다.",
            "timestamp": now.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 테스트 실패: {str(e)}")


@router.post("/telegram-alerts/cross", summary="골든크로스/데드크로스 알림 테스트")
async def test_cross_alert(
    symbol: str = Query("^IXIC", description="심볼 (예: ^IXIC, ^GSPC)"),
    cross_type: str = Query("golden", description="크로스 유형 (golden 또는 dead)"),
):
    """
    골든크로스/데드크로스 알림을 테스트합니다.

    Args:
        symbol: 심볼 (예: ^IXIC, ^GSPC)
        cross_type: 크로스 유형 (golden 또는 dead)
    """
    try:
        now = datetime.utcnow()

        # 크로스 유형에 따라 이동평균값 설정
        if cross_type == "golden":
            ma_50 = 20950.50 if symbol == "^IXIC" else 6350.75
            ma_200 = 20900.25 if symbol == "^IXIC" else 6300.50
            send_golden_cross_message(
                symbol=symbol, ma_50=ma_50, ma_200=ma_200, now=now
            )
        else:
            ma_50 = 20850.50 if symbol == "^IXIC" else 6250.75
            ma_200 = 20900.25 if symbol == "^IXIC" else 6300.50
            send_dead_cross_message(symbol=symbol, ma_50=ma_50, ma_200=ma_200, now=now)

        return {
            "success": True,
            "message": f"{symbol} {cross_type} 크로스 알림 테스트가 성공적으로 실행되었습니다.",
            "timestamp": now.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 테스트 실패: {str(e)}")


@router.post("/telegram-alerts/bollinger", summary="볼린저 밴드 알림 테스트")
async def test_bollinger_alert(
    symbol: str = Query("^IXIC", description="심볼 (예: ^IXIC, ^GSPC)"),
    signal_type: str = Query(
        "touch_upper",
        description="신호 유형 (touch_upper, touch_lower, break_upper, break_lower)",
    ),
):
    """
    볼린저 밴드 알림을 테스트합니다.

    Args:
        symbol: 심볼 (예: ^IXIC, ^GSPC)
        signal_type: 신호 유형 (touch_upper, touch_lower, break_upper, break_lower)
    """
    try:
        now = datetime.utcnow()

        # 신호 유형에 따라 가격과 밴드값 설정
        if signal_type in ["touch_upper", "break_upper"]:
            current_price = 21050.50 if symbol == "^IXIC" else 6400.75
            upper_band = 21000.25 if symbol == "^IXIC" else 6350.50
            lower_band = 20800.25 if symbol == "^IXIC" else 6250.50
        else:
            current_price = 20750.50 if symbol == "^IXIC" else 6200.75
            upper_band = 21000.25 if symbol == "^IXIC" else 6350.50
            lower_band = 20800.25 if symbol == "^IXIC" else 6250.50

        # 알림 전송
        send_bollinger_alert_message(
            symbol=symbol,
            timeframe="1day",
            current_price=current_price,
            upper_band=upper_band,
            lower_band=lower_band,
            signal_type=signal_type,
            now=now,
        )

        return {
            "success": True,
            "message": f"{symbol} 볼린저 밴드 {signal_type} 알림 테스트가 성공적으로 실행되었습니다.",
            "timestamp": now.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 테스트 실패: {str(e)}")


@router.get("/env-check", summary="환경 변수 확인")
async def check_environment():
    """
    텔레그램 알림에 필요한 환경 변수가 설정되어 있는지 확인합니다.
    """
    import os

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    return {
        "telegram_bot_token_set": token is not None,
        "telegram_chat_id_set": chat_id is not None,
        "env_mode": os.getenv("ENV_MODE", "알 수 없음"),
        "timestamp": datetime.utcnow().isoformat(),
    }
