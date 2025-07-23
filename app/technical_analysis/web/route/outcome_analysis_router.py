"""
결과 분석 API 라우터

신호 결과 추적, 성과 분석, 백테스팅 결과 등을 제공하는 API 엔드포인트들
라우터 → 핸들러 → 서비스 아키텍처를 따릅니다.
"""

from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.technical_analysis.handler.outcome_analysis_handler import (
    OutcomeAnalysisHandler,
)

# 라우터 생성
router = APIRouter()

# 핸들러 인스턴스
handler = OutcomeAnalysisHandler()


# =============================================================================
# Response Models (DTO)
# =============================================================================


class TrackingSummaryResponse(BaseModel):
    total_tracked: int
    completed: int
    pending: int
    completion_rate: float


class SignalPerformanceResponse(BaseModel):
    signal_type: str
    total_signals: int
    avg_return_1h: Optional[float]
    avg_return_1d: Optional[float]
    avg_return_1w: Optional[float]
    success_rate_1h: float
    success_rate_1d: float
    success_rate_1w: float


class BacktestingResultResponse(BaseModel):
    strategy_name: str
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int


class PendingOutcomeResponse(BaseModel):
    outcome_id: int
    signal_id: int
    signal_type: str
    symbol: str
    signal_time: datetime
    elapsed_hours: float
    price_1h_completed: bool
    price_1d_completed: bool
    price_1w_completed: bool
    price_1m_completed: bool


# =============================================================================
# 결과 추적 현황 API
# =============================================================================


@router.get(
    "/tracking/summary",
    response_model=TrackingSummaryResponse,
    summary="결과 추적 현황 요약",
)
async def get_tracking_summary():
    """
    현재 결과 추적 상황의 요약 정보를 반환합니다.

    Returns:
        - total_tracked: 총 추적 중인 신호 수
        - completed: 완료된 추적 수
        - pending: 진행 중인 추적 수
        - completion_rate: 완료율 (%)
    """
    try:
        result = handler.get_tracking_summary()

        return TrackingSummaryResponse(
            total_tracked=result["total_tracked"],
            completed=result["completed"],
            pending=result["pending"],
            completion_rate=result["completion_rate"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tracking/pending",
    response_model=List[PendingOutcomeResponse],
    summary="진행 중인 결과 추적 목록",
)
async def get_pending_outcomes(
    limit: int = Query(10, ge=1, le=100, description="조회할 결과 수")
):
    """
    현재 진행 중인 결과 추적 목록을 반환합니다.

    Args:
        limit: 조회할 결과 수 (1-100)

    Returns:
        진행 중인 추적 결과 목록
    """
    try:
        results = handler.get_pending_outcomes(limit)

        return [
            PendingOutcomeResponse(
                outcome_id=result["outcome_id"],
                signal_id=result["signal_id"],
                signal_type=result["signal_type"],
                symbol=result["symbol"],
                signal_time=result["signal_time"],
                elapsed_hours=result["elapsed_hours"],
                price_1h_completed=result["price_1h_completed"],
                price_1d_completed=result["price_1d_completed"],
                price_1w_completed=result["price_1w_completed"],
                price_1m_completed=result["price_1m_completed"],
            )
            for result in results
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 신호 성과 분석 API
# =============================================================================


@router.get(
    "/performance/by-signal-type",
    response_model=List[SignalPerformanceResponse],
    summary="신호 유형별 성과 분석",
)
async def get_performance_by_signal_type(
    limit: int = Query(10, ge=1, le=50, description="조회할 신호 유형 수")
):
    """
    신호 유형별 성과를 분석하여 반환합니다.

    Args:
        limit: 조회할 신호 유형 수

    Returns:
        신호 유형별 성과 분석 결과
    """
    try:
        results = handler.get_performance_by_signal_type(limit)

        return [
            SignalPerformanceResponse(
                signal_type=result["signal_type"],
                total_signals=result["total_signals"],
                avg_return_1h=result["avg_return_1h"],
                avg_return_1d=result["avg_return_1d"],
                avg_return_1w=result["avg_return_1w"],
                success_rate_1h=result["success_rate_1h"],
                success_rate_1d=result["success_rate_1d"],
                success_rate_1w=result["success_rate_1w"],
            )
            for result in results
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/top-performers", summary="최고 성과 신호 목록")
async def get_top_performers(
    timeframe: str = Query(
        "1d", regex="^(1h|1d|1w)$", description="시간대 (1h, 1d, 1w)"
    ),
    limit: int = Query(10, ge=1, le=50, description="조회할 신호 수"),
):
    """
    최고 성과를 낸 신호들을 반환합니다.

    Args:
        timeframe: 분석할 시간대 (1h, 1d, 1w)
        limit: 조회할 신호 수

    Returns:
        최고 성과 신호 목록
    """
    try:
        results = handler.get_top_performers(timeframe, limit)
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 백테스팅 결과 API
# =============================================================================


@router.post(
    "/backtesting/simple",
    response_model=BacktestingResultResponse,
    summary="간단한 백테스팅 실행",
)
async def run_simple_backtesting(
    signal_types: List[str] = Query(..., description="분석할 신호 유형들"),
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
):
    """
    지정된 신호 유형들에 대해 간단한 백테스팅을 실행합니다.

    Args:
        signal_types: 분석할 신호 유형 목록
        start_date: 분석 시작 날짜
        end_date: 분석 종료 날짜

    Returns:
        백테스팅 결과
    """
    try:
        # 날짜 파싱
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        result = handler.run_simple_backtesting(signal_types, start_dt, end_dt)

        return BacktestingResultResponse(
            strategy_name=result["strategy_name"],
            total_return=result["total_return"],
            annual_return=result["annual_return"],
            max_drawdown=result["max_drawdown"],
            sharpe_ratio=result["sharpe_ratio"],
            win_rate=result["win_rate"],
            total_trades=result["total_trades"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 실시간 모니터링 API
# =============================================================================


@router.get("/monitoring/dashboard", summary="실시간 모니터링 대시보드 데이터")
async def get_dashboard_data():
    """
    실시간 모니터링 대시보드에 필요한 데이터를 반환합니다.

    Returns:
        대시보드 데이터 (통계, 최근 신호, 최고 성과 등)
    """
    try:
        result = handler.get_dashboard_data()
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 유틸리티 API
# =============================================================================


@router.post("/tracking/update", summary="결과 추적 수동 업데이트")
async def manual_update_tracking(
    batch_size: int = Query(10, ge=1, le=100, description="한 번에 처리할 결과 수")
):
    """
    결과 추적을 수동으로 업데이트합니다.

    Args:
        batch_size: 한 번에 처리할 결과 수

    Returns:
        업데이트 결과
    """
    try:
        result = handler.manual_update_tracking(batch_size)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
