"""
A/B 테스트 미들웨어

HTTP 요청을 가로채서 A/B 테스트 변형을 할당하고 결과를 자동으로 기록하는 미들웨어입니다.
"""

import time
import uuid
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.common.testing.ab_test_system import get_ab_test_system
from app.common.utils.logging_config import get_logger
from app.common.utils.memory_optimizer import memory_monitor

logger = get_logger(__name__)


class ABTestMiddleware(BaseHTTPMiddleware):
    """A/B 테스트 미들웨어"""

    def __init__(self, app, excluded_paths: Optional[list] = None):
        super().__init__(app)
        self.ab_test_system = get_ab_test_system()

        # A/B 테스트에서 제외할 경로들
        self.excluded_paths = excluded_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/metrics",
            "/api/v2/ab-tests",
            "/api/v2/optimization",
            "/api/v2/performance",
            "/api/v2/alerts",
        ]

    @memory_monitor
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """요청 처리 및 A/B 테스트 적용"""

        # 제외 경로 확인
        if self._should_exclude_path(request.url.path):
            return await call_next(request)

        # 사용자 식별자 생성
        user_identifier = self._get_user_identifier(request)

        # 해당 엔드포인트의 활성 테스트 조회
        active_tests = self.ab_test_system.get_active_tests_for_endpoint(
            request.url.path
        )

        if not active_tests:
            # A/B 테스트가 없으면 일반 처리
            return await call_next(request)

        # 각 테스트에 대해 변형 할당
        test_assignments = {}
        for test_id in active_tests:
            variant_id = self.ab_test_system.assign_variant(
                test_id=test_id,
                user_identifier=user_identifier,
                endpoint=request.url.path,
            )
            if variant_id:
                test_assignments[test_id] = variant_id

        if not test_assignments:
            # 할당된 변형이 없으면 일반 처리
            return await call_next(request)

        # 요청에 A/B 테스트 정보 추가
        request.state.ab_test_assignments = test_assignments
        request.state.ab_test_user_identifier = user_identifier

        # 요청 시작 시간 기록
        start_time = time.time()

        try:
            # 최적화 적용 (변형에 따라)
            self._apply_optimizations(request, test_assignments)

            # 요청 처리
            response = await call_next(request)

            # 응답 시간 계산
            response_time_ms = (time.time() - start_time) * 1000

            # 성공 여부 판단
            success = 200 <= response.status_code < 400

            # 테스트 결과 기록
            await self._record_test_results(
                test_assignments=test_assignments,
                endpoint=request.url.path,
                user_identifier=user_identifier,
                response_time_ms=response_time_ms,
                success=success,
                status_code=response.status_code,
            )

            # 응답 헤더에 A/B 테스트 정보 추가 (디버깅용)
            if hasattr(request.state, "ab_test_assignments"):
                response.headers["X-AB-Test-Variants"] = ",".join(
                    [
                        f"{test_id}:{variant_id}"
                        for test_id, variant_id in test_assignments.items()
                    ]
                )

            return response

        except Exception as e:
            # 에러 발생 시에도 결과 기록
            response_time_ms = (time.time() - start_time) * 1000

            await self._record_test_results(
                test_assignments=test_assignments,
                endpoint=request.url.path,
                user_identifier=user_identifier,
                response_time_ms=response_time_ms,
                success=False,
                error_message=str(e),
            )

            # 에러 재발생
            raise e

    def _should_exclude_path(self, path: str) -> bool:
        """경로가 A/B 테스트에서 제외되어야 하는지 확인"""
        for excluded_path in self.excluded_paths:
            if path.startswith(excluded_path):
                return True
        return False

    def _get_user_identifier(self, request: Request) -> str:
        """사용자 식별자 생성"""
        # 1. 사용자 ID가 있으면 사용
        if hasattr(request.state, "user_id") and request.state.user_id:
            return f"user:{request.state.user_id}"

        # 2. 세션 ID가 있으면 사용
        session_id = request.cookies.get("session_id")
        if session_id:
            return f"session:{session_id}"

        # 3. IP 주소 사용
        client_ip = request.client.host if request.client else "unknown"

        # 4. User-Agent와 조합하여 더 안정적인 식별자 생성
        user_agent = request.headers.get("user-agent", "")

        # 간단한 해시 생성
        import hashlib

        identifier_string = f"{client_ip}:{user_agent}"
        hash_value = hashlib.md5(identifier_string.encode()).hexdigest()[:16]

        return f"anonymous:{hash_value}"

    def _apply_optimizations(self, request: Request, test_assignments: dict):
        """변형에 따른 최적화 적용"""
        try:
            # 각 테스트의 변형에 따라 최적화 규칙 적용
            applied_optimizations = set()

            for test_id, variant_id in test_assignments.items():
                test = self.ab_test_system.ab_tests.get(test_id)
                if not test:
                    continue

                # 해당 변형 찾기
                variant = next((v for v in test.variants if v.id == variant_id), None)
                if not variant or not variant.optimization_rules:
                    continue

                # 최적화 규칙 적용
                for rule_id in variant.optimization_rules:
                    if rule_id not in applied_optimizations:
                        self._apply_optimization_rule(request, rule_id)
                        applied_optimizations.add(rule_id)

            # 적용된 최적화 정보를 요청 상태에 저장
            request.state.applied_optimizations = list(applied_optimizations)

        except Exception as e:
            logger.error(
                "optimization_application_failed",
                test_assignments=test_assignments,
                error=str(e),
            )

    def _apply_optimization_rule(self, request: Request, rule_id: str):
        """특정 최적화 규칙 적용"""
        try:
            # 최적화 매니저에서 규칙 정보 조회
            from app.common.optimization.optimization_manager import (
                get_optimization_manager,
            )

            optimization_manager = get_optimization_manager()

            if rule_id not in optimization_manager.optimization_rules:
                logger.warning("optimization_rule_not_found", rule_id=rule_id)
                return

            rule = optimization_manager.optimization_rules[rule_id]

            # 요청 상태에 최적화 정보 추가
            if not hasattr(request.state, "optimization_flags"):
                request.state.optimization_flags = {}

            request.state.optimization_flags[rule_id] = {
                "enabled": True,
                "type": rule.optimization_type.value,
                "target_services": rule.target_services,
            }

            logger.debug(
                "optimization_rule_applied",
                rule_id=rule_id,
                type=rule.optimization_type.value,
            )

        except Exception as e:
            logger.error(
                "optimization_rule_application_failed", rule_id=rule_id, error=str(e)
            )

    async def _record_test_results(
        self,
        test_assignments: dict,
        endpoint: str,
        user_identifier: str,
        response_time_ms: float,
        success: bool,
        status_code: int = None,
        error_message: str = None,
    ):
        """테스트 결과 기록"""
        try:
            for test_id, variant_id in test_assignments.items():
                # 커스텀 메트릭 생성
                custom_metrics = {}
                if status_code:
                    custom_metrics["status_code"] = float(status_code)

                # 결과 기록
                self.ab_test_system.record_test_result(
                    test_id=test_id,
                    variant_id=variant_id,
                    endpoint=endpoint,
                    user_identifier=user_identifier,
                    response_time_ms=response_time_ms,
                    success=success,
                    error_message=error_message,
                    custom_metrics=custom_metrics,
                )

            logger.debug(
                "ab_test_results_recorded",
                test_count=len(test_assignments),
                endpoint=endpoint,
                response_time=response_time_ms,
                success=success,
            )

        except Exception as e:
            logger.error(
                "ab_test_result_recording_failed",
                test_assignments=test_assignments,
                error=str(e),
            )


def create_ab_test_middleware(
    excluded_paths: Optional[list] = None,
) -> ABTestMiddleware:
    """A/B 테스트 미들웨어 생성 함수"""

    def middleware_factory(app):
        return ABTestMiddleware(app, excluded_paths)

    return middleware_factory
