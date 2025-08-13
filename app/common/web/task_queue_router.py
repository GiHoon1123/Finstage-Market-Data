"""
작업 큐 관리 API 라우터

분산 작업 큐 시스템을 관리하고 모니터링하는 API 엔드포인트들을 제공합니다.
작업 제출, 상태 조회, 결과 확인, 시스템 통계 등을 지원합니다.
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.common.utils.task_queue import task_queue, TaskPriority, TaskStatus
from app.common.services.background_tasks import (
    submit_background_task,
    get_task_progress,
)
from app.common.utils.logging_config import get_logger
from app.common.dto.api_response import ApiResponse
from app.common.utils.response_helper import (
    success_response,
    not_found_response,
    handle_service_error,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/api/tasks", tags=["Task Queue Management"])


@router.get("/status", summary="작업 큐 시스템 상태")
async def get_task_queue_status() -> ApiResponse:
    """작업 큐 시스템의 전체 상태를 조회합니다."""
    try:
        stats = task_queue.get_stats()
        response_data = {
            "timestamp": datetime.now().isoformat(),
            "system_status": "running" if task_queue.is_running else "stopped",
            "queue_statistics": stats,
        }
        
        return success_response(
            data=response_data,
            message="작업 큐 시스템 상태 조회 완료"
        )
    except Exception as e:
        handle_service_error(e, "작업 큐 시스템 상태 조회 실패")


@router.post("/submit", summary="백그라운드 작업 제출")
async def submit_task(
    task_name: str = Query(
        ..., description="작업 이름 (process_dataset, generate_report, etc.)"
    ),
    priority: str = Query(
        "normal", description="작업 우선순위 (low, normal, high, critical)"
    ),
    args: Optional[str] = Query(None, description="작업 인자들 (JSON 형식)"),
    kwargs: Optional[str] = Query(None, description="작업 키워드 인자들 (JSON 형식)"),
) -> ApiResponse:
    """백그라운드 작업을 큐에 제출합니다."""
    try:
        # 우선순위 변환
        priority_mapping = {
            "low": TaskPriority.LOW,
            "normal": TaskPriority.NORMAL,
            "high": TaskPriority.HIGH,
            "critical": TaskPriority.CRITICAL,
        }

        task_priority = priority_mapping.get(priority.lower(), TaskPriority.NORMAL)

        # 인자 파싱
        import json

        parsed_args = json.loads(args) if args else []
        parsed_kwargs = json.loads(kwargs) if kwargs else {}

        # 작업 제출
        task_id = await submit_background_task(
            task_name, *parsed_args, priority=task_priority, **parsed_kwargs
        )

        response_data = {
            "task_id": task_id,
            "task_name": task_name,
            "priority": priority,
            "submitted_at": datetime.now().isoformat(),
        }
        
        return success_response(
            data=response_data,
            message="작업이 성공적으로 제출되었습니다"
        )

    except json.JSONDecodeError as e:
        handle_service_error(e, "JSON 파싱 오류")
    except ValueError as e:
        handle_service_error(e, "잘못된 요청")
    except Exception as e:
        handle_service_error(e, "작업 제출 실패")


@router.get("/task/{task_id}", summary="작업 상태 조회")
async def get_task_status(task_id: str) -> ApiResponse:
    """특정 작업의 상태와 진행 상황을 조회합니다."""
    try:
        progress = await get_task_progress(task_id)

        if "error" in progress:
            not_found_response(progress["error"])

        return success_response(
            data=progress,
            message=f"작업 {task_id} 상태 조회 완료"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"작업 상태 조회 실패: {str(e)}")


@router.get("/task/{task_id}/result", summary="작업 결과 조회")
async def get_task_result(task_id: str):
    """완료된 작업의 결과를 조회합니다."""
    try:
        result = task_queue.get_task_result(task_id)

        if not result:
            raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")

        if result.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            raise HTTPException(
                status_code=400,
                detail=f"작업이 아직 완료되지 않았습니다. 현재 상태: {result.status.value}",
            )

        response = {
            "task_id": task_id,
            "status": result.status.value,
            "completed_at": (
                result.completed_at.isoformat() if result.completed_at else None
            ),
            "execution_time": result.execution_time,
            "worker_id": result.worker_id,
        }

        if result.status == TaskStatus.COMPLETED:
            response["result"] = result.result
        else:
            response["error"] = result.error

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"작업 결과 조회 실패: {str(e)}")


@router.post("/task/{task_id}/cancel", summary="작업 취소")
async def cancel_task(task_id: str):
    """대기 중인 작업을 취소합니다."""
    try:
        success = task_queue.cancel_task(task_id)

        if success:
            return {
                "success": True,
                "task_id": task_id,
                "message": "작업이 성공적으로 취소되었습니다",
                "cancelled_at": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "task_id": task_id,
                "message": "작업을 취소할 수 없습니다 (이미 실행 중이거나 완료됨)",
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"작업 취소 실패: {str(e)}")


@router.get("/workers", summary="워커 상태 조회")
async def get_worker_status():
    """모든 워커의 상태를 조회합니다."""
    try:
        stats = task_queue.get_stats()
        worker_stats = stats.get("worker_stats", [])

        return {
            "timestamp": datetime.now().isoformat(),
            "total_workers": len(worker_stats),
            "active_workers": sum(1 for w in worker_stats if w["is_running"]),
            "workers": worker_stats,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"워커 상태 조회 실패: {str(e)}")


@router.get("/queue/stats", summary="큐 통계")
async def get_queue_statistics():
    """작업 큐의 상세 통계를 조회합니다."""
    try:
        stats = task_queue.get_stats()

        return {
            "timestamp": datetime.now().isoformat(),
            "queue_stats": stats["queue_stats"],
            "status_counts": stats["status_counts"],
            "registered_functions": stats["registered_functions"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"큐 통계 조회 실패: {str(e)}")


@router.post("/system/start", summary="작업 큐 시스템 시작")
async def start_task_queue_system():
    """작업 큐 시스템을 시작합니다."""
    try:
        if task_queue.is_running:
            return {"success": False, "message": "작업 큐 시스템이 이미 실행 중입니다"}

        await task_queue.start()

        return {
            "success": True,
            "message": "작업 큐 시스템이 시작되었습니다",
            "started_at": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시스템 시작 실패: {str(e)}")


@router.post("/system/stop", summary="작업 큐 시스템 중지")
async def stop_task_queue_system():
    """작업 큐 시스템을 중지합니다."""
    try:
        if not task_queue.is_running:
            return {"success": False, "message": "작업 큐 시스템이 실행 중이 아닙니다"}

        await task_queue.stop()

        return {
            "success": True,
            "message": "작업 큐 시스템이 중지되었습니다",
            "stopped_at": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시스템 중지 실패: {str(e)}")


@router.post("/maintenance/cleanup", summary="오래된 작업 결과 정리")
async def cleanup_old_results(
    max_age_hours: int = Query(24, description="보관할 최대 시간 (시간)", ge=1, le=168)
):
    """오래된 작업 결과를 정리합니다."""
    try:
        task_queue.cleanup_old_results(max_age_hours)

        return {
            "success": True,
            "message": f"{max_age_hours}시간 이전의 작업 결과가 정리되었습니다",
            "cleaned_at": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"정리 작업 실패: {str(e)}")


# =============================================================================
# 편의 엔드포인트들 (자주 사용되는 작업들)
# =============================================================================


@router.post("/quick/dataset-processing", summary="데이터셋 처리 작업 제출")
async def submit_dataset_processing(
    symbol: str = Query(..., description="처리할 심볼"),
    period: str = Query("1y", description="데이터 기간"),
    priority: str = Query("high", description="작업 우선순위"),
):
    """대용량 데이터셋 처리 작업을 제출합니다."""
    try:
        task_priority = {
            "low": TaskPriority.LOW,
            "normal": TaskPriority.NORMAL,
            "high": TaskPriority.HIGH,
            "critical": TaskPriority.CRITICAL,
        }.get(priority.lower(), TaskPriority.HIGH)

        task_id = await submit_background_task(
            "process_dataset", symbol, period, priority=task_priority
        )

        return {
            "success": True,
            "task_id": task_id,
            "symbol": symbol,
            "period": period,
            "priority": priority,
            "message": f"{symbol} 데이터셋 처리 작업이 제출되었습니다",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"데이터셋 처리 작업 제출 실패: {str(e)}"
        )


@router.post("/quick/daily-report", summary="일일 리포트 생성 작업 제출")
async def submit_daily_report(
    symbols: str = Query(..., description="리포트 생성할 심볼들 (쉼표로 구분)"),
    date: Optional[str] = Query(None, description="리포트 날짜 (YYYY-MM-DD)"),
):
    """일일 리포트 생성 작업을 제출합니다."""
    try:
        symbol_list = [s.strip() for s in symbols.split(",")]

        task_id = await submit_background_task(
            "generate_report", symbol_list, date, priority=TaskPriority.NORMAL
        )

        return {
            "success": True,
            "task_id": task_id,
            "symbols": symbol_list,
            "date": date or "today",
            "message": f"{len(symbol_list)}개 심볼의 일일 리포트 생성 작업이 제출되었습니다",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"일일 리포트 작업 제출 실패: {str(e)}"
        )


@router.post("/quick/market-analysis", summary="시장 분석 작업 제출")
async def submit_market_analysis(
    analysis_type: str = Query("comprehensive", description="분석 유형")
):
    """시장 분석 작업을 제출합니다."""
    try:
        task_id = await submit_background_task(
            "market_analysis", analysis_type, priority=TaskPriority.NORMAL
        )

        return {
            "success": True,
            "task_id": task_id,
            "analysis_type": analysis_type,
            "message": f"{analysis_type} 시장 분석 작업이 제출되었습니다",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"시장 분석 작업 제출 실패: {str(e)}"
        )


@router.post("/quick/data-cleanup", summary="데이터 정리 작업 제출")
async def submit_data_cleanup(
    days_to_keep: int = Query(30, description="보관할 일수", ge=1, le=365)
):
    """데이터 정리 작업을 제출합니다."""
    try:
        task_id = await submit_background_task(
            "cleanup_data", days_to_keep, priority=TaskPriority.LOW
        )

        return {
            "success": True,
            "task_id": task_id,
            "days_to_keep": days_to_keep,
            "message": f"{days_to_keep}일 이전 데이터 정리 작업이 제출되었습니다",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"데이터 정리 작업 제출 실패: {str(e)}"
        )


@router.get("/dashboard", summary="작업 큐 대시보드 데이터")
async def get_dashboard_data():
    """작업 큐 대시보드용 종합 데이터를 조회합니다."""
    try:
        stats = task_queue.get_stats()

        # 최근 작업들 (최대 10개)
        recent_tasks = []
        for task_id, result in list(task_queue.task_results.items())[-10:]:
            recent_tasks.append(
                {
                    "task_id": task_id,
                    "status": result.status.value,
                    "started_at": (
                        result.started_at.isoformat() if result.started_at else None
                    ),
                    "execution_time": result.execution_time,
                    "worker_id": result.worker_id,
                }
            )

        return {
            "timestamp": datetime.now().isoformat(),
            "system_status": "running" if task_queue.is_running else "stopped",
            "summary": {
                "total_workers": len(stats["worker_stats"]),
                "active_workers": sum(
                    1 for w in stats["worker_stats"] if w["is_running"]
                ),
                "pending_tasks": stats["queue_stats"]["pending_tasks"],
                "total_submitted": stats["queue_stats"]["total_submitted"],
                "success_rate": stats["queue_stats"]["success_rate"],
            },
            "status_distribution": stats["status_counts"],
            "recent_tasks": recent_tasks,
            "worker_performance": [
                {
                    "worker_id": w["worker_id"],
                    "processed_tasks": w["processed_tasks"],
                    "success_rate": w["success_rate"],
                    "current_task": w["current_task_id"],
                }
                for w in stats["worker_stats"]
            ],
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"대시보드 데이터 조회 실패: {str(e)}"
        )
