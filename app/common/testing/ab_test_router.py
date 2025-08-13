"""
A/B 테스트 시스템 API 라우터

A/B 테스트 생성, 관리, 결과 분석을 위한 REST API 엔드포인트를 제공합니다.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

from app.common.testing.ab_test_system import (
    get_ab_test_system,
    ABTestConfig,
    ABTestVariant,
    ABTestStatus,
    TrafficSplitMethod,
)
from app.common.utils.logging_config import get_logger
from app.common.utils.memory_optimizer import memory_monitor
from app.common.dto.api_response import ApiResponse
from app.common.utils.response_helper import (
    success_response,
    handle_service_error,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v2/ab-tests", tags=["A/B Testing"])


class ABTestVariantRequest(BaseModel):
    """A/B 테스트 변형 요청 모델"""

    id: str
    name: str
    description: str
    traffic_percentage: float
    is_control: bool = False
    optimization_rules: Optional[List[str]] = []
    custom_config: Optional[Dict[str, Any]] = {}


class ABTestConfigRequest(BaseModel):
    """A/B 테스트 설정 요청 모델"""

    id: str
    name: str
    description: str
    variants: List[ABTestVariantRequest]
    traffic_split_method: str
    target_endpoints: List[str]
    min_sample_size: int = 1000
    confidence_level: float = 0.95
    success_metrics: Optional[List[str]] = []


class TestResultRequest(BaseModel):
    """테스트 결과 요청 모델"""

    test_id: str
    variant_id: str
    endpoint: str
    user_identifier: str
    response_time_ms: float
    success: bool
    error_message: Optional[str] = None
    custom_metrics: Optional[Dict[str, float]] = {}


@router.get(
    "/", 
    summary="A/B 테스트 목록 조회",
    responses={
        200: {
            "description": "A/B 테스트 목록 조회 성공",
            "content": {
                "application/json": {
                    "example": {
                        "status": 200,
                        "message": "A/B 테스트 목록 조회 완료",
                        "data": {
                            "tests": [
                                {
                                    "id": "test_001",
                                    "name": "UI 개선 테스트",
                                    "status": "running",
                                    "variants": 2,
                                    "total_traffic": 1000,
                                    "start_date": "2025-08-10T00:00:00Z"
                                }
                            ],
                            "total_tests": 5,
                            "active_tests": 2,
                            "completed_tests": 3
                        }
                    }
                }
            },
        }
    },
)
@memory_monitor
async def get_ab_tests() -> ApiResponse:
    """
    등록된 A/B 테스트 목록을 조회합니다.

    Returns:
        A/B 테스트 목록
    """
    try:
        ab_test_system = get_ab_test_system()
        summary = ab_test_system.get_test_summary()

        if "error" in summary:
            handle_service_error(Exception(summary["error"]), "A/B 테스트 목록 조회 실패")

        return success_response(
            data=summary,
            message="A/B 테스트 목록 조회 완료"
        )

    except Exception as e:
        logger.error("ab_tests_list_api_failed", error=str(e))
        handle_service_error(e, "A/B 테스트 목록 조회 실패")


@router.get(
    "/{test_id}", 
    summary="특정 A/B 테스트 조회",
    responses={
        200: {
            "description": "특정 A/B 테스트 조회 성공",
            "content": {
                "application/json": {
                    "example": {
                        "status": 200,
                        "message": "A/B 테스트 'UI 개선 테스트' 조회 완료",
                        "data": {
                            "id": "test_001",
                            "name": "UI 개선 테스트",
                            "description": "새로운 UI 디자인 테스트",
                            "variants": [
                                {
                                    "id": "variant_a",
                                    "name": "기존 UI",
                                    "traffic_percentage": 50.0,
                                    "is_control": True
                                },
                                {
                                    "id": "variant_b",
                                    "name": "새로운 UI",
                                    "traffic_percentage": 50.0,
                                    "is_control": False
                                }
                            ],
                            "status": "running",
                            "start_time": "2025-08-10T00:00:00Z",
                            "results_count": 1250
                        }
                    }
                }
            },
        }
    },
)
@memory_monitor
async def get_ab_test(test_id: str) -> ApiResponse:
    """
    특정 A/B 테스트의 상세 정보를 조회합니다.

    Args:
        test_id: 조회할 테스트 ID

    Returns:
        A/B 테스트 상세 정보
    """
    try:
        ab_test_system = get_ab_test_system()

        if test_id not in ab_test_system.ab_tests:
            handle_service_error(Exception(f"AB test not found: {test_id}"), "A/B 테스트를 찾을 수 없습니다")

        test = ab_test_system.ab_tests[test_id]

        # 변형 정보 구성
        variants_info = []
        for variant in test.variants:
            variants_info.append(
                {
                    "id": variant.id,
                    "name": variant.name,
                    "description": variant.description,
                    "traffic_percentage": variant.traffic_percentage,
                    "is_control": variant.is_control,
                    "optimization_rules": variant.optimization_rules or [],
                    "custom_config": variant.custom_config or {},
                }
            )

        test_data = {
            "id": test.id,
            "name": test.name,
            "description": test.description,
            "variants": variants_info,
            "traffic_split_method": test.traffic_split_method.value,
            "target_endpoints": test.target_endpoints,
            "status": test.status.value,
            "start_time": test.start_time.isoformat() if test.start_time else None,
            "end_time": test.end_time.isoformat() if test.end_time else None,
            "min_sample_size": test.min_sample_size,
            "confidence_level": test.confidence_level,
            "success_metrics": test.success_metrics or [],
            "created_at": test.created_at.isoformat() if test.created_at else None,
            "updated_at": test.updated_at.isoformat() if test.updated_at else None,
            "results_count": len(ab_test_system.test_results.get(test_id, [])),
        }

        return success_response(
            data=test_data,
            message=f"A/B 테스트 '{test.name}' 조회 완료"
        )

    except Exception as e:
        logger.error("ab_test_detail_api_failed", test_id=test_id, error=str(e))
        handle_service_error(e, f"A/B 테스트 '{test_id}' 조회 실패")


@router.post(
    "/", 
    summary="A/B 테스트 생성",
    responses={
        200: {
            "description": "A/B 테스트 생성 성공",
            "content": {
                "application/json": {
                    "example": {
                        "status": 200,
                        "message": "A/B 테스트 'UI 개선 테스트'이 성공적으로 생성되었습니다",
                        "data": {
                            "test_id": "test_001",
                            "created_at": "2025-08-13T13:30:00Z"
                        }
                    }
                }
            },
        }
    },
)
@memory_monitor
async def create_ab_test(test_request: ABTestConfigRequest) -> ApiResponse:
    """
    새로운 A/B 테스트를 생성합니다.

    Args:
        test_request: A/B 테스트 설정

    Returns:
        생성 결과
    """
    try:
        ab_test_system = get_ab_test_system()

        # 트래픽 분할 방법 검증
        try:
            traffic_split_method = TrafficSplitMethod(test_request.traffic_split_method)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid traffic split method: {test_request.traffic_split_method}",
            )

        # 변형들 생성
        variants = []
        for variant_req in test_request.variants:
            variant = ABTestVariant(
                id=variant_req.id,
                name=variant_req.name,
                description=variant_req.description,
                traffic_percentage=variant_req.traffic_percentage,
                is_control=variant_req.is_control,
                optimization_rules=variant_req.optimization_rules,
                custom_config=variant_req.custom_config,
            )
            variants.append(variant)

        # 테스트 설정 생성
        test_config = ABTestConfig(
            id=test_request.id,
            name=test_request.name,
            description=test_request.description,
            variants=variants,
            traffic_split_method=traffic_split_method,
            target_endpoints=test_request.target_endpoints,
            status=ABTestStatus.DRAFT,
            min_sample_size=test_request.min_sample_size,
            confidence_level=test_request.confidence_level,
            success_metrics=test_request.success_metrics,
        )

        # 테스트 생성
        success = ab_test_system.create_ab_test(test_config)

        if success:
            response_data = {
                "test_id": test_request.id,
                "created_at": datetime.now().isoformat(),
            }
            
            return success_response(
                data=response_data,
                message=f"A/B 테스트 '{test_request.name}'이 성공적으로 생성되었습니다"
            )
        else:
            handle_service_error(Exception("Failed to create AB test"), "A/B 테스트 생성 실패")

    except Exception as e:
        logger.error(
            "ab_test_creation_api_failed", test_id=test_request.id, error=str(e)
        )
        handle_service_error(e, f"A/B 테스트 '{test_request.name}' 생성 실패")


@router.post("/{test_id}/start", summary="A/B 테스트 시작")
@memory_monitor
async def start_ab_test(test_id: str) -> ApiResponse:
    """
    A/B 테스트를 시작합니다.

    Args:
        test_id: 시작할 테스트 ID

    Returns:
        시작 결과
    """
    try:
        ab_test_system = get_ab_test_system()
        success = ab_test_system.start_ab_test(test_id)

        if success:
            response_data = {
                "test_id": test_id,
                "started_at": datetime.now().isoformat(),
            }
            
            return success_response(
                data=response_data,
                message=f"A/B 테스트 '{test_id}'이 성공적으로 시작되었습니다"
            )
        else:
            handle_service_error(Exception("Failed to start AB test"), "A/B 테스트 시작 실패")

    except Exception as e:
        logger.error("ab_test_start_api_failed", test_id=test_id, error=str(e))
        handle_service_error(e, f"A/B 테스트 '{test_id}' 시작 실패")


@router.post("/{test_id}/stop", summary="A/B 테스트 중지")
@memory_monitor
async def stop_ab_test(
    test_id: str, reason: str = Body("", description="중지 이유")
) -> ApiResponse:
    """
    A/B 테스트를 중지합니다.

    Args:
        test_id: 중지할 테스트 ID
        reason: 중지 이유

    Returns:
        중지 결과
    """
    try:
        ab_test_system = get_ab_test_system()
        success = ab_test_system.stop_ab_test(test_id, reason)

        if success:
            response_data = {
                "test_id": test_id,
                "reason": reason,
                "stopped_at": datetime.now().isoformat(),
            }
            
            return success_response(
                data=response_data,
                message=f"A/B 테스트 '{test_id}'이 성공적으로 중지되었습니다"
            )
        else:
            handle_service_error(Exception("Failed to stop AB test"), "A/B 테스트 중지 실패")

    except Exception as e:
        logger.error("ab_test_stop_api_failed", test_id=test_id, error=str(e))
        handle_service_error(e, f"A/B 테스트 '{test_id}' 중지 실패")


@router.get("/{test_id}/assign/{user_identifier}", summary="변형 할당 조회")
@memory_monitor
async def get_variant_assignment(
    test_id: str,
    user_identifier: str,
    endpoint: str = Query(..., description="요청 엔드포인트"),
) -> Dict[str, Any]:
    """
    사용자에게 할당된 변형을 조회합니다.

    Args:
        test_id: 테스트 ID
        user_identifier: 사용자 식별자
        endpoint: 요청 엔드포인트

    Returns:
        할당된 변형 정보
    """
    try:
        ab_test_system = get_ab_test_system()
        variant_id = ab_test_system.assign_variant(test_id, user_identifier, endpoint)

        if variant_id:
            # 변형 정보 조회
            test = ab_test_system.ab_tests[test_id]
            variant = next((v for v in test.variants if v.id == variant_id), None)

            return {
                "test_id": test_id,
                "user_identifier": user_identifier,
                "endpoint": endpoint,
                "assigned_variant": {
                    "id": variant_id,
                    "name": variant.name if variant else "Unknown",
                    "is_control": variant.is_control if variant else False,
                    "optimization_rules": variant.optimization_rules if variant else [],
                },
                "assigned_at": datetime.now().isoformat(),
            }
        else:
            return {
                "test_id": test_id,
                "user_identifier": user_identifier,
                "endpoint": endpoint,
                "assigned_variant": None,
                "message": "Not eligible for this test",
            }

    except Exception as e:
        logger.error(
            "variant_assignment_api_failed",
            test_id=test_id,
            user_identifier=user_identifier,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/results", summary="테스트 결과 기록")
@memory_monitor
async def record_test_result(result: TestResultRequest) -> Dict[str, Any]:
    """
    테스트 결과를 기록합니다.

    Args:
        result: 테스트 결과 정보

    Returns:
        기록 결과
    """
    try:
        ab_test_system = get_ab_test_system()

        ab_test_system.record_test_result(
            test_id=result.test_id,
            variant_id=result.variant_id,
            endpoint=result.endpoint,
            user_identifier=result.user_identifier,
            response_time_ms=result.response_time_ms,
            success=result.success,
            error_message=result.error_message,
            custom_metrics=result.custom_metrics,
        )

        return {
            "status": "success",
            "message": "Test result recorded successfully",
            "test_id": result.test_id,
            "variant_id": result.variant_id,
            "recorded_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(
            "test_result_recording_api_failed", test_id=result.test_id, error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{test_id}/statistics", summary="테스트 통계 조회")
@memory_monitor
async def get_test_statistics(
    test_id: str, force_refresh: bool = Query(False, description="강제 새로고침 여부")
) -> Dict[str, Any]:
    """
    테스트 통계를 조회합니다.

    Args:
        test_id: 테스트 ID
        force_refresh: 강제 새로고침 여부

    Returns:
        테스트 통계
    """
    try:
        ab_test_system = get_ab_test_system()
        statistics = ab_test_system.get_test_statistics(test_id, force_refresh)

        if not statistics:
            raise HTTPException(
                status_code=404, detail=f"No statistics found for test: {test_id}"
            )

        # 통계를 딕셔너리 형태로 변환
        stats_dict = {}
        for variant_id, stats in statistics.items():
            stats_dict[variant_id] = {
                "variant_id": stats.variant_id,
                "sample_size": stats.sample_size,
                "success_rate": stats.success_rate,
                "avg_response_time": stats.avg_response_time,
                "median_response_time": stats.median_response_time,
                "p95_response_time": stats.p95_response_time,
                "error_rate": stats.error_rate,
                "conversion_rate": stats.conversion_rate,
                "custom_metrics": stats.custom_metrics or {},
            }

        return {
            "test_id": test_id,
            "statistics": stats_dict,
            "generated_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("test_statistics_api_failed", test_id=test_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{test_id}/analysis", summary="테스트 유의성 분석")
@memory_monitor
async def analyze_test_significance(test_id: str) -> Dict[str, Any]:
    """
    테스트의 통계적 유의성을 분석합니다.

    Args:
        test_id: 테스트 ID

    Returns:
        유의성 분석 결과
    """
    try:
        ab_test_system = get_ab_test_system()
        analysis = ab_test_system.analyze_test_significance(test_id)

        if "error" in analysis:
            raise HTTPException(status_code=400, detail=analysis["error"])

        return analysis

    except HTTPException:
        raise
    except Exception as e:
        logger.error("test_analysis_api_failed", test_id=test_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{test_id}", summary="A/B 테스트 삭제")
@memory_monitor
async def delete_ab_test(test_id: str) -> Dict[str, Any]:
    """
    A/B 테스트를 삭제합니다.

    Args:
        test_id: 삭제할 테스트 ID

    Returns:
        삭제 결과
    """
    try:
        ab_test_system = get_ab_test_system()

        if test_id not in ab_test_system.ab_tests:
            raise HTTPException(status_code=404, detail=f"AB test not found: {test_id}")

        test = ab_test_system.ab_tests[test_id]

        # 실행 중인 테스트는 삭제 불가
        if test.status == ABTestStatus.RUNNING:
            raise HTTPException(
                status_code=400, detail="Cannot delete running test. Stop it first."
            )

        # 테스트 삭제
        del ab_test_system.ab_tests[test_id]
        if test_id in ab_test_system.test_results:
            del ab_test_system.test_results[test_id]
        if test_id in ab_test_system.statistics_cache:
            del ab_test_system.statistics_cache[test_id]

        # 설정 저장
        ab_test_system._save_configuration()

        return {
            "status": "success",
            "message": "AB test deleted successfully",
            "test_id": test_id,
            "deleted_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("ab_test_deletion_api_failed", test_id=test_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/endpoint/{endpoint_path:path}/active", summary="엔드포인트별 활성 테스트 조회"
)
@memory_monitor
async def get_active_tests_for_endpoint(endpoint_path: str) -> Dict[str, Any]:
    """
    특정 엔드포인트에 대한 활성 테스트 목록을 조회합니다.

    Args:
        endpoint_path: 엔드포인트 경로

    Returns:
        활성 테스트 목록
    """
    try:
        ab_test_system = get_ab_test_system()
        active_tests = ab_test_system.get_active_tests_for_endpoint(endpoint_path)

        test_details = []
        for test_id in active_tests:
            test = ab_test_system.ab_tests[test_id]
            test_details.append(
                {
                    "id": test.id,
                    "name": test.name,
                    "variants_count": len(test.variants),
                    "traffic_split_method": test.traffic_split_method.value,
                    "start_time": (
                        test.start_time.isoformat() if test.start_time else None
                    ),
                }
            )

        return {
            "endpoint": endpoint_path,
            "active_tests_count": len(active_tests),
            "active_tests": test_details,
            "retrieved_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(
            "active_tests_endpoint_api_failed", endpoint=endpoint_path, error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))
