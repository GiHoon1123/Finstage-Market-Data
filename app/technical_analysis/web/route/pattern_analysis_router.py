"""
패턴 분석 API 라우터

패턴 자동 발견, 성과 분석, 성공적인 패턴 조회 등의 기능을 제공합니다.
"""

from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, Dict, Any
from app.technical_analysis.service.pattern_analysis_service import (
    PatternAnalysisService,
)

# 라우터 생성
router = APIRouter()

# 서비스 인스턴스
pattern_analysis_service = PatternAnalysisService()


# =============================================================================
# 패턴 분석 API
# =============================================================================


@router.post("/discover/{symbol}", summary="패턴 자동 발견")
async def discover_patterns(
    symbol: str = Path(..., description="분석할 심볼 (예: NQ=F)"),
    timeframe: str = Query("15min", description="시간대 (1min, 15min, 1day)"),
) -> Dict[str, Any]:
    """
    특정 심볼에서 반복되는 신호 패턴을 자동으로 발견합니다.

    여러 기술적 신호들이 특정 순서로 발생하는 패턴을 찾아내어
    더 정확한 매매 신호를 만들 수 있습니다.

    Args:
        symbol: 패턴을 찾을 심볼
        timeframe: 분석할 시간대

    Returns:
        발견된 패턴 정보
        - discovered_patterns: 발견된 패턴 후보 개수
        - saved_patterns: 실제 저장된 패턴 개수
        - patterns: 저장된 패턴들의 상세 정보
    """
    try:
        result = pattern_analysis_service.discover_patterns(
            symbol=symbol, timeframe=timeframe
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"패턴 발견 실패: {str(e)}")


@router.get("/analysis", summary="패턴 성과 분석")
async def get_pattern_analysis(
    pattern_name: Optional[str] = Query(None, description="분석할 패턴명"),
    symbol: Optional[str] = Query(None, description="심볼 필터"),
    min_occurrences: int = Query(5, description="최소 발생 횟수", ge=1, le=50),
) -> Dict[str, Any]:
    """
    저장된 패턴들의 성과를 분석합니다.

    각 패턴이 얼마나 자주 발생하고, 성공률이 어떻게 되는지 분석하여
    가장 효과적인 패턴을 찾을 수 있습니다.

    Args:
        pattern_name: 특정 패턴만 분석 (None이면 모든 패턴)
        symbol: 특정 심볼로 필터링
        min_occurrences: 분석에 포함할 최소 발생 횟수

    Returns:
        패턴 성과 분석 결과
        - summary: 전체 패턴 요약
        - pattern_analysis: 패턴별 상세 분석
        - filters: 적용된 필터 조건
    """
    try:
        result = pattern_analysis_service.analyze_pattern_performance(
            pattern_name=pattern_name, symbol=symbol, min_occurrences=min_occurrences
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"패턴 분석 실패: {str(e)}")


@router.get("/successful", summary="성공적인 패턴 조회")
async def get_successful_patterns(
    symbol: Optional[str] = Query(None, description="심볼 필터"),
    success_threshold: float = Query(0.7, description="성공 임계값", ge=0.1, le=1.0),
    min_occurrences: int = Query(3, description="최소 발생 횟수", ge=1, le=20),
) -> Dict[str, Any]:
    """
    높은 성공률을 보이는 패턴들을 조회합니다.

    설정한 성공률 이상의 패턴들만 필터링하여
    실제 매매에 활용할 수 있는 고품질 패턴을 찾습니다.

    Args:
        symbol: 특정 심볼로 필터링
        success_threshold: 성공률 기준 (0.7 = 70% 이상)
        min_occurrences: 최소 발생 횟수

    Returns:
        성공적인 패턴 목록
        - successful_patterns: 기준을 만족하는 패턴들
        - criteria: 적용된 기준
        - summary: 분석 요약
    """
    try:
        result = pattern_analysis_service.find_successful_patterns(
            symbol=symbol,
            success_threshold=success_threshold,
            min_occurrences=min_occurrences,
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"성공적인 패턴 조회 실패: {str(e)}"
        )


@router.post("/test/{symbol}", summary="패턴 분석 테스트")
async def test_pattern_analysis(
    symbol: str = Path(..., description="테스트할 심볼"),
) -> Dict[str, Any]:
    """
    패턴 분석 기능을 테스트합니다. (개발용)

    가상의 패턴 데이터를 생성하여 패턴 분석 시스템이
    정상적으로 동작하는지 확인합니다.

    Args:
        symbol: 테스트에 사용할 심볼

    Returns:
        테스트 결과
    """
    try:
        result = pattern_analysis_service.test_pattern_analysis(symbol=symbol)

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"패턴 분석 테스트 실패: {str(e)}")


@router.delete("/test/{symbol}", summary="테스트 패턴 정리")
async def cleanup_test_patterns(
    symbol: str = Path(..., description="정리할 심볼"),
) -> Dict[str, Any]:
    """
    테스트용으로 생성된 패턴 데이터를 정리합니다. (개발용)

    Args:
        symbol: 정리할 심볼

    Returns:
        정리 결과
    """
    try:
        result = pattern_analysis_service.cleanup_test_patterns(symbol=symbol)

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"테스트 패턴 정리 실패: {str(e)}")