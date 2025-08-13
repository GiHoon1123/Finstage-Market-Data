"""
점진적 최적화 적용 매니저 API 라우터

최적화 규칙 관리, 활성화/비활성화, 모니터링 등을 위한 REST API 엔드포인트를 제공합니다.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

from app.common.optimization.optimization_manager import (
    get_optimization_manager,
    OptimizationRule,
    OptimizationType,
    OptimizationStatus,
)
from app.common.utils.logging_config import get_logger
from app.common.utils.memory_optimizer import memory_monitor
from app.common.dto.api_response import ApiResponse
from app.common.utils.response_helper import (
    success_response,
    handle_service_error,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v2/optimization", tags=["Optimization Manager"])


class OptimizationRuleRequest(BaseModel):
    """최적화 규칙 요청 모델"""

    id: str
    name: str
    description: str
    optimization_type: str
    target_services: List[str]
    dependencies: Optional[List[str]] = []
    performance_threshold: Optional[Dict[str, float]] = None


class OptimizationActionRequest(BaseModel):
    """최적화 액션 요청 모델"""

    rule_id: str
    force: Optional[bool] = False
    reason: Optional[str] = ""


@router.get("/status", summary="최적화 상태 조회")
@memory_monitor
async def get_optimization_status() -> ApiResponse:
    """
    현재 최적화 시스템의 전체 상태를 조회합니다.

    Returns:
        최적화 상태 정보
    """
    try:
        manager = get_optimization_manager()
        status = manager.get_optimization_status()

        if "error" in status:
            handle_service_error(Exception(status["error"]), "최적화 상태 조회 실패")

        return success_response(
            data=status,
            message="최적화 상태 조회 완료"
        )

    except Exception as e:
        logger.error("optimization_status_api_failed", error=str(e))
        handle_service_error(e, "최적화 상태 조회 실패")


@router.get("/rules", summary="최적화 규칙 목록 조회")
@memory_monitor
async def get_optimization_rules() -> ApiResponse:
    """
    등록된 최적화 규칙들을 조회합니다.

    Returns:
        최적화 규칙 목록
    """
    try:
        manager = get_optimization_manager()
        status = manager.get_optimization_status()

        response_data = {
            "rules": status.get("rules", []),
            "total_count": status.get("total_rules", 0),
            "retrieved_at": datetime.now().isoformat(),
        }

        return success_response(
            data=response_data,
            message=f"최적화 규칙 목록 조회 완료 ({status.get('total_rules', 0)}개 규칙)"
        )

    except Exception as e:
        logger.error("optimization_rules_api_failed", error=str(e))
        handle_service_error(e, "최적화 규칙 목록 조회 실패")


@router.get("/rules/{rule_id}", summary="특정 최적화 규칙 조회")
@memory_monitor
async def get_optimization_rule(rule_id: str) -> ApiResponse:
    """
    특정 최적화 규칙의 상세 정보를 조회합니다.

    Args:
        rule_id: 조회할 규칙 ID

    Returns:
        최적화 규칙 상세 정보
    """
    try:
        manager = get_optimization_manager()

        if rule_id not in manager.optimization_rules:
            handle_service_error(Exception(f"Optimization rule not found: {rule_id}"), "최적화 규칙을 찾을 수 없습니다")

        rule = manager.optimization_rules[rule_id]

        rule_data = {
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "optimization_type": rule.optimization_type.value,
            "target_services": rule.target_services,
            "status": rule.status.value,
            "enabled_at": rule.enabled_at.isoformat() if rule.enabled_at else None,
            "disabled_at": rule.disabled_at.isoformat() if rule.disabled_at else None,
            "dependencies": rule.dependencies or [],
            "performance_threshold": rule.performance_threshold,
            "rollback_condition": rule.rollback_condition,
        }

        return success_response(
            data=rule_data,
            message=f"최적화 규칙 '{rule.name}' 조회 완료"
        )

    except Exception as e:
        logger.error(
            "optimization_rule_detail_api_failed", rule_id=rule_id, error=str(e)
        )
        handle_service_error(e, f"최적화 규칙 '{rule_id}' 조회 실패")


@router.post("/rules", summary="최적화 규칙 추가")
@memory_monitor
async def add_optimization_rule(
    rule_request: OptimizationRuleRequest,
) -> ApiResponse:
    """
    새로운 최적화 규칙을 추가합니다.

    Args:
        rule_request: 최적화 규칙 정보

    Returns:
        추가 결과
    """
    try:
        manager = get_optimization_manager()

        # 이미 존재하는 규칙인지 확인
        if rule_request.id in manager.optimization_rules:
            raise HTTPException(
                status_code=400,
                detail=f"Optimization rule already exists: {rule_request.id}",
            )

        # 최적화 유형 검증
        try:
            optimization_type = OptimizationType(rule_request.optimization_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid optimization type: {rule_request.optimization_type}",
            )

        # 의존성 검증
        if rule_request.dependencies:
            for dep_id in rule_request.dependencies:
                if dep_id not in manager.optimization_rules:
                    raise HTTPException(
                        status_code=400, detail=f"Dependency not found: {dep_id}"
                    )

        # 최적화 규칙 생성
        rule = OptimizationRule(
            id=rule_request.id,
            name=rule_request.name,
            description=rule_request.description,
            optimization_type=optimization_type,
            target_services=rule_request.target_services,
            status=OptimizationStatus.DISABLED,
            dependencies=rule_request.dependencies,
            performance_threshold=rule_request.performance_threshold,
        )

        # 규칙 추가
        manager.optimization_rules[rule.id] = rule
        manager._save_configuration()

        response_data = {
            "rule_id": rule_request.id,
            "added_at": datetime.now().isoformat(),
        }

        return success_response(
            data=response_data,
            message=f"최적화 규칙 '{rule_request.name}'이 성공적으로 추가되었습니다"
        )

    except Exception as e:
        logger.error(
            "optimization_rule_add_failed", rule_id=rule_request.id, error=str(e)
        )
        handle_service_error(e, f"최적화 규칙 '{rule_request.name}' 추가 실패")


@router.delete("/rules/{rule_id}", summary="최적화 규칙 삭제")
@memory_monitor
async def remove_optimization_rule(rule_id: str) -> ApiResponse:
    """
    최적화 규칙을 삭제합니다.

    Args:
        rule_id: 삭제할 규칙 ID

    Returns:
        삭제 결과
    """
    try:
        manager = get_optimization_manager()

        if rule_id not in manager.optimization_rules:
            raise HTTPException(
                status_code=404, detail=f"Optimization rule not found: {rule_id}"
            )

        rule = manager.optimization_rules[rule_id]

        # 활성화된 규칙은 먼저 비활성화 필요
        if rule.status == OptimizationStatus.ENABLED:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete enabled optimization rule. Disable it first.",
            )

        # 의존하는 다른 규칙들 확인
        dependent_rules = [
            r
            for r in manager.optimization_rules.values()
            if r.dependencies and rule_id in r.dependencies
        ]

        if dependent_rules:
            dependent_names = [r.name for r in dependent_rules]
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete rule with dependencies: {dependent_names}",
            )

        # 규칙 삭제
        del manager.optimization_rules[rule_id]
        manager._save_configuration()

        response_data = {
            "rule_id": rule_id,
            "removed_at": datetime.now().isoformat(),
        }

        return success_response(
            data=response_data,
            message=f"최적화 규칙 '{rule_id}'이 성공적으로 삭제되었습니다"
        )

    except Exception as e:
        logger.error("optimization_rule_remove_failed", rule_id=rule_id, error=str(e))
        handle_service_error(e, f"최적화 규칙 '{rule_id}' 삭제 실패")


@router.post("/enable", summary="최적화 활성화")
@memory_monitor
async def enable_optimization(action: OptimizationActionRequest) -> ApiResponse:
    """
    최적화를 활성화합니다.

    Args:
        action: 최적화 액션 정보

    Returns:
        활성화 결과
    """
    try:
        manager = get_optimization_manager()
        result = manager.enable_optimization(action.rule_id, action.force)

        response_data = {
            "status": (
                "success" if result.status == OptimizationStatus.ENABLED else "failed"
            ),
            "rule_id": result.rule_id,
            "optimization_status": result.status.value,
            "applied_at": result.applied_at.isoformat(),
            "performance_before": result.performance_before,
            "performance_after": result.performance_after,
            "error_message": result.error_message,
        }

        return success_response(
            data=response_data,
            message=f"최적화 규칙 '{action.rule_id}' 활성화 완료"
        )

    except Exception as e:
        logger.error(
            "optimization_enable_api_failed", rule_id=action.rule_id, error=str(e)
        )
        handle_service_error(e, f"최적화 규칙 '{action.rule_id}' 활성화 실패")


@router.post("/disable", summary="최적화 비활성화")
@memory_monitor
async def disable_optimization(action: OptimizationActionRequest) -> ApiResponse:
    """
    최적화를 비활성화합니다.

    Args:
        action: 최적화 액션 정보

    Returns:
        비활성화 결과
    """
    try:
        manager = get_optimization_manager()
        result = manager.disable_optimization(action.rule_id, action.reason)

        response_data = {
            "status": (
                "success" if result.status == OptimizationStatus.DISABLED else "failed"
            ),
            "rule_id": result.rule_id,
            "optimization_status": result.status.value,
            "applied_at": result.applied_at.isoformat(),
            "performance_before": result.performance_before,
            "rollback_reason": result.rollback_reason,
            "error_message": result.error_message,
        }

        return success_response(
            data=response_data,
            message=f"최적화 규칙 '{action.rule_id}' 비활성화 완료"
        )

    except Exception as e:
        logger.error(
            "optimization_disable_api_failed", rule_id=action.rule_id, error=str(e)
        )
        handle_service_error(e, f"최적화 규칙 '{action.rule_id}' 비활성화 실패")


@router.post("/baseline", summary="성능 기준선 설정")
@memory_monitor
async def set_performance_baseline() -> ApiResponse:
    """
    현재 성능을 기준선으로 설정합니다.

    Returns:
        기준선 설정 결과
    """
    try:
        manager = get_optimization_manager()
        success = manager.set_performance_baseline()

        if success:
            response_data = {
                "baseline": manager.performance_baseline,
                "set_at": datetime.now().isoformat(),
            }
            
            return success_response(
                data=response_data,
                message="성능 기준선이 성공적으로 설정되었습니다"
            )
        else:
            handle_service_error(Exception("Failed to set performance baseline"), "성능 기준선 설정 실패")

    except Exception as e:
        logger.error("performance_baseline_api_failed", error=str(e))
        handle_service_error(e, "성능 기준선 설정 실패")


@router.get("/baseline", summary="성능 기준선 조회")
@memory_monitor
async def get_performance_baseline() -> ApiResponse:
    """
    현재 설정된 성능 기준선을 조회합니다.

    Returns:
        성능 기준선 정보
    """
    try:
        manager = get_optimization_manager()

        if not manager.performance_baseline:
            handle_service_error(Exception("Performance baseline not set"), "성능 기준선이 설정되지 않았습니다")

        response_data = {
            "baseline": manager.performance_baseline,
            "is_set": True,
            "retrieved_at": datetime.now().isoformat(),
        }

        return success_response(
            data=response_data,
            message="성능 기준선 조회 완료"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("performance_baseline_get_api_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/start", summary="자동 모니터링 시작")
@memory_monitor
async def start_monitoring(
    check_interval: int = Query(60, description="체크 간격 (초)")
) -> Dict[str, Any]:
    """
    최적화 자동 모니터링을 시작합니다.

    Args:
        check_interval: 체크 간격

    Returns:
        모니터링 시작 결과
    """
    try:
        manager = get_optimization_manager()
        manager.start_monitoring(check_interval)

        return {
            "status": "success",
            "message": "Optimization monitoring started successfully",
            "check_interval": check_interval,
            "started_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("optimization_monitoring_start_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/stop", summary="자동 모니터링 중지")
@memory_monitor
async def stop_monitoring() -> Dict[str, Any]:
    """
    최적화 자동 모니터링을 중지합니다.

    Returns:
        모니터링 중지 결과
    """
    try:
        manager = get_optimization_manager()
        manager.stop_monitoring()

        return {
            "status": "success",
            "message": "Optimization monitoring stopped successfully",
            "stopped_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("optimization_monitoring_stop_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", summary="최적화 히스토리 조회")
@memory_monitor
async def get_optimization_history(
    hours: int = Query(24, description="조회할 시간 범위 (시간)")
) -> Dict[str, Any]:
    """
    최적화 적용 히스토리를 조회합니다.

    Args:
        hours: 조회할 시간 범위

    Returns:
        최적화 히스토리
    """
    try:
        manager = get_optimization_manager()
        history = manager.get_optimization_history(hours)

        return {
            "history": history,
            "time_range_hours": hours,
            "total_count": len(history),
            "retrieved_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("optimization_history_api_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/enable", summary="배치 최적화 활성화")
@memory_monitor
async def batch_enable_optimizations(
    rule_ids: List[str] = Body(..., description="활성화할 규칙 ID 목록"),
    force: bool = Body(False, description="의존성 무시하고 강제 활성화"),
) -> Dict[str, Any]:
    """
    여러 최적화를 배치로 활성화합니다.

    Args:
        rule_ids: 활성화할 규칙 ID 목록
        force: 의존성 무시 여부

    Returns:
        배치 활성화 결과
    """
    try:
        manager = get_optimization_manager()
        results = []

        for rule_id in rule_ids:
            try:
                result = manager.enable_optimization(rule_id, force)
                results.append(
                    {
                        "rule_id": rule_id,
                        "status": result.status.value,
                        "success": result.status == OptimizationStatus.ENABLED,
                        "error_message": result.error_message,
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "rule_id": rule_id,
                        "status": "error",
                        "success": False,
                        "error_message": str(e),
                    }
                )

        successful_count = len([r for r in results if r["success"]])

        return {
            "status": "completed",
            "total_rules": len(rule_ids),
            "successful_count": successful_count,
            "failed_count": len(rule_ids) - successful_count,
            "results": results,
            "processed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("batch_enable_optimizations_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/disable", summary="배치 최적화 비활성화")
@memory_monitor
async def batch_disable_optimizations(
    rule_ids: List[str] = Body(..., description="비활성화할 규칙 ID 목록"),
    reason: str = Body("", description="비활성화 이유"),
) -> Dict[str, Any]:
    """
    여러 최적화를 배치로 비활성화합니다.

    Args:
        rule_ids: 비활성화할 규칙 ID 목록
        reason: 비활성화 이유

    Returns:
        배치 비활성화 결과
    """
    try:
        manager = get_optimization_manager()
        results = []

        for rule_id in rule_ids:
            try:
                result = manager.disable_optimization(rule_id, reason)
                results.append(
                    {
                        "rule_id": rule_id,
                        "status": result.status.value,
                        "success": result.status == OptimizationStatus.DISABLED,
                        "error_message": result.error_message,
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "rule_id": rule_id,
                        "status": "error",
                        "success": False,
                        "error_message": str(e),
                    }
                )

        successful_count = len([r for r in results if r["success"]])

        return {
            "status": "completed",
            "total_rules": len(rule_ids),
            "successful_count": successful_count,
            "failed_count": len(rule_ids) - successful_count,
            "results": results,
            "processed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("batch_disable_optimizations_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations", summary="최적화 권장사항 조회")
@memory_monitor
async def get_optimization_recommendations() -> Dict[str, Any]:
    """
    현재 시스템 상태를 기반으로 최적화 권장사항을 제공합니다.

    Returns:
        최적화 권장사항
    """
    try:
        manager = get_optimization_manager()

        # 현재 성능 측정
        current_performance = manager._measure_current_performance()

        recommendations = []

        # 비활성화된 최적화 중 활성화 권장
        for rule in manager.optimization_rules.values():
            if rule.status == OptimizationStatus.DISABLED:
                # 의존성 확인
                dependencies_met = True
                if rule.dependencies:
                    for dep_id in rule.dependencies:
                        if dep_id not in manager.optimization_rules:
                            dependencies_met = False
                            break
                        if (
                            manager.optimization_rules[dep_id].status
                            != OptimizationStatus.ENABLED
                        ):
                            dependencies_met = False
                            break

                if dependencies_met:
                    recommendations.append(
                        {
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "action": "enable",
                            "priority": "medium",
                            "reason": "Dependencies are met and optimization is available",
                            "expected_benefit": f"Improve {rule.optimization_type.value} for {', '.join(rule.target_services)}",
                        }
                    )

        # 성능 기반 권장사항
        if current_performance:
            cpu_percent = current_performance.get("cpu_percent", 0)
            memory_percent = current_performance.get("memory_percent", 0)
            response_time = current_performance.get("api_response_time_ms", 0)

            if cpu_percent > 70:
                recommendations.append(
                    {
                        "rule_id": "async_api_endpoints",
                        "rule_name": "비동기 API 엔드포인트",
                        "action": "enable",
                        "priority": "high",
                        "reason": f"High CPU usage detected: {cpu_percent:.1f}%",
                        "expected_benefit": "Reduce CPU usage through async processing",
                    }
                )

            if memory_percent > 80:
                recommendations.append(
                    {
                        "rule_id": "memory_optimization_basic",
                        "rule_name": "기본 메모리 최적화",
                        "action": "enable",
                        "priority": "high",
                        "reason": f"High memory usage detected: {memory_percent:.1f}%",
                        "expected_benefit": "Optimize memory usage and prevent memory leaks",
                    }
                )

            if response_time > 1000:
                recommendations.append(
                    {
                        "rule_id": "caching_technical_analysis",
                        "rule_name": "기술적 분석 캐싱",
                        "action": "enable",
                        "priority": "high",
                        "reason": f"Slow response time detected: {response_time:.0f}ms",
                        "expected_benefit": "Improve response time through caching",
                    }
                )

        return {
            "recommendations": recommendations,
            "total_count": len(recommendations),
            "current_performance": current_performance,
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("optimization_recommendations_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
