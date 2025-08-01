"""
메모리 관리 API 라우터

메모리 상태 조회, 최적화 실행, 진단 정보 등을 제공하는 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from datetime import datetime

from app.common.utils.memory_utils import (
    get_memory_status,
    optimize_memory,
    check_memory_health,
    get_memory_diagnostics,
    integrated_memory_manager,
)
from app.common.utils.memory_cache import cache_manager
from app.common.utils.memory_optimizer import memory_manager

router = APIRouter(prefix="/api/memory", tags=["Memory Management"])


@router.get("/status", summary="메모리 상태 조회")
async def get_system_memory_status() -> Dict[str, Any]:
    """
    현재 시스템 메모리 상태를 조회합니다.

    Returns:
        시스템 메모리, 캐시 상태, 성능 트렌드 등 종합 정보
    """
    try:
        return get_memory_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"메모리 상태 조회 실패: {str(e)}")


@router.get("/health", summary="메모리 건강 상태 체크")
async def check_system_memory_health() -> Dict[str, Any]:
    """
    메모리 건강 상태를 간단히 체크합니다.

    Returns:
        건강 상태, 메모리 사용률, 권장사항 등
    """
    try:
        return check_memory_health()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"메모리 건강 상태 체크 실패: {str(e)}"
        )


@router.post("/optimize", summary="메모리 최적화 실행")
async def optimize_system_memory(
    aggressive: bool = Query(False, description="공격적 최적화 여부 (정밀도 손실 가능)")
) -> Dict[str, Any]:
    """
    시스템 메모리 최적화를 실행합니다.

    Args:
        aggressive: 공격적 최적화 여부 (기본값: False)

    Returns:
        최적화 결과 및 통계
    """
    try:
        return optimize_memory(aggressive=aggressive)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"메모리 최적화 실패: {str(e)}")


@router.get("/diagnostics", summary="메모리 진단 정보")
async def get_system_memory_diagnostics() -> Dict[str, Any]:
    """
    상세한 메모리 진단 정보를 조회합니다.

    Returns:
        종합 보고서, 최적화 기록, 성능 기록 등
    """
    try:
        return get_memory_diagnostics()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"메모리 진단 정보 조회 실패: {str(e)}"
        )


@router.get("/cache/stats", summary="캐시 통계 조회")
async def get_cache_statistics() -> Dict[str, Any]:
    """
    모든 캐시 인스턴스의 통계를 조회합니다.

    Returns:
        캐시별 히트율, 메모리 사용량, 항목 수 등
    """
    try:
        return cache_manager.get_all_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"캐시 통계 조회 실패: {str(e)}")


@router.post("/cache/cleanup", summary="캐시 정리")
async def cleanup_expired_cache() -> Dict[str, Any]:
    """
    만료된 캐시 항목들을 정리합니다.

    Returns:
        정리된 항목 수 및 캐시별 상세 정보
    """
    try:
        expired_items = cache_manager.cleanup_all_expired()
        total_expired = sum(expired_items.values())

        return {
            "timestamp": datetime.now().isoformat(),
            "total_expired_items": total_expired,
            "cache_details": expired_items,
            "success": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"캐시 정리 실패: {str(e)}")


@router.post("/cache/clear", summary="캐시 전체 삭제")
async def clear_all_cache(
    cache_name: Optional[str] = Query(
        None, description="특정 캐시만 삭제 (미지정시 전체)"
    )
) -> Dict[str, Any]:
    """
    캐시를 전체 또는 특정 캐시만 삭제합니다.

    Args:
        cache_name: 삭제할 캐시 이름 (미지정시 전체 삭제)

    Returns:
        삭제 결과
    """
    try:
        if cache_name:
            if cache_name in cache_manager.caches:
                cache_manager.caches[cache_name].clear()
                return {
                    "timestamp": datetime.now().isoformat(),
                    "cleared_cache": cache_name,
                    "success": True,
                }
            else:
                raise HTTPException(
                    status_code=404, detail=f"캐시 '{cache_name}'를 찾을 수 없습니다"
                )
        else:
            cache_manager.clear_all()
            return {
                "timestamp": datetime.now().isoformat(),
                "cleared_caches": "all",
                "cache_count": len(cache_manager.caches),
                "success": True,
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"캐시 삭제 실패: {str(e)}")


@router.get("/performance/history", summary="성능 기록 조회")
async def get_performance_history(
    hours: int = Query(24, description="조회할 시간 범위 (시간)", ge=1, le=168)
) -> Dict[str, Any]:
    """
    메모리 성능 기록을 조회합니다.

    Args:
        hours: 조회할 시간 범위 (1-168시간, 기본값: 24시간)

    Returns:
        시간별 메모리 사용량, 캐시 히트율 등 성능 데이터
    """
    try:
        history = integrated_memory_manager.get_performance_history(hours=hours)

        return {
            "timestamp": datetime.now().isoformat(),
            "period_hours": hours,
            "data_points": len(history),
            "performance_data": history,
            "summary": {
                "avg_memory_percent": (
                    sum(h["memory_percent"] for h in history) / len(history)
                    if history
                    else 0
                ),
                "avg_cache_hit_rate": (
                    sum(h["cache_hit_rate"] for h in history) / len(history)
                    if history
                    else 0
                ),
                "total_cached_items": (
                    history[-1]["total_cached_items"] if history else 0
                ),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"성능 기록 조회 실패: {str(e)}")


@router.get("/optimization/history", summary="최적화 기록 조회")
async def get_optimization_history(
    limit: int = Query(10, description="조회할 기록 수", ge=1, le=100)
) -> Dict[str, Any]:
    """
    메모리 최적화 실행 기록을 조회합니다.

    Args:
        limit: 조회할 기록 수 (1-100개, 기본값: 10개)

    Returns:
        최적화 실행 기록 및 효과
    """
    try:
        history = memory_manager.get_optimization_history(limit=limit)

        return {
            "timestamp": datetime.now().isoformat(),
            "record_count": len(history),
            "optimization_history": history,
            "summary": {
                "total_optimizations": len(history),
                "total_memory_freed_mb": sum(
                    h.get("memory_freed_mb", 0) for h in history
                ),
                "avg_memory_freed_mb": (
                    sum(h.get("memory_freed_mb", 0) for h in history) / len(history)
                    if history
                    else 0
                ),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"최적화 기록 조회 실패: {str(e)}")


@router.get("/alerts", summary="메모리 알림 조회")
async def get_memory_alerts(
    limit: int = Query(20, description="조회할 알림 수", ge=1, le=100)
) -> Dict[str, Any]:
    """
    메모리 관련 알림을 조회합니다.

    Args:
        limit: 조회할 알림 수 (1-100개, 기본값: 20개)

    Returns:
        메모리 알림 목록
    """
    try:
        alerts = memory_manager.get_memory_alerts(limit=limit)

        return {
            "timestamp": datetime.now().isoformat(),
            "alert_count": len(alerts),
            "alerts": alerts,
            "summary": {
                "critical_alerts": len(
                    [a for a in alerts if a.get("level") == "critical"]
                ),
                "warning_alerts": len(
                    [a for a in alerts if a.get("level") == "warning"]
                ),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"메모리 알림 조회 실패: {str(e)}")


@router.get("/monitoring/status", summary="모니터링 상태 조회")
async def get_monitoring_status() -> Dict[str, Any]:
    """
    메모리 모니터링 시스템의 상태를 조회합니다.

    Returns:
        모니터링 활성화 상태, 설정 정보 등
    """
    try:
        return {
            "timestamp": datetime.now().isoformat(),
            "monitoring_active": integrated_memory_manager.monitoring_active,
            "performance_records": len(integrated_memory_manager.performance_history),
            "cache_instances": len(cache_manager.caches),
            "system_status": "healthy",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"모니터링 상태 조회 실패: {str(e)}"
        )
