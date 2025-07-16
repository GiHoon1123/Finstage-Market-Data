"""
기술적 분석 API 라우터

이 파일은 기술적 분석 관련 API 엔드포인트를 제공합니다.
저장된 기술적 신호 데이터를 조회하고 통계를 제공하는 REST API입니다.

주요 기능:
1. 신호 조회 - 저장된 기술적 신호들을 다양한 조건으로 조회
2. 통계 조회 - 신호 발생 빈도, 성공률 등 통계 데이터
3. 현재 상태 - 실시간 기술적 지표 상태 조회
4. 백테스팅 - 과거 신호들의 성과 분석 (Phase 2에서 구현 예정)

API 사용 예시:
- GET /api/technical-analysis/signals - 최근 신호들 조회
- GET /api/technical-analysis/signals/NQ=F - 특정 심볼의 신호들
- GET /api/technical-analysis/stats/signal-count - 신호 발생 통계
- GET /api/technical-analysis/current-status/NQ=F/1min - 현재 기술적 지표 상태
"""

from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.technical_analysis.service.signal_storage_service import SignalStorageService
from app.technical_analysis.service.technical_monitor_service import (
    TechnicalMonitorService,
)
from app.technical_analysis.infra.model.repository.technical_signal_repository import (
    TechnicalSignalRepository,
)
from app.common.infra.database.config.database_config import SessionLocal

# 라우터 생성
router = APIRouter()

# 서비스 인스턴스들
signal_storage_service = SignalStorageService()
technical_monitor_service = TechnicalMonitorService()


# =============================================================================
# 신호 조회 API
# =============================================================================


@router.get("/signals", summary="최근 기술적 신호 조회")
async def get_recent_signals(
    symbol: Optional[str] = Query(None, description="심볼 필터 (예: NQ=F, ^IXIC)"),
    signal_type: Optional[str] = Query(
        None, description="신호 타입 필터 (예: MA200_breakout_up)"
    ),
    timeframe: Optional[str] = Query(
        None, description="시간대 필터 (1min, 15min, 1day)"
    ),
    hours: int = Query(
        24, description="조회할 시간 범위 (시간)", ge=1, le=168
    ),  # 최대 1주일
    limit: int = Query(50, description="최대 조회 개수", ge=1, le=200),
) -> Dict[str, Any]:
    """
    최근 발생한 기술적 신호들을 조회합니다.

    다양한 필터 조건을 사용하여 원하는 신호들만 조회할 수 있습니다.

    Args:
        symbol: 심볼 필터 (선택사항)
        signal_type: 신호 타입 필터 (선택사항)
        timeframe: 시간대 필터 (선택사항)
        hours: 조회할 시간 범위 (기본: 24시간)
        limit: 최대 조회 개수 (기본: 50개)

    Returns:
        신호 리스트와 메타데이터
    """
    try:
        session = SessionLocal()
        repository = TechnicalSignalRepository(session)

        # 날짜 범위 계산
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(hours=hours)

        # 기본 조회
        signals = repository.find_by_date_range(
            start_date=start_date,
            end_date=end_date,
            symbol=symbol,
            signal_type=signal_type,
        )

        # 시간대 필터 적용 (DB 쿼리에서 지원하지 않는 경우)
        if timeframe:
            signals = [s for s in signals if s.timeframe == timeframe]

        # 제한 개수 적용
        signals = signals[:limit]

        # 응답 데이터 구성
        response_data = {
            "signals": [signal.to_dict() for signal in signals],
            "metadata": {
                "total_count": len(signals),
                "query_params": {
                    "symbol": symbol,
                    "signal_type": signal_type,
                    "timeframe": timeframe,
                    "hours": hours,
                    "limit": limit,
                },
                "time_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
            },
        }

        session.close()
        return response_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"신호 조회 실패: {str(e)}")


