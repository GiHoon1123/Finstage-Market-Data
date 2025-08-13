"""
신호 분석 API 라우터

신호 조회, 통계, 현재 상태, 백테스팅, 성과 분석, 결과 추적 등의 기능을 제공합니다.
"""

from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.technical_analysis.dto.signal_response import (
    SignalListResponse,
    TechnicalSignalResponse,
)
from app.common.config.api_metadata import common_responses
from app.common.dto.api_response import ApiResponse
from app.common.utils.response_helper import (
    success_response,
    paginated_response,
    handle_service_error,
)
from app.technical_analysis.service.signal_storage_service import SignalStorageService
from app.technical_analysis.service.technical_monitor_service import (
    TechnicalMonitorService,
)
from app.technical_analysis.service.backtesting_service import BacktestingService
from app.technical_analysis.service.outcome_tracking_service import (
    OutcomeTrackingService,
)
from app.technical_analysis.service.advanced_pattern_service import (
    AdvancedPatternService,
)
from app.technical_analysis.service.portfolio_backtesting_service import (
    PortfolioBacktestingService,
)
from app.technical_analysis.service.signal_filtering_service import (
    SignalFilteringService,
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
backtesting_service = BacktestingService()
outcome_tracking_service = OutcomeTrackingService()
advanced_pattern_service = AdvancedPatternService()
portfolio_backtesting_service = PortfolioBacktestingService()
signal_filtering_service = SignalFilteringService()


# =============================================================================
# 신호 조회 API
# =============================================================================


@router.get(
    "/signals",
    response_model=ApiResponse,
    summary="기술적 분석 신호 조회",
    description="""
    최근 발생한 기술적 분석 신호들을 조회합니다.
    
    **주요 기능:**
    - 다양한 필터 조건으로 신호 검색
    - 시간 범위별 신호 조회
    - 신호 강도 및 신뢰도 정보 제공
    - 실시간 신호 모니터링 지원
    
    **지원하는 신호 타입:**
    - MA200_breakout_up/down: 200일 이동평균선 돌파
    - RSI_oversold/overbought: RSI 과매도/과매수
    - MACD_bullish/bearish: MACD 강세/약세 신호
    - Bollinger_squeeze: 볼린저 밴드 압축
    
    **사용 사례:**
    - 매매 타이밍 포착
    - 시장 동향 분석
    - 포트폴리오 리밸런싱
    - 알고리즘 트레이딩 신호
    """,
    tags=["Technical Analysis"],
    responses={
        **common_responses,
        200: {
            "description": "기술적 신호를 성공적으로 조회했습니다.",
            "model": ApiResponse,
        },
    },
)
async def get_recent_signals(
    symbol: Optional[str] = Query(
        None, example="AAPL", description="심볼 필터 (예: AAPL, MSFT, ^IXIC)"
    ),
    signal_type: Optional[str] = Query(
        None,
        example="MA200_breakout_up",
        description="신호 타입 필터 (예: MA200_breakout_up, RSI_oversold)",
    ),
    timeframe: Optional[str] = Query(
        None, example="1d", description="시간대 필터 (1min, 15min, 1h, 1d)"
    ),
    hours: int = Query(
        24, description="조회할 시간 범위 (시간)", ge=1, le=168, example=24
    ),
    limit: int = Query(50, description="최대 조회 개수", ge=1, le=200, example=50),
) -> ApiResponse:
    """
    최근 발생한 기술적 분석 신호들을 조회합니다.

    다양한 필터 조건을 사용하여 원하는 신호들만 선별적으로 조회할 수 있으며,
    각 신호의 강도와 신뢰도 정보를 함께 제공합니다.
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
        
        return success_response(
            data=response_data,
            message=f"기술적 신호 조회 완료 ({len(signals)}개 신호)"
        )

    except Exception as e:
        handle_service_error(e, "기술적 신호 조회 실패")


@router.get(
    "/signals/{symbol}",
    summary="심볼별 신호 조회",
    description="특정 심볼에서 발생한 기술적 분석 신호들을 조회합니다.",
    tags=["Technical Analysis"],
)
async def get_signals_by_symbol(
    symbol: str = Path(..., example="AAPL", description="조회할 심볼"),
    signal_type: Optional[str] = Query(None, description="신호 타입 필터"),
    timeframe: Optional[str] = Query(None, description="시간대 필터"),
    limit: int = Query(100, description="최대 조회 개수", ge=1, le=500),
    offset: int = Query(0, description="건너뛸 개수 (페이징)", ge=0),
) -> ApiResponse:
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

        # 전체 개수 조회 (페이징을 위해)
        total_signals = repository.find_by_symbol(symbol=symbol)
        if timeframe:
            total_signals = [s for s in total_signals if s.timeframe == timeframe]
        total_count = len(total_signals)

        response_data = {
            "symbol": symbol,
            "signals": [signal.to_dict() for signal in signals],
            "filters": {"signal_type": signal_type, "timeframe": timeframe},
        }

        session.close()
        
        # 페이징 응답 사용
        return paginated_response(
            items=response_data,
            page=(offset // limit) + 1,
            size=limit,
            total=total_count,
            message=f"{symbol} 신호 조회 완료"
        )

    except Exception as e:
        handle_service_error(e, f"{symbol} 신호 조회 실패")


# =============================================================================
# 통계 조회 API
# =============================================================================


@router.get(
    "/stats/signal-count",
    summary="신호 발생 통계",
    description="지정된 기간 동안의 신호 발생 통계를 조회합니다.",
    tags=["Technical Analysis"],
)
async def get_signal_count_stats(
    days: int = Query(30, description="조회할 일수", ge=1, le=365),
    symbol: Optional[str] = Query(None, description="심볼 필터"),
) -> ApiResponse:
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
        
        return success_response(
            data=response_data,
            message=f"신호 통계 조회 완료 ({sum(stat['count'] for stat in stats)}개 신호)"
        )

    except Exception as e:
        handle_service_error(e, "신호 통계 조회 실패")


@router.get(
    "/stats/daily-count/{symbol}",
    summary="일별 신호 발생 횟수",
    description="특정 심볼의 일별 신호 발생 횟수를 조회합니다.",
    tags=["Technical Analysis"],
)
async def get_daily_signal_count(
    symbol: str = Path(..., example="AAPL", description="조회할 심볼"),
    days: int = Query(30, description="조회할 일수", ge=1, le=90),
) -> ApiResponse:
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
        
        total_signals = sum(day["count"] for day in daily_counts)
        return success_response(
            data=response_data,
            message=f"{symbol} 일별 신호 통계 조회 완료 ({total_signals}개 신호)"
        )

    except Exception as e:
        handle_service_error(e, f"{symbol} 일별 신호 통계 조회 실패")


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
# 백테스팅 및 성과 분석 API
# =============================================================================


@router.get(
    "/performance/all",
    summary="전체 신호 성과 분석",
    description="모든 신호 타입의 성과를 종합적으로 분석합니다.",
    tags=["Technical Analysis"],
)
async def get_all_signals_performance(
    timeframe_eval: str = Query("1d", description="평가 기간 (1h, 1d, 1w, 1m)"),
    min_samples: int = Query(10, description="최소 샘플 수", ge=1, le=100),
) -> Dict[str, Any]:
    """
    모든 신호 타입의 성과를 종합 분석합니다.

    각 신호의 성공률, 평균 수익률, 리스크 지표 등을 제공하여
    어떤 신호가 가장 효과적인지 파악할 수 있습니다.

    Args:
        timeframe_eval: 평가할 시간 기준 (1h=1시간후, 1d=1일후, 1w=1주후, 1m=1개월후)
        min_samples: 분석에 포함할 최소 신호 개수 (이보다 적으면 제외)

    Returns:
        전체 신호 성과 분석 결과
        - summary: 전체 요약 통계
        - by_signal_type: 신호 타입별 상세 성과
        - best_performers: 가장 좋은 성과를 보인 신호들
        - recommendations: AI 추천 사항
    """
    try:
        result = backtesting_service.analyze_all_signals_performance(
            timeframe_eval=timeframe_eval, min_samples=min_samples
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"전체 성과 분석 실패: {str(e)}")


@router.get("/performance/{signal_type}", summary="특정 신호 타입 성과 분석")
async def get_signal_type_performance(
    signal_type: str = Path(..., description="신호 타입 (예: MA200_breakout_up)"),
    symbol: Optional[str] = Query(None, description="심볼 필터 (예: NQ=F)"),
) -> Dict[str, Any]:
    """
    특정 신호 타입의 상세 성과를 분석합니다.

    시간대별 성과, 리스크 지표, 월별 성과 등을 제공하여
    해당 신호의 특성을 깊이 있게 파악할 수 있습니다.

    Args:
        signal_type: 분석할 신호 타입
        symbol: 특정 심볼로 필터링 (선택사항)

    Returns:
        해당 신호의 상세 성과 분석
        - timeframe_performance: 1시간/1일/1주/1개월 후 성과
        - risk_metrics: 최대손실, 변동성, 샤프비율 등
        - monthly_performance: 월별 성과 추이
        - signal_quality_score: AI가 계산한 신호 품질 점수
    """
    try:
        result = backtesting_service.analyze_signal_type_performance(
            signal_type=signal_type, symbol=symbol
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"신호 타입 성과 분석 실패: {str(e)}"
        )


@router.post(
    "/backtest/strategy",
    summary="매매 전략 백테스팅",
    description="선택한 신호들을 조합한 매매 전략의 백테스팅을 수행합니다.",
    tags=["Technical Analysis"],
)
async def backtest_trading_strategy(
    signal_types: List[str] = Query(..., description="사용할 신호 타입들"),
    initial_capital: float = Query(10000.0, description="초기 자본금 ($)", ge=1000),
    position_size: float = Query(
        0.1, description="포지션 크기 (자본금 대비 비율)", ge=0.01, le=1.0
    ),
    stop_loss: Optional[float] = Query(
        None, description="손절매 비율 (예: -0.05 = -5%)"
    ),
    take_profit: Optional[float] = Query(
        None, description="익절매 비율 (예: 0.10 = +10%)"
    ),
    days: int = Query(90, description="백테스팅 기간 (일)", ge=7, le=365),
) -> Dict[str, Any]:
    """
    매매 전략을 백테스팅하여 성과를 시뮬레이션합니다.

    여러 신호를 조합한 전략의 수익률, 승률, 최대손실 등을 계산하여
    실제 매매 전에 전략의 효과를 검증할 수 있습니다.

    Args:
        signal_types: 전략에 사용할 신호 타입들 (예: ["MA200_breakout_up", "RSI_oversold"])
        initial_capital: 시뮬레이션 시작 자본금
        position_size: 한 번에 투자할 비율 (0.1 = 자본금의 10%)
        stop_loss: 손절매 기준 (-0.05 = -5% 손실시 매도)
        take_profit: 익절매 기준 (0.10 = +10% 수익시 매도)
        days: 백테스팅할 기간 (일수)

    Returns:
        백테스팅 결과
        - performance: 총 수익률, 승률, 최대손실 등 핵심 지표
        - trades: 실제 거래 내역 (최근 20개)
        - strategy_config: 사용된 전략 설정
    """
    try:
        # 날짜 범위 계산
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        result = backtesting_service.simulate_trading_strategy(
            signal_types=signal_types,
            initial_capital=initial_capital,
            position_size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            start_date=start_date,
            end_date=end_date,
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"백테스팅 실패: {str(e)}")


@router.get("/quality/{signal_type}", summary="신호 품질 평가")
async def evaluate_signal_quality(
    signal_type: str = Path(..., description="평가할 신호 타입"),
    symbol: Optional[str] = Query(None, description="심볼 필터"),
) -> Dict[str, Any]:
    """
    신호의 품질을 종합적으로 평가하여 등급을 매깁니다.

    성공률, 수익률, 리스크 등을 종합하여 A~F 등급으로 평가하고
    해당 신호의 강점과 약점을 분석합니다.

    Args:
        signal_type: 평가할 신호 타입
        symbol: 특정 심볼로 필터링 (선택사항)

    Returns:
        신호 품질 평가 결과
        - quality_assessment: 종합 점수, 등급, 추천사항
        - detailed_analysis: 강점, 약점, 샘플 크기
        - performance_metrics: 상세 성과 지표
    """
    try:
        result = backtesting_service.evaluate_signal_quality(
            signal_type=signal_type, symbol=symbol
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"신호 품질 평가 실패: {str(e)}")


# =============================================================================
# 결과 추적 API
# =============================================================================


@router.post("/outcomes/track/{signal_id}", summary="신호 결과 추적 시작")
async def start_outcome_tracking(
    signal_id: int = Path(..., description="추적할 신호 ID"),
) -> Dict[str, Any]:
    """
    특정 신호에 대한 결과 추적을 시작합니다.

    신호 발생 후 1시간, 4시간, 1일, 1주일, 1개월 후의 가격을
    자동으로 수집하여 실제 성과를 측정합니다.

    Args:
        signal_id: 추적을 시작할 신호의 ID

    Returns:
        추적 시작 결과
    """
    try:
        result = outcome_tracking_service.initialize_outcome_tracking(signal_id)

        if result is None:
            raise HTTPException(
                status_code=404, detail="신호를 찾을 수 없거나 추적 시작 실패"
            )

        return {
            "message": "결과 추적이 시작되었습니다",
            "signal_id": signal_id,
            "outcome_id": result.id,
            "tracking_started_at": result.created_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"결과 추적 시작 실패: {str(e)}")


@router.put("/outcomes/update", summary="결과 추적 업데이트")
async def update_outcomes(
    hours_old: int = Query(1, description="몇 시간 이상 된 것만 업데이트", ge=1, le=24),
) -> Dict[str, Any]:
    """
    미완료된 결과 추적들을 업데이트합니다.

    스케줄러에서 주기적으로 호출하거나, 수동으로 실행하여
    신호 발생 후 경과된 시간에 따라 가격과 수익률을 업데이트합니다.

    Args:
        hours_old: 몇 시간 이상 된 신호만 업데이트할지 설정

    Returns:
        업데이트 결과 통계
    """
    try:
        result = outcome_tracking_service.update_outcomes(hours_old=hours_old)

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"결과 업데이트 실패: {str(e)}")


@router.get("/outcomes/{signal_id}", summary="신호 결과 조회")
async def get_signal_outcome(
    signal_id: int = Path(..., description="조회할 신호 ID"),
) -> Dict[str, Any]:
    """
    특정 신호의 결과 추적 데이터를 조회합니다.

    신호 발생 후 각 시간대별 가격 변화와 수익률을 확인할 수 있습니다.

    Args:
        signal_id: 조회할 신호의 ID

    Returns:
        신호 결과 데이터
        - signal: 원본 신호 정보
        - outcome: 시간대별 가격 및 수익률 데이터
        - analysis: 추가 분석 정보
        - tracking_status: 추적 완료 여부
    """
    try:
        result = outcome_tracking_service.get_signal_outcome(signal_id)

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"신호 결과 조회 실패: {str(e)}")


@router.post("/outcomes/test/{signal_id}", summary="결과 추적 테스트")
async def test_outcome_tracking(
    signal_id: int = Path(..., description="테스트할 신호 ID"),
) -> Dict[str, Any]:
    """
    결과 추적 기능을 테스트합니다. (개발용)

    실제 시간 경과를 기다리지 않고 가상의 가격 데이터를 생성하여
    결과 추적 시스템이 정상 동작하는지 확인합니다.

    Args:
        signal_id: 테스트할 신호 ID

    Returns:
        테스트 결과
    """
    try:
        result = outcome_tracking_service.test_outcome_tracking(signal_id)

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"결과 추적 테스트 실패: {str(e)}")
