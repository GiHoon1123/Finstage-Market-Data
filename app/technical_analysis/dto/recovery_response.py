from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


class RecoveryTaskResponse(BaseModel):
    """복구 작업 응답 모델"""

    task_id: str = Field(
        ..., example="recovery_20250809_001", description="복구 작업 ID"
    )
    task_type: str = Field(..., example="historical_data", description="복구 작업 타입")
    status: str = Field(..., example="queued", description="작업 상태")
    symbols: List[str] = Field(..., description="복구 대상 심볼 목록")
    estimated_duration: str = Field(
        ..., example="30-60 minutes", description="예상 소요 시간"
    )
    started_at: str = Field(
        ..., example="2025-08-09T12:00:00Z", description="시작 시간"
    )

    class Config:
        schema_extra = {
            "example": {
                "task_id": "recovery_20250809_001",
                "task_type": "historical_data",
                "status": "queued",
                "symbols": ["AAPL", "MSFT", "GOOGL"],
                "estimated_duration": "30-60 minutes",
                "started_at": "2025-08-09T12:00:00Z",
            }
        }


class RecoveryStatusResponse(BaseModel):
    """복구 상태 응답 모델"""

    active_tasks: int = Field(..., example=2, description="진행 중인 작업 수", ge=0)
    completed_tasks: int = Field(..., example=15, description="완료된 작업 수", ge=0)
    failed_tasks: int = Field(..., example=1, description="실패한 작업 수", ge=0)
    total_recovered_symbols: int = Field(
        ..., example=150, description="복구된 총 심볼 수", ge=0
    )
    last_recovery: Optional[str] = Field(
        None, example="2025-08-09T10:30:00Z", description="마지막 복구 시간"
    )

    class Config:
        schema_extra = {
            "example": {
                "active_tasks": 2,
                "completed_tasks": 15,
                "failed_tasks": 1,
                "total_recovered_symbols": 150,
                "last_recovery": "2025-08-09T10:30:00Z",
            }
        }