@router.get("/signals/{symbol}", summary="특정 심볼의 신호 조회")
async def get_signals_by_symbol(
    symbol: str = Path(..., description="심볼 (예: NQ=F, ^IXIC)"),
    signal_type: Optional[str] = Query(None, description="신호 타입 필터"),
    timeframe: Optional[str] = Query(None, description="시간대 필터"),
    limit: int = Query(100, description="최대 조회 개수", ge=1, le=500),
    offset: int = Query(0, description="건너뛸 개수 (페이징)", ge=0),
) -> Dict[str, Any]:
    """
    특정 심볼의 기술적 신호들을 조회합니다.

    페이징을 지원하여 대량의 데이터도 효율적으로 조회할 수 있습니다.

    Args:
        symbol: 조회할 심볼
        signal_type: 신호 타입 필터 (선택사항)
        timeframe: 시간대 필터 (선택사항)
        limit: 최대 조회 개수
        offset: 건너뛸 개수 (페이징용)

    Returns:
        해당 심볼의 신호 리스트
    """
    try:
        session = SessionLocal()
        repository = TechnicalSignalRepository(session)

        # 신호 타입별 조회 또는 심볼별 조회
        if signal_type:
            signals = repository.find_by_signal_type(
                signal_type=signal_type,
                symbol=symbol,
                timeframe=timeframe,
                limit=limit + offset,  # offset 고려하여 더 많이 조회
            )
            # 수동으로 offset 적용
            signals = signals[offset : offset + limit]
        else:
            signals = repository.find_by_symbol(
                symbol=symbol, limit=limit, offset=offset
            )
            # 시간대 필터 적용
            if timeframe:
                signals = [s for s in signals if s.timeframe == timeframe]

        response_data = {
            "symbol": symbol,
            "signals": [signal.to_dict() for signal in signals],
            "pagination": {"limit": limit, "offset": offset, "count": len(signals)},
            "filters": {"signal_type": signal_type, "timeframe": timeframe},
        }

        session.close()
        return response_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"심볼별 신호 조회 실패: {str(e)}")


# =============================================================================
# 통계 조회 API
# =============================================================================


@router.get("/stats/signal-count", summary="신호 발생 통계")
async def get_signal_count_stats(
    days: int = Query(30, description="조회할 일수", ge=1, le=365),
    symbol: Optional[str] = Query(None, description="심볼 필터"),
) -> Dict[str, Any]:
    """
    신호 타입별 발생 횟수 통계를 조회합니다.

    지정된 기간 동안 각 신호 타입이 얼마나 자주 발생했는지 확인할 수 있습니다.

    Args:
        days: 조회할 일수 (기본: 30일)
        symbol: 심볼 필터 (선택사항)

    Returns:
        신호 타입별 발생 횟수 통계
    """
    try:
        session = SessionLocal()
        repository = TechnicalSignalRepository(session)

        # 날짜 범위 계산
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # 신호 타입별 통계 조회
        stats = repository.get_signal_count_by_type(
            start_date=start_date, end_date=end_date
        )

        # 심볼 필터가 있는 경우 추가 필터링 (간단한 구현)
        if symbol:
            # 해당 심볼의 신호들만 별도 조회하여 통계 계산
            symbol_signals = repository.find_by_date_range(
                start_date=start_date, end_date=end_date, symbol=symbol
            )

            # 신호 타입별 카운트 계산
            signal_type_counts = {}
            for signal in symbol_signals:
                signal_type = signal.signal_type
                signal_type_counts[signal_type] = (
                    signal_type_counts.get(signal_type, 0) + 1
                )

            stats = [
                {"signal_type": signal_type, "count": count}
                for signal_type, count in signal_type_counts.items()
            ]

        response_data = {
            "statistics": stats,
            "metadata": {
                "period": {
                    "days": days,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "filters": {"symbol": symbol},
                "total_signals": sum(stat["count"] for stat in stats),
            },
        }

        session.close()
        return response_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"신호 통계 조회 실패: {str(e)}")


