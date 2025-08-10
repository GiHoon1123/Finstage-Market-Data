"""
전략분석 복구 API 라우터

10년치 나스닥/S&P500 데이터를 수집하고 모든 분석을 수행하여 테이블에 저장하는 복구 API
라우터 → 핸들러 → 서비스 아키텍처를 따릅니다.
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
import asyncio

from app.technical_analysis.handler.recovery_handler import RecoveryHandler
from app.technical_analysis.service.recovery_service import RecoveryService
from app.common.utils.logging_config import get_logger
from app.technical_analysis.dto.recovery_response import (
    RecoveryTaskResponse,
    RecoveryStatusResponse,
)
from app.common.config.api_metadata import common_responses

logger = get_logger(__name__)
router = APIRouter()

# 핸들러 및 서비스 인스턴스
recovery_handler = RecoveryHandler()
recovery_service = RecoveryService()


@router.post(
    "/historical-data",
    response_model=RecoveryTaskResponse,
    summary="과거 데이터 복구",
    description="""
    10년치 과거 주가 데이터를 복구합니다.
    
    **복구 범위:**
    - 일봉, 주봉, 월봉 데이터
    - 거래량 및 시가총액
    - 배당 및 분할 정보
    """,
    tags=["Data Recovery"],
)
async def recover_historical_data(
    background_tasks: BackgroundTasks,
    symbols: Optional[str] = Query(
        "^IXIC,^GSPC", description="복구할 심볼들 (쉼표 구분)"
    ),
    years: int = Query(10, description="복구할 연도 수", ge=1, le=25),
    force_update: bool = Query(False, description="기존 데이터 강제 업데이트 여부"),
    run_in_background: bool = Query(True, description="백그라운드에서 실행 여부"),
) -> Dict[str, Any]:
    """
    나스닥과 S&P500의 10년치 일봉 데이터를 수집하여 테이블에 저장합니다.

    Args:
        symbols: 복구할 심볼들 (기본값: ^IXIC,^GSPC)
        years: 복구할 연도 수 (기본값: 10년)
        force_update: 기존 데이터가 있어도 강제로 업데이트할지 여부
        run_in_background: 백그라운드에서 실행할지 여부

    Returns:
        복구 작업 시작 결과
    """
    try:
        # 심볼 리스트 파싱
        symbol_list = [s.strip() for s in symbols.split(",")]

        logger.info(
            "historical_data_recovery_api_called",
            symbols=symbol_list,
            years=years,
            force_update=force_update,
            run_in_background=run_in_background,
        )

        if run_in_background:
            # 백그라운드에서 실행
            background_tasks.add_task(
                recovery_service.recover_historical_data_background,
                symbol_list,
                years,
                force_update,
            )

            return {
                "status": "started",
                "message": "10년치 과거 데이터 복구가 백그라운드에서 시작되었습니다.",
                "symbols": symbol_list,
                "years": years,
                "force_update": force_update,
                "estimated_time": f"{len(symbol_list) * years * 2}분",
                "started_at": datetime.now().isoformat(),
            }
        else:
            # 핸들러를 통한 동기적 실행
            result = await recovery_handler.handle_historical_data_recovery(
                symbol_list, years, force_update
            )

            return result

    except Exception as e:
        logger.error("historical_data_recovery_api_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"과거 데이터 복구 실패: {str(e)}")


@router.post(
    "/technical-analysis",
    response_model=RecoveryTaskResponse,
    summary="기술적 분석 데이터 복구",
    description="모든 기술적 분석 지표와 신호를 재계산하여 복구합니다.",
    tags=["Data Recovery"],
)
async def recover_technical_analysis(
    background_tasks: BackgroundTasks,
    symbols: Optional[str] = Query("^IXIC,^GSPC", description="분석할 심볼들"),
    analysis_types: List[str] = Query(
        ["signals", "patterns", "outcomes", "clusters"],
        description="수행할 분석 타입들",
    ),
    date_range_days: int = Query(
        365, description="분석할 날짜 범위 (일)", ge=30, le=3650
    ),
    run_in_background: bool = Query(True, description="백그라운드에서 실행 여부"),
) -> Dict[str, Any]:
    """
    저장된 일봉 데이터를 기반으로 모든 기술적 분석을 수행하여 결과를 테이블에 저장합니다.

    분석 타입:
    - signals: 기술적 신호 분석 (이동평균, RSI, 볼린저밴드 등)
    - patterns: 신호 패턴 분석 (신호 조합 패턴)
    - outcomes: 신호 결과 추적 (백테스팅)
    - clusters: 패턴 클러스터링 (고급 분석)

    Args:
        symbols: 분석할 심볼들
        analysis_types: 수행할 분석 타입들
        date_range_days: 분석할 날짜 범위 (일)
        run_in_background: 백그라운드에서 실행할지 여부

    Returns:
        분석 작업 시작 결과
    """
    try:
        # 심볼 리스트 파싱
        symbol_list = [s.strip() for s in symbols.split(",")]

        logger.info(
            "technical_analysis_recovery_api_called",
            symbols=symbol_list,
            analysis_types=analysis_types,
            date_range_days=date_range_days,
            run_in_background=run_in_background,
        )

        if run_in_background:
            # 백그라운드에서 실행
            background_tasks.add_task(
                recovery_service.recover_technical_analysis_background,
                symbol_list,
                analysis_types,
                date_range_days,
            )

            return {
                "status": "started",
                "message": "전체 기술적 분석 복구가 백그라운드에서 시작되었습니다.",
                "symbols": symbol_list,
                "analysis_types": analysis_types,
                "date_range_days": date_range_days,
                "estimated_time": f"{len(symbol_list) * len(analysis_types) * 10}분",
                "started_at": datetime.now().isoformat(),
            }
        else:
            # 핸들러를 통한 동기적 실행
            result = await recovery_handler.handle_technical_analysis_recovery(
                symbol_list, analysis_types, date_range_days
            )

            return result

    except Exception as e:
        logger.error("technical_analysis_recovery_api_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"기술적 분석 복구 실패: {str(e)}")


@router.post(
    "/full-recovery",
    response_model=RecoveryTaskResponse,
    summary="전체 시스템 복구",
    description="과거 데이터와 기술적 분석을 모두 복구하는 완전 복구 작업입니다.",
    tags=["Data Recovery"],
)
async def full_recovery(
    background_tasks: BackgroundTasks,
    symbols: Optional[str] = Query("^IXIC,^GSPC", description="복구할 심볼들"),
    years: int = Query(10, description="복구할 연도 수", ge=1, le=25),
    force_update: bool = Query(False, description="기존 데이터 강제 업데이트 여부"),
) -> Dict[str, Any]:
    """
    전체 복구: 10년치 데이터 수집 + 모든 기술적 분석 수행

    1단계: 10년치 일봉 데이터 수집 및 저장
    2단계: 수집된 데이터로 모든 기술적 분석 수행

    Args:
        symbols: 복구할 심볼들
        years: 복구할 연도 수
        force_update: 기존 데이터 강제 업데이트 여부

    Returns:
        전체 복구 작업 시작 결과
    """
    try:
        # 심볼 리스트 파싱
        symbol_list = [s.strip() for s in symbols.split(",")]

        logger.info(
            "full_recovery_api_called",
            symbols=symbol_list,
            years=years,
            force_update=force_update,
        )

        # 핸들러를 통한 처리
        result = await recovery_handler.handle_full_recovery(
            symbol_list, years, force_update
        )

        # 백그라운드에서 전체 복구 실행
        background_tasks.add_task(
            recovery_service.full_recovery_background, symbol_list, years, force_update
        )

        return result

    except Exception as e:
        logger.error("full_recovery_api_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"전체 복구 실패: {str(e)}")


@router.get(
    "/status",
    response_model=RecoveryStatusResponse,
    summary="복구 작업 상태 확인",
    description="현재 진행 중인 복구 작업들의 상태를 확인합니다.",
    tags=["Data Recovery"],
)
async def get_recovery_status() -> RecoveryStatusResponse:
    """
    현재 복구 작업의 상태를 확인합니다.

    Returns:
        복구 작업 상태 정보
    """
    try:
        logger.info("recovery_status_api_called")

        # 핸들러를 통한 상태 확인
        result = await recovery_handler.handle_recovery_status_check()

        return result

    except Exception as e:
        logger.error("recovery_status_api_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"상태 확인 실패: {str(e)}")


@router.get("/data-summary", summary="저장된 데이터 요약")
async def get_data_summary(
    symbol: Optional[str] = Query(None, description="특정 심볼 필터")
) -> Dict[str, Any]:
    """
    현재 저장된 데이터의 요약 정보를 조회합니다.

    Args:
        symbol: 특정 심볼로 필터링 (선택사항)

    Returns:
        데이터 요약 정보
    """
    try:
        logger.info("data_summary_api_called", symbol=symbol)

        # 핸들러를 통한 데이터 요약 요청
        result = await recovery_handler.handle_data_summary_request(symbol)

        return result

    except Exception as e:
        logger.error("data_summary_api_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"데이터 요약 조회 실패: {str(e)}")


@router.delete("/cleanup", summary="테스트 데이터 정리")
async def cleanup_test_data(
    data_types: List[str] = Query(
        ["test_signals", "test_patterns"], description="정리할 데이터 타입들"
    ),
    confirm: bool = Query(False, description="정리 확인 (안전장치)"),
) -> Dict[str, Any]:
    """
    테스트용으로 생성된 데이터를 정리합니다.

    Args:
        data_types: 정리할 데이터 타입들
        confirm: 정리 확인 (True여야 실행됨)

    Returns:
        정리 결과
    """
    try:
        logger.info(
            "cleanup_test_data_api_called", data_types=data_types, confirm=confirm
        )

        # 핸들러를 통한 테스트 데이터 정리
        result = await recovery_handler.handle_test_data_cleanup(data_types, confirm)

        return result

    except Exception as e:
        logger.error("cleanup_test_data_api_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"테스트 데이터 정리 실패: {str(e)}"
        )


@router.get("/health", summary="복구 서비스 상태 확인")
async def health_check() -> Dict[str, Any]:
    """복구 서비스의 상태를 확인합니다."""
    try:
        logger.info("recovery_health_check_api_called")

        # 핸들러를 통한 헬스 체크
        result = recovery_handler.handle_health_check()

        return result

    except Exception as e:
        logger.error("recovery_health_check_api_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"헬스 체크 실패: {str(e)}")
