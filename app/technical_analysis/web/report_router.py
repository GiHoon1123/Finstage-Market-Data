"""
리포트 생성 API 라우터

리포트 생성을 백그라운드 처리로 최적화한 엔드포인트들
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta

from app.common.utils.async_executor import async_timed
from app.common.utils.logging_config import get_logger
from app.common.utils.memory_optimizer import memory_monitor
from app.common.utils.task_queue import TaskQueue, TaskPriority
from app.common.services.background_tasks import (
    run_daily_comprehensive_report_background,
)
from app.common.constants.symbol_names import SYMBOL_PRICE_MAP

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v2/reports", tags=["Background Reports"])


@router.post("/comprehensive/background", summary="종합 리포트 백그라운드 생성")
@async_timed()
@memory_monitor
async def generate_comprehensive_report_background(
    background_tasks: BackgroundTasks,
    symbols: List[str] = Query(..., description="리포트 생성할 심볼 리스트"),
    priority: str = Query("medium", description="작업 우선순위 (high, medium, low)"),
) -> Dict[str, Any]:
    """
    종합 리포트 생성을 백그라운드 작업으로 큐에 추가합니다.

    Args:
        symbols: 리포트 생성할 심볼 리스트
        priority: 작업 우선순위

    Returns:
        작업 큐잉 결과
    """
    try:
        logger.info(
            "comprehensive_report_background_queuing_started",
            symbol_count=len(symbols),
            priority=priority,
        )

        # 우선순위 매핑
        priority_map = {
            "high": TaskPriority.HIGH,
            "medium": TaskPriority.MEDIUM,
            "low": TaskPriority.LOW,
        }

        task_priority = priority_map.get(priority, TaskPriority.MEDIUM)

        # 작업 큐에 종합 리포트 생성 작업 추가
        task_queue = TaskQueue()
        task_id = await task_queue.enqueue_task(
            run_daily_comprehensive_report_background,
            symbols=symbols,
            priority=task_priority,
        )

        logger.info(
            "comprehensive_report_background_queued",
            task_id=task_id,
            symbol_count=len(symbols),
        )

        return {
            "status": "queued",
            "task_id": task_id,
            "symbols": symbols,
            "priority": priority,
            "estimated_completion": "15-30 minutes",
            "queued_at": datetime.now().isoformat(),
            "check_status_url": f"/api/v2/reports/status/{task_id}",
        }

    except Exception as e:
        logger.error("comprehensive_report_background_queuing_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"종합 리포트 백그라운드 생성 큐잉 실패: {str(e)}"
        )


@router.get("/status/{task_id}", summary="리포트 생성 작업 상태 조회")
@async_timed()
@memory_monitor
async def get_report_generation_status(task_id: str) -> Dict[str, Any]:
    """
    백그라운드 리포트 생성 작업의 상태를 조회합니다.

    Args:
        task_id: 작업 ID

    Returns:
        작업 상태 정보
    """
    try:
        task_queue = TaskQueue()
        status = await task_queue.get_task_status(task_id)

        return {
            "task_id": task_id,
            "status": status.get("status", "unknown"),
            "progress": status.get("progress", 0),
            "result": status.get("result"),
            "error": status.get("error"),
            "created_at": status.get("created_at"),
            "completed_at": status.get("completed_at"),
            "estimated_remaining": status.get("estimated_remaining"),
        }

    except Exception as e:
        logger.error(
            "report_generation_status_query_failed", task_id=task_id, error=str(e)
        )
        raise HTTPException(
            status_code=500, detail=f"리포트 생성 상태 조회 실패: {str(e)}"
        )


@router.get("/result/{task_id}", summary="리포트 생성 결과 조회")
@async_timed()
@memory_monitor
async def get_report_generation_result(task_id: str) -> Dict[str, Any]:
    """
    완료된 리포트 생성 작업의 결과를 조회합니다.

    Args:
        task_id: 작업 ID

    Returns:
        리포트 생성 결과
    """
    try:
        task_queue = TaskQueue()
        result = await task_queue.get_task_result(task_id)

        if not result:
            raise HTTPException(
                status_code=404, detail=f"작업 ID {task_id}의 결과를 찾을 수 없습니다"
            )

        return {
            "task_id": task_id,
            "result": result,
            "retrieved_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(
            "report_generation_result_query_failed", task_id=task_id, error=str(e)
        )
        raise HTTPException(
            status_code=500, detail=f"리포트 생성 결과 조회 실패: {str(e)}"
        )


@router.post("/daily/schedule", summary="일일 리포트 스케줄링")
@async_timed()
@memory_monitor
async def schedule_daily_reports(
    symbols: List[str] = Query(None, description="리포트 생성할 심볼 리스트"),
    schedule_time: str = Query("06:00", description="실행 시간 (HH:MM 형식)"),
    enabled: bool = Query(True, description="스케줄 활성화 여부"),
) -> Dict[str, Any]:
    """
    일일 리포트 자동 생성을 스케줄링합니다.

    Args:
        symbols: 리포트 생성할 심볼 리스트 (None이면 기본 심볼들)
        schedule_time: 실행 시간
        enabled: 스케줄 활성화 여부

    Returns:
        스케줄링 결과
    """
    try:
        if not symbols:
            symbols = ["^IXIC", "^GSPC", "^DJI"]  # 기본 지수들

        logger.info(
            "daily_reports_scheduling_started",
            symbol_count=len(symbols),
            schedule_time=schedule_time,
        )

        # 스케줄링 로직 (실제로는 스케줄러에 등록)
        # 여기서는 시뮬레이션

        return {
            "status": "scheduled" if enabled else "disabled",
            "symbols": symbols,
            "schedule_time": schedule_time,
            "next_execution": f"매일 {schedule_time}",
            "scheduled_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("daily_reports_scheduling_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"일일 리포트 스케줄링 실패: {str(e)}"
        )


@router.get("/queue/status", summary="리포트 생성 큐 상태")
@memory_monitor
async def get_report_queue_status() -> Dict[str, Any]:
    """
    리포트 생성 작업 큐의 현재 상태를 조회합니다.

    Returns:
        큐 상태 정보
    """
    try:
        task_queue = TaskQueue()
        queue_stats = await task_queue.get_queue_stats()

        return {"queue_stats": queue_stats, "timestamp": datetime.now().isoformat()}

    except Exception as e:
        logger.error("report_queue_status_query_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"리포트 큐 상태 조회 실패: {str(e)}"
        )


@router.post("/batch/comprehensive", summary="배치 종합 리포트 생성")
@async_timed()
@memory_monitor
async def generate_batch_comprehensive_reports(
    background_tasks: BackgroundTasks,
    symbol_groups: Dict[str, List[str]] = Query(..., description="그룹별 심볼 리스트"),
    priority: str = Query("medium", description="작업 우선순위"),
) -> Dict[str, Any]:
    """
    여러 그룹의 심볼들에 대해 배치로 종합 리포트를 생성합니다.

    Args:
        symbol_groups: 그룹별 심볼 리스트 (예: {"indices": ["^IXIC", "^GSPC"], "stocks": ["AAPL", "MSFT"]})
        priority: 작업 우선순위

    Returns:
        배치 작업 큐잉 결과
    """
    try:
        logger.info(
            "batch_comprehensive_reports_queuing_started",
            group_count=len(symbol_groups),
        )

        # 우선순위 매핑
        priority_map = {
            "high": TaskPriority.HIGH,
            "medium": TaskPriority.MEDIUM,
            "low": TaskPriority.LOW,
        }

        task_priority = priority_map.get(priority, TaskPriority.MEDIUM)
        task_queue = TaskQueue()
        task_ids = {}

        # 각 그룹별로 별도 작업 생성
        for group_name, symbols in symbol_groups.items():
            task_id = await task_queue.enqueue_task(
                run_daily_comprehensive_report_background,
                symbols=symbols,
                priority=task_priority,
            )
            task_ids[group_name] = task_id

            logger.info(
                "group_comprehensive_report_queued",
                group=group_name,
                task_id=task_id,
                symbol_count=len(symbols),
            )

        total_symbols = sum(len(symbols) for symbols in symbol_groups.values())

        return {
            "status": "queued",
            "task_ids": task_ids,
            "symbol_groups": symbol_groups,
            "total_symbols": total_symbols,
            "priority": priority,
            "estimated_completion": "20-45 minutes",
            "queued_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("batch_comprehensive_reports_queuing_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"배치 종합 리포트 생성 큐잉 실패: {str(e)}"
        )


@router.delete("/task/{task_id}", summary="리포트 생성 작업 취소")
@async_timed()
@memory_monitor
async def cancel_report_generation_task(task_id: str) -> Dict[str, Any]:
    """
    진행 중인 리포트 생성 작업을 취소합니다.

    Args:
        task_id: 취소할 작업 ID

    Returns:
        작업 취소 결과
    """
    try:
        task_queue = TaskQueue()
        cancelled = await task_queue.cancel_task(task_id)

        if cancelled:
            logger.info("report_generation_task_cancelled", task_id=task_id)
            return {
                "status": "cancelled",
                "task_id": task_id,
                "cancelled_at": datetime.now().isoformat(),
            }
        else:
            return {
                "status": "not_cancelled",
                "task_id": task_id,
                "reason": "Task may be already completed or not found",
            }

    except Exception as e:
        logger.error(
            "report_generation_task_cancellation_failed", task_id=task_id, error=str(e)
        )
        raise HTTPException(
            status_code=500, detail=f"리포트 생성 작업 취소 실패: {str(e)}"
        )