@router.get("/stats/daily-count/{symbol}", summary="일별 신호 발생 횟수")
async def get_daily_signal_count(
    symbol: str = Path(..., description="심볼"),
    days: int = Query(30, description="조회할 일수", ge=1, le=90),
) -> Dict[str, Any]:
    """
    특정 심볼의 일별 신호 발생 횟수를 조회합니다.

    차트나 그래프로 시각화하기 좋은 형태의 데이터를 제공합니다.

    Args:
        symbol: 조회할 심볼
        days: 조회할 일수

    Returns:
        일별 신호 발생 횟수 데이터
    """
    try:
        session = SessionLocal()
        repository = TechnicalSignalRepository(session)

        # 일별 신호 횟수 조회
        daily_counts = repository.get_daily_signal_count(symbol=symbol, days=days)

        response_data = {
            "symbol": symbol,
            "daily_counts": daily_counts,
            "metadata": {
                "period_days": days,
                "total_days_with_signals": len(daily_counts),
                "total_signals": sum(day["count"] for day in daily_counts),
                "average_signals_per_day": (
                    sum(day["count"] for day in daily_counts) / len(daily_counts)
                    if daily_counts
                    else 0
                ),
            },
        }

        session.close()
        return response_data

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"일별 신호 통계 조회 실패: {str(e)}"
        )


@router.get("/stats/signal-strength/{signal_type}", summary="신호 강도 통계")
async def get_signal_strength_stats(
    signal_type: str = Path(..., description="신호 타입 (예: MA200_breakout_up)"),
    symbol: Optional[str] = Query(None, description="심볼 필터"),
) -> Dict[str, Any]:
    """
    특정 신호 타입의 강도 통계를 조회합니다.

    신호의 평균 강도, 최대/최소 강도 등을 확인할 수 있습니다.

    Args:
        signal_type: 신호 타입
        symbol: 심볼 필터 (선택사항)

    Returns:
        신호 강도 통계 데이터
    """
    try:
        session = SessionLocal()
        repository = TechnicalSignalRepository(session)

        # 신호 강도 통계 조회
        strength_stats = repository.get_signal_strength_stats(
            signal_type=signal_type, symbol=symbol
        )

        response_data = {
            "signal_type": signal_type,
            "symbol": symbol,
            "strength_statistics": strength_stats,
            "interpretation": {
                "avg": f"평균 신호 강도: {strength_stats['avg']:.2f}%",
                "max": f"최대 신호 강도: {strength_stats['max']:.2f}%",
                "min": f"최소 신호 강도: {strength_stats['min']:.2f}%",
                "sample_size": f"분석 대상 신호 개수: {strength_stats['count']}개",
            },
        }

        session.close()
        return response_data

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"신호 강도 통계 조회 실패: {str(e)}"
        )


# =============================================================================
# 현재 상태 조회 API
# =============================================================================


@router.get("/current-status/{symbol}/{timeframe}", summary="현재 기술적 지표 상태")
async def get_current_technical_status(
    symbol: str = Path(..., description="심볼 (예: NQ=F, ^IXIC)"),
    timeframe: str = Path(..., description="시간대 (1min, 15min, 1day)"),
) -> Dict[str, Any]:
    """
    현재 기술적 지표 상태를 실시간으로 조회합니다.

    이동평균, RSI, 볼린저 밴드 등의 현재 값과 신호 상태를 확인할 수 있습니다.

    Args:
        symbol: 조회할 심볼
        timeframe: 시간대

    Returns:
        현재 기술적 지표 상태
    """
    try:
        # 유효한 시간대 체크
        valid_timeframes = ["1min", "15min", "1day"]
        if timeframe not in valid_timeframes:
            raise HTTPException(
                status_code=400,
                detail=f"유효하지 않은 시간대: {timeframe}. 사용 가능: {valid_timeframes}",
            )

        # 현재 기술적 지표 상태 조회
        status = technical_monitor_service.get_current_technical_status(
            symbol, timeframe
        )

        if "error" in status:
            raise HTTPException(status_code=500, detail=status["error"])

        return status

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"기술적 지표 상태 조회 실패: {str(e)}"
        )


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
