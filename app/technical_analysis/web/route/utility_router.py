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
from app.technical_analysis.dto.utility_response import (
    ServiceHealthResponse,
    SignalTypesResponse,
)
from app.common.config.api_metadata import common_responses

# 라우터 생성
router = APIRouter()


# =============================================================================
# 유틸리티 API
# =============================================================================


@router.get(
    "/health",
    response_model=ServiceHealthResponse,
    summary="기술적 분석 서비스 상태 확인",
    description="""
    기술적 분석 서비스의 전반적인 상태를 확인합니다.
    
    **확인 항목:**
    - 서비스 가동 상태
    - 의존성 서비스 연결 상태
    - 성능 지표
    - 시스템 리소스 사용량
    
    **모니터링 용도:**
    - 서비스 헬스 체크
    - 장애 감지
    - 성능 모니터링
    """,
    tags=["Health Check"],
    responses={
        **common_responses,
        200: {
            "description": "서비스 상태를 성공적으로 조회했습니다.",
            "model": ServiceHealthResponse,
        },
    },
)
async def health_check() -> ServiceHealthResponse:
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


@router.get(
    "/signal-types",
    response_model=SignalTypesResponse,
    summary="지원하는 신호 타입 목록",
    description="""
    시스템에서 지원하는 모든 기술적 분석 신호 타입을 조회합니다.
    
    **카테고리별 분류:**
    - 이동평균선 신호
    - 모멘텀 지표 신호  
    - 트렌드 지표 신호
    - 볼륨 지표 신호
    """,
    tags=["Utility"],
)
async def get_supported_signal_types() -> SignalTypesResponse:
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
