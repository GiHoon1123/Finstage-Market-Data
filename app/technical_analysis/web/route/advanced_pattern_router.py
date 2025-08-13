"""
고급 패턴 분석 라우터

머신러닝과 통계 기법을 활용한 고급 패턴 분석 API를 제공합니다.
"""

from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional
from app.technical_analysis.service.advanced_pattern_service import (
    AdvancedPatternService,
)
from app.technical_analysis.dto.pattern_response import (
    PatternSimilarityResponse,
    PatternClusterResponse,
    HealthCheckResponse,
)
from app.common.config.api_metadata import common_responses
from app.common.dto.api_response import ApiResponse
from app.common.utils.response_helper import (
    success_response,
    handle_service_error,
)

router = APIRouter()
advanced_pattern_service = AdvancedPatternService()


@router.get(
    "/similarity-matrix/{symbol}",
    response_model=ApiResponse,
    summary="패턴 유사도 매트릭스 분석",
    description="""
    특정 심볼의 차트 패턴들 간의 유사도를 분석합니다.
    
    **주요 기능:**
    - 머신러닝 기반 패턴 유사도 계산
    - 패턴 간 상관관계 분석
    - 반복되는 패턴 식별
    - 패턴 빈도 분석
    
    **활용 방안:**
    - 유사한 패턴의 성과 예측
    - 패턴 기반 매매 전략 개발
    - 시장 사이클 분석
    """,
    tags=["Pattern Analysis"],
    responses={
        **common_responses,
        200: {
            "description": "패턴 유사도 분석이 완료되었습니다.",
            "content": {
                "application/json": {
                    "example": {
                        "status": 200,
                        "message": "AAPL 패턴 유사도 분석이 완료되었습니다",
                        "data": {
                            "symbol": "AAPL",
                            "pattern_type": "sequential",
                            "similarity_matrix": [
                                [1.0, 0.85, 0.72],
                                [0.85, 1.0, 0.78],
                                [0.72, 0.78, 1.0]
                            ],
                            "patterns": [
                                {"id": "pattern_1", "similarity_score": 0.85},
                                {"id": "pattern_2", "similarity_score": 0.72}
                            ],
                            "analysis_timestamp": "2025-08-13T13:30:00Z"
                        }
                    }
                }
            },
        },
    },
)
async def get_pattern_similarity_matrix(
    symbol: str = Path(..., example="AAPL", description="분석할 주식 심볼"),
    pattern_type: str = Query(default="sequential", description="패턴 타입"),
) -> ApiResponse:
    """
    패턴 간 유사도 매트릭스 분석

    - **symbol**: 분석할 심볼 (예: AAPL, TSLA)
    - **pattern_type**: 패턴 타입 (기본값: sequential)

    코사인 유사도와 유클리드 거리를 기반으로 패턴 간 유사도를 계산합니다.
    """
    try:
        result = advanced_pattern_service.calculate_pattern_similarity_matrix(
            symbol=symbol, pattern_type=pattern_type
        )

        if "error" in result:
            handle_service_error(Exception(result["error"]), "패턴 유사도 분석 실패")

        return success_response(
            data=result,
            message=f"{symbol} 패턴 유사도 분석이 완료되었습니다"
        )

    except Exception as e:
        handle_service_error(e, "패턴 유사도 분석 실패")


@router.get("/clustering/{symbol}")
async def cluster_patterns(
    symbol: str,
    n_clusters: int = Query(default=5, ge=2, le=20, description="클러스터 개수"),
    min_patterns: int = Query(default=10, ge=5, description="최소 패턴 개수"),
) -> ApiResponse:
    """
    패턴 클러스터링을 통한 그룹화

    - **symbol**: 분석할 심볼
    - **n_clusters**: 생성할 클러스터 개수 (2-20)
    - **min_patterns**: 클러스터링에 필요한 최소 패턴 개수

    K-means 클러스터링을 사용하여 유사한 패턴들을 자동으로 그룹화합니다.
    """
    try:
        result = advanced_pattern_service.cluster_patterns(
            symbol=symbol, n_clusters=n_clusters, min_patterns=min_patterns
        )

        if "error" in result:
            handle_service_error(Exception(result["error"]), "패턴 클러스터링 실패")

        return success_response(
            data=result,
            message=f"{symbol} 패턴 클러스터링이 완료되었습니다 ({n_clusters}개 클러스터)"
        )

    except Exception as e:
        handle_service_error(e, "패턴 클러스터링 실패")


@router.get("/temporal-analysis/{symbol}")
async def analyze_temporal_patterns(
    symbol: str,
    timeframe: str = Query(
        default="1h", description="시간대 (1m, 5m, 15m, 1h, 4h, 1d)"
    ),
    days: int = Query(default=30, ge=7, le=365, description="분석 기간 (일)"),
) -> ApiResponse:
    """
    시계열 패턴 분석

    - **symbol**: 분석할 심볼
    - **timeframe**: 분석할 시간대
    - **days**: 분석 기간 (7-365일)

    패턴의 시간적 특성을 분석하여 발생 빈도, 계절성, 주기성을 파악합니다.
    """
    try:
        result = advanced_pattern_service.analyze_temporal_patterns(
            symbol=symbol, timeframe=timeframe, days=days
        )

        if "error" in result:
            handle_service_error(Exception(result["error"]), "시계열 패턴 분석 실패")

        return success_response(
            data=result,
            message=f"{symbol} 시계열 패턴 분석이 완료되었습니다 ({timeframe}, {days}일)"
        )

    except Exception as e:
        handle_service_error(e, "시계열 패턴 분석 실패")


@router.get("/health")
async def health_check() -> ApiResponse:
    """고급 패턴 분석 서비스 상태 확인"""
    health_data = {
        "service": "Advanced Pattern Analysis",
        "status": "healthy",
        "features": [
            "패턴 유사도 분석",
            "클러스터링 기반 패턴 그룹화",
            "시계열 패턴 분석",
            "머신러닝 기반 패턴 매칭",
        ],
    }
    
    return success_response(
        data=health_data,
        message="고급 패턴 분석 서비스가 정상적으로 작동 중입니다"
    )
