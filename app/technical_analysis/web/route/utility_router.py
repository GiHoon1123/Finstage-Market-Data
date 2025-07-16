"""
유틸리티 API 라우터

서비스 상태 확인, 신호 타입 목록 등의 유틸리티 기능을 제공합니다.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime
from app.technical_analysis.infra.model.repository.technical_signal_repository import (
    TechnicalSignalRepository,
)
from app.common.infra.database.config.database_config import SessionLocal

# 라우터 생성
router = APIRouter()


# =============================================================================
# 유틸리티 API
# =============================================================================


@router.get("/health", summary="서비스 상태 확인")
async def health_check() -> Dict[str, Any]:
    """
    기술적 분석 서비스의 상태를 확인합니다.

    Returns:
        서비스 상태 정보
    """
    try:
        # 간단한 DB 연결 테스트
        session = SessionLocal()
        repository = TechnicalSignalRepository(session)

        # 최근 1시간 내 신호 개수 조회 (DB 연결 테스트)
        recent_signals = repository.find_recent_signals(hours=1)
        signal_count = len(recent_signals)

        session.close()

        return {
            "status": "healthy",
            "service": "technical_analysis",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "recent_signals_1h": signal_count,
            "version": "1.0.0",
        }

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"서비스 상태 불량: {str(e)}")


@router.get("/signal-types", summary="지원하는 신호 타입 목록")
async def get_supported_signal_types() -> Dict[str, Any]:
    """
    현재 지원하는 모든 신호 타입의 목록과 설명을 제공합니다.

    Returns:
        신호 타입 목록과 설명
    """
    signal_types = {
        "moving_average": {
            "MA20_breakout_up": "20일선 상향 돌파",
            "MA20_breakout_down": "20일선 하향 이탈",
            "MA50_breakout_up": "50일선 상향 돌파",
            "MA50_breakout_down": "50일선 하향 이탈",
            "MA200_breakout_up": "200일선 상향 돌파",
            "MA200_breakout_down": "200일선 하향 이탈",
        },
        "rsi": {
            "RSI_overbought": "RSI 과매수 (70 이상)",
            "RSI_oversold": "RSI 과매도 (30 이하)",
            "RSI_bullish": "RSI 상승 모멘텀 (50 돌파)",
            "RSI_bearish": "RSI 하락 모멘텀 (50 이탈)",
        },
        "bollinger_bands": {
            "BB_touch_upper": "볼린저 밴드 상단 터치",
            "BB_touch_lower": "볼린저 밴드 하단 터치",
            "BB_break_upper": "볼린저 밴드 상단 돌파",
            "BB_break_lower": "볼린저 밴드 하단 이탈",
        },
        "cross_signals": {
            "golden_cross": "골든크로스 (50일선이 200일선 상향돌파)",
            "dead_cross": "데드크로스 (50일선이 200일선 하향이탈)",
        },
    }

    return {
        "signal_types": signal_types,
        "total_types": sum(len(category) for category in signal_types.values()),
        "categories": list(signal_types.keys()),
        "description": "기술적 분석에서 지원하는 모든 신호 타입들입니다.",
    }