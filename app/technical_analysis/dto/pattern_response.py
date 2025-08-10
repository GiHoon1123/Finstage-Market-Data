from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


class PatternSimilarityResponse(BaseModel):
    """패턴 유사도 분석 응답 모델"""

    symbol: str = Field(..., example="AAPL", description="분석한 심볼")
    similarity_matrix: Dict[str, Any] = Field(..., description="패턴 유사도 매트릭스")
    analysis_period: str = Field(..., example="1y", description="분석 기간")
    pattern_count: int = Field(..., example=15, description="발견된 패턴 수", ge=0)
    timestamp: str = Field(..., example="2025-08-09T12:00:00Z", description="분석 시간")

    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "similarity_matrix": {
                    "pattern_1": {"similarity": 0.85, "frequency": 12},
                    "pattern_2": {"similarity": 0.72, "frequency": 8},
                },
                "analysis_period": "1y",
                "pattern_count": 15,
                "timestamp": "2025-08-09T12:00:00Z",
            }
        }


class PatternClusterResponse(BaseModel):
    """패턴 클러스터링 응답 모델"""

    symbol: str = Field(..., example="AAPL", description="분석한 심볼")
    clusters: List[Dict[str, Any]] = Field(..., description="클러스터 정보")
    cluster_count: int = Field(..., example=5, description="클러스터 수", ge=0)
    silhouette_score: Optional[float] = Field(
        None, example=0.65, description="실루엣 점수 (클러스터링 품질)", ge=-1.0, le=1.0
    )
    timestamp: str = Field(..., example="2025-08-09T12:00:00Z", description="분석 시간")

    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "clusters": [
                    {"cluster_id": 0, "size": 25, "center": [0.1, 0.2, 0.3]},
                    {"cluster_id": 1, "size": 18, "center": [0.4, 0.5, 0.6]},
                ],
                "cluster_count": 5,
                "silhouette_score": 0.65,
                "timestamp": "2025-08-09T12:00:00Z",
            }
        }


class HealthCheckResponse(BaseModel):
    """헬스 체크 응답 모델"""

    status: str = Field(..., example="healthy", description="서비스 상태")
    service_name: str = Field(
        ..., example="Advanced Pattern Analysis", description="서비스명"
    )
    uptime: str = Field(..., example="2h 30m", description="가동 시간")
    version: str = Field(..., example="1.0.0", description="서비스 버전")
    dependencies: Dict[str, str] = Field(..., description="의존성 상태")
    timestamp: str = Field(..., example="2025-08-09T12:00:00Z", description="확인 시간")

    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "service_name": "Advanced Pattern Analysis",
                "uptime": "2h 30m",
                "version": "1.0.0",
                "dependencies": {
                    "database": "connected",
                    "cache": "available",
                    "ml_engine": "ready",
                },
                "timestamp": "2025-08-09T12:00:00Z",
            }
        }
