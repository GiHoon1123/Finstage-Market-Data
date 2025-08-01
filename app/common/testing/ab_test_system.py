"""
A/B 테스트 시스템

일부 요청만 최적화 버전으로 처리하고 성능 비교 및 안정성 검증을 수행하는 시스템입니다.
"""

import hashlib
import json
import random
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time
import uuid

from app.common.utils.logging_config import get_logger
from app.common.utils.memory_optimizer import memory_monitor
from app.common.monitoring.performance_metrics_collector import get_metrics_collector

logger = get_logger(__name__)


class ABTestStatus(Enum):
    """A/B 테스트 상태"""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    STOPPED = "stopped"


class TrafficSplitMethod(Enum):
    """트래픽 분할 방법"""

    RANDOM = "random"
    USER_ID = "user_id"
    SESSION_ID = "session_id"
    IP_ADDRESS = "ip_address"
    CUSTOM_HASH = "custom_hash"


@dataclass
class ABTestVariant:
    """A/B 테스트 변형"""

    id: str
    name: str
    description: str
    traffic_percentage: float
    is_control: bool = False
    optimization_rules: List[str] = None  # 적용할 최적화 규칙 ID들
    custom_config: Dict[str, Any] = None


@dataclass
class ABTestConfig:
    """A/B 테스트 설정"""

    id: str
    name: str
    description: str
    variants: List[ABTestVariant]
    traffic_split_method: TrafficSplitMethod
    target_endpoints: List[str]  # 테스트 대상 API 엔드포인트들
    status: ABTestStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    min_sample_size: int = 1000
    confidence_level: float = 0.95
    success_metrics: List[str] = None  # 성공 지표들
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ABTestResult:
    """A/B 테스트 결과"""

    test_id: str
    variant_id: str
    timestamp: datetime
    endpoint: str
    user_identifier: str
    response_time_ms: float
    success: bool
    error_message: Optional[str] = None
    custom_metrics: Dict[str, float] = None


@dataclass
class ABTestStatistics:
    """A/B 테스트 통계"""

    variant_id: str
    sample_size: int
    success_rate: float
    avg_response_time: float
    median_response_time: float
    p95_response_time: float
    error_rate: float
    conversion_rate: Optional[float] = None
    custom_metrics: Dict[str, float] = None


class ABTestSystem:
    """A/B 테스트 시스템"""

    def __init__(self, config_file: str = "config/ab_test_config.json"):
        self.config_file = config_file
        self.metrics_collector = get_metrics_collector()

        # A/B 테스트 설정들
        self.ab_tests: Dict[str, ABTestConfig] = {}

        # 테스트 결과 저장소
        self.test_results: Dict[str, List[ABTestResult]] = {}

        # 사용자 할당 캐시 (사용자 -> 변형 매핑)
        self.user_assignments: Dict[str, Dict[str, str]] = {}

        # 통계 캐시
        self.statistics_cache: Dict[str, Dict[str, ABTestStatistics]] = {}
        self.cache_last_updated: Dict[str, datetime] = {}

        # 모니터링 상태
        self.is_monitoring = False
        self.monitoring_thread = None

        # 설정 로드
        self._load_configuration()

    def _load_configuration(self):
        """설정 파일 로드"""
        try:
            import os

            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)

                # A/B 테스트 설정 로드
                if "ab_tests" in config:
                    for test_data in config["ab_tests"]:
                        # 변형들 로드
                        variants = []
                        for variant_data in test_data["variants"]:
                            variant = ABTestVariant(
                                id=variant_data["id"],
                                name=variant_data["name"],
                                description=variant_data["description"],
                                traffic_percentage=variant_data["traffic_percentage"],
                                is_control=variant_data.get("is_control", False),
                                optimization_rules=variant_data.get(
                                    "optimization_rules", []
                                ),
                                custom_config=variant_data.get("custom_config", {}),
                            )
                            variants.append(variant)

                        # 테스트 설정 생성
                        test_config = ABTestConfig(
                            id=test_data["id"],
                            name=test_data["name"],
                            description=test_data["description"],
                            variants=variants,
                            traffic_split_method=TrafficSplitMethod(
                                test_data["traffic_split_method"]
                            ),
                            target_endpoints=test_data["target_endpoints"],
                            status=ABTestStatus(test_data["status"]),
                            start_time=(
                                datetime.fromisoformat(test_data["start_time"])
                                if test_data.get("start_time")
                                else None
                            ),
                            end_time=(
                                datetime.fromisoformat(test_data["end_time"])
                                if test_data.get("end_time")
                                else None
                            ),
                            min_sample_size=test_data.get("min_sample_size", 1000),
                            confidence_level=test_data.get("confidence_level", 0.95),
                            success_metrics=test_data.get("success_metrics", []),
                            created_at=(
                                datetime.fromisoformat(test_data["created_at"])
                                if test_data.get("created_at")
                                else None
                            ),
                            updated_at=(
                                datetime.fromisoformat(test_data["updated_at"])
                                if test_data.get("updated_at")
                                else None
                            ),
                        )

                        self.ab_tests[test_config.id] = test_config

                logger.info("ab_test_config_loaded", tests_count=len(self.ab_tests))
            else:
                logger.info("ab_test_config_not_found", creating_default=True)

        except Exception as e:
            logger.error("ab_test_config_load_failed", error=str(e))

    def _save_configuration(self):
        """설정 파일 저장"""
        try:
            import os

            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

            config = {"ab_tests": [], "last_updated": datetime.now().isoformat()}

            # A/B 테스트 설정 저장
            for test in self.ab_tests.values():
                variants_data = []
                for variant in test.variants:
                    variant_data = asdict(variant)
                    variants_data.append(variant_data)

                test_data = {
                    "id": test.id,
                    "name": test.name,
                    "description": test.description,
                    "variants": variants_data,
                    "traffic_split_method": test.traffic_split_method.value,
                    "target_endpoints": test.target_endpoints,
                    "status": test.status.value,
                    "start_time": (
                        test.start_time.isoformat() if test.start_time else None
                    ),
                    "end_time": test.end_time.isoformat() if test.end_time else None,
                    "min_sample_size": test.min_sample_size,
                    "confidence_level": test.confidence_level,
                    "success_metrics": test.success_metrics,
                    "created_at": (
                        test.created_at.isoformat() if test.created_at else None
                    ),
                    "updated_at": (
                        test.updated_at.isoformat() if test.updated_at else None
                    ),
                }

                config["ab_tests"].append(test_data)

            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            logger.info("ab_test_config_saved")

        except Exception as e:
            logger.error("ab_test_config_save_failed", error=str(e))

    @memory_monitor
    def create_ab_test(self, test_config: ABTestConfig) -> bool:
        """
        A/B 테스트 생성

        Args:
            test_config: 테스트 설정

        Returns:
            생성 성공 여부
        """
        try:
            # 트래픽 비율 검증
            total_percentage = sum(
                variant.traffic_percentage for variant in test_config.variants
            )
            if abs(total_percentage - 100.0) > 0.01:
                raise ValueError(
                    f"Total traffic percentage must be 100%, got {total_percentage}%"
                )

            # 컨트롤 그룹 검증
            control_variants = [v for v in test_config.variants if v.is_control]
            if len(control_variants) != 1:
                raise ValueError("Exactly one control variant is required")

            # 테스트 ID 중복 확인
            if test_config.id in self.ab_tests:
                raise ValueError(f"AB test already exists: {test_config.id}")

            # 생성 시간 설정
            test_config.created_at = datetime.now()
            test_config.updated_at = datetime.now()
            test_config.status = ABTestStatus.DRAFT

            # 테스트 저장
            self.ab_tests[test_config.id] = test_config
            self.test_results[test_config.id] = []

            # 설정 저장
            self._save_configuration()

            logger.info(
                "ab_test_created",
                test_id=test_config.id,
                test_name=test_config.name,
                variants_count=len(test_config.variants),
            )

            return True

        except Exception as e:
            logger.error(
                "ab_test_creation_failed", test_id=test_config.id, error=str(e)
            )
            return False

    @memory_monitor
    def start_ab_test(self, test_id: str) -> bool:
        """
        A/B 테스트 시작

        Args:
            test_id: 테스트 ID

        Returns:
            시작 성공 여부
        """
        try:
            if test_id not in self.ab_tests:
                raise ValueError(f"AB test not found: {test_id}")

            test = self.ab_tests[test_id]

            if test.status != ABTestStatus.DRAFT:
                raise ValueError(f"Cannot start test in {test.status.value} status")

            # 테스트 시작
            test.status = ABTestStatus.RUNNING
            test.start_time = datetime.now()
            test.updated_at = datetime.now()

            # 설정 저장
            self._save_configuration()

            logger.info("ab_test_started", test_id=test_id, test_name=test.name)

            return True

        except Exception as e:
            logger.error("ab_test_start_failed", test_id=test_id, error=str(e))
            return False

    @memory_monitor
    def stop_ab_test(self, test_id: str, reason: str = "") -> bool:
        """
        A/B 테스트 중지

        Args:
            test_id: 테스트 ID
            reason: 중지 이유

        Returns:
            중지 성공 여부
        """
        try:
            if test_id not in self.ab_tests:
                raise ValueError(f"AB test not found: {test_id}")

            test = self.ab_tests[test_id]

            if test.status not in [ABTestStatus.RUNNING, ABTestStatus.PAUSED]:
                raise ValueError(f"Cannot stop test in {test.status.value} status")

            # 테스트 중지
            test.status = ABTestStatus.STOPPED
            test.end_time = datetime.now()
            test.updated_at = datetime.now()

            # 설정 저장
            self._save_configuration()

            logger.info(
                "ab_test_stopped", test_id=test_id, test_name=test.name, reason=reason
            )

            return True

        except Exception as e:
            logger.error("ab_test_stop_failed", test_id=test_id, error=str(e))
            return False

    @memory_monitor
    def assign_variant(
        self, test_id: str, user_identifier: str, endpoint: str
    ) -> Optional[str]:
        """
        사용자에게 변형 할당

        Args:
            test_id: 테스트 ID
            user_identifier: 사용자 식별자
            endpoint: 요청 엔드포인트

        Returns:
            할당된 변형 ID (테스트 대상이 아니면 None)
        """
        try:
            if test_id not in self.ab_tests:
                return None

            test = self.ab_tests[test_id]

            # 테스트가 실행 중이 아니면 None 반환
            if test.status != ABTestStatus.RUNNING:
                return None

            # 대상 엔드포인트가 아니면 None 반환
            if endpoint not in test.target_endpoints:
                return None

            # 이미 할당된 변형이 있는지 확인
            if test_id in self.user_assignments.get(user_identifier, {}):
                return self.user_assignments[user_identifier][test_id]

            # 새로운 변형 할당
            variant_id = self._calculate_variant_assignment(test, user_identifier)

            # 할당 저장
            if user_identifier not in self.user_assignments:
                self.user_assignments[user_identifier] = {}
            self.user_assignments[user_identifier][test_id] = variant_id

            logger.debug(
                "variant_assigned",
                test_id=test_id,
                user_identifier=user_identifier,
                variant_id=variant_id,
            )

            return variant_id

        except Exception as e:
            logger.error(
                "variant_assignment_failed",
                test_id=test_id,
                user_identifier=user_identifier,
                error=str(e),
            )
            return None

    def _calculate_variant_assignment(
        self, test: ABTestConfig, user_identifier: str
    ) -> str:
        """변형 할당 계산"""
        try:
            # 해시 기반 할당
            if test.traffic_split_method in [
                TrafficSplitMethod.USER_ID,
                TrafficSplitMethod.SESSION_ID,
                TrafficSplitMethod.IP_ADDRESS,
                TrafficSplitMethod.CUSTOM_HASH,
            ]:
                # 일관된 해시 생성
                hash_input = f"{test.id}:{user_identifier}"
                hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
                percentage = (hash_value % 10000) / 100.0  # 0-99.99%
            else:
                # 랜덤 할당
                percentage = random.uniform(0, 100)

            # 누적 비율로 변형 선택
            cumulative_percentage = 0
            for variant in test.variants:
                cumulative_percentage += variant.traffic_percentage
                if percentage < cumulative_percentage:
                    return variant.id

            # 기본값으로 첫 번째 변형 반환
            return test.variants[0].id

        except Exception as e:
            logger.error("variant_calculation_failed", test_id=test.id, error=str(e))
            return test.variants[0].id

    @memory_monitor
    def record_test_result(
        self,
        test_id: str,
        variant_id: str,
        endpoint: str,
        user_identifier: str,
        response_time_ms: float,
        success: bool,
        error_message: Optional[str] = None,
        custom_metrics: Optional[Dict[str, float]] = None,
    ):
        """
        테스트 결과 기록

        Args:
            test_id: 테스트 ID
            variant_id: 변형 ID
            endpoint: 엔드포인트
            user_identifier: 사용자 식별자
            response_time_ms: 응답 시간 (밀리초)
            success: 성공 여부
            error_message: 에러 메시지
            custom_metrics: 커스텀 메트릭들
        """
        try:
            if test_id not in self.ab_tests:
                return

            result = ABTestResult(
                test_id=test_id,
                variant_id=variant_id,
                timestamp=datetime.now(),
                endpoint=endpoint,
                user_identifier=user_identifier,
                response_time_ms=response_time_ms,
                success=success,
                error_message=error_message,
                custom_metrics=custom_metrics or {},
            )

            # 결과 저장
            if test_id not in self.test_results:
                self.test_results[test_id] = []

            self.test_results[test_id].append(result)

            # 결과 개수 제한 (메모리 관리)
            if len(self.test_results[test_id]) > 100000:
                self.test_results[test_id] = self.test_results[test_id][-50000:]

            # 통계 캐시 무효화
            if test_id in self.statistics_cache:
                del self.statistics_cache[test_id]

            logger.debug(
                "test_result_recorded",
                test_id=test_id,
                variant_id=variant_id,
                success=success,
                response_time=response_time_ms,
            )

        except Exception as e:
            logger.error("test_result_recording_failed", test_id=test_id, error=str(e))

    @memory_monitor
    def get_test_statistics(
        self, test_id: str, force_refresh: bool = False
    ) -> Dict[str, ABTestStatistics]:
        """
        테스트 통계 조회

        Args:
            test_id: 테스트 ID
            force_refresh: 강제 새로고침 여부

        Returns:
            변형별 통계
        """
        try:
            if test_id not in self.ab_tests:
                return {}

            # 캐시 확인
            if not force_refresh and test_id in self.statistics_cache:
                cache_time = self.cache_last_updated.get(test_id)
                if cache_time and datetime.now() - cache_time < timedelta(minutes=5):
                    return self.statistics_cache[test_id]

            # 통계 계산
            test = self.ab_tests[test_id]
            results = self.test_results.get(test_id, [])

            statistics = {}

            for variant in test.variants:
                variant_results = [r for r in results if r.variant_id == variant.id]

                if not variant_results:
                    statistics[variant.id] = ABTestStatistics(
                        variant_id=variant.id,
                        sample_size=0,
                        success_rate=0.0,
                        avg_response_time=0.0,
                        median_response_time=0.0,
                        p95_response_time=0.0,
                        error_rate=0.0,
                    )
                    continue

                # 기본 통계 계산
                sample_size = len(variant_results)
                successful_results = [r for r in variant_results if r.success]
                success_rate = len(successful_results) / sample_size * 100
                error_rate = (sample_size - len(successful_results)) / sample_size * 100

                # 응답 시간 통계
                response_times = [r.response_time_ms for r in variant_results]
                response_times.sort()

                avg_response_time = sum(response_times) / len(response_times)
                median_response_time = response_times[len(response_times) // 2]
                p95_index = int(len(response_times) * 0.95)
                p95_response_time = (
                    response_times[p95_index]
                    if p95_index < len(response_times)
                    else response_times[-1]
                )

                # 커스텀 메트릭 통계
                custom_metrics = {}
                if variant_results and variant_results[0].custom_metrics:
                    for metric_name in variant_results[0].custom_metrics.keys():
                        metric_values = [
                            r.custom_metrics.get(metric_name, 0)
                            for r in variant_results
                            if r.custom_metrics
                        ]
                        if metric_values:
                            custom_metrics[f"avg_{metric_name}"] = sum(
                                metric_values
                            ) / len(metric_values)

                statistics[variant.id] = ABTestStatistics(
                    variant_id=variant.id,
                    sample_size=sample_size,
                    success_rate=success_rate,
                    avg_response_time=avg_response_time,
                    median_response_time=median_response_time,
                    p95_response_time=p95_response_time,
                    error_rate=error_rate,
                    custom_metrics=custom_metrics,
                )

            # 캐시 저장
            self.statistics_cache[test_id] = statistics
            self.cache_last_updated[test_id] = datetime.now()

            return statistics

        except Exception as e:
            logger.error(
                "test_statistics_calculation_failed", test_id=test_id, error=str(e)
            )
            return {}

    @memory_monitor
    def analyze_test_significance(self, test_id: str) -> Dict[str, Any]:
        """
        테스트 통계적 유의성 분석

        Args:
            test_id: 테스트 ID

        Returns:
            유의성 분석 결과
        """
        try:
            if test_id not in self.ab_tests:
                return {"error": "Test not found"}

            test = self.ab_tests[test_id]
            statistics = self.get_test_statistics(test_id)

            if len(statistics) < 2:
                return {"error": "Insufficient variants for comparison"}

            # 컨트롤 그룹 찾기
            control_variant = None
            for variant in test.variants:
                if variant.is_control:
                    control_variant = variant
                    break

            if not control_variant or control_variant.id not in statistics:
                return {"error": "Control variant not found"}

            control_stats = statistics[control_variant.id]

            # 최소 샘플 크기 확인
            if control_stats.sample_size < test.min_sample_size:
                return {
                    "status": "insufficient_data",
                    "message": f"Control group has {control_stats.sample_size} samples, minimum required: {test.min_sample_size}",
                }

            # 각 변형과 컨트롤 비교
            comparisons = []

            for variant in test.variants:
                if variant.is_control or variant.id not in statistics:
                    continue

                variant_stats = statistics[variant.id]

                if variant_stats.sample_size < test.min_sample_size:
                    comparisons.append(
                        {
                            "variant_id": variant.id,
                            "variant_name": variant.name,
                            "status": "insufficient_data",
                            "sample_size": variant_stats.sample_size,
                            "required_size": test.min_sample_size,
                        }
                    )
                    continue

                # 간단한 t-test 근사 (실제로는 더 정교한 통계 테스트 필요)
                response_time_improvement = (
                    (control_stats.avg_response_time - variant_stats.avg_response_time)
                    / control_stats.avg_response_time
                ) * 100
                success_rate_improvement = (
                    variant_stats.success_rate - control_stats.success_rate
                )

                # 통계적 유의성 판단 (간소화된 버전)
                is_significant = (
                    abs(response_time_improvement) > 5.0  # 5% 이상 개선
                    and variant_stats.sample_size >= test.min_sample_size
                    and control_stats.sample_size >= test.min_sample_size
                )

                comparisons.append(
                    {
                        "variant_id": variant.id,
                        "variant_name": variant.name,
                        "status": (
                            "significant" if is_significant else "not_significant"
                        ),
                        "sample_size": variant_stats.sample_size,
                        "response_time_improvement_percent": response_time_improvement,
                        "success_rate_improvement": success_rate_improvement,
                        "avg_response_time": variant_stats.avg_response_time,
                        "control_avg_response_time": control_stats.avg_response_time,
                        "success_rate": variant_stats.success_rate,
                        "control_success_rate": control_stats.success_rate,
                    }
                )

            # 전체 결과 요약
            significant_improvements = [
                c
                for c in comparisons
                if c.get("status") == "significant"
                and c.get("response_time_improvement_percent", 0) > 0
            ]

            return {
                "test_id": test_id,
                "test_name": test.name,
                "analysis_time": datetime.now().isoformat(),
                "control_variant": {
                    "id": control_variant.id,
                    "name": control_variant.name,
                    "sample_size": control_stats.sample_size,
                    "avg_response_time": control_stats.avg_response_time,
                    "success_rate": control_stats.success_rate,
                },
                "comparisons": comparisons,
                "summary": {
                    "total_variants": len(comparisons),
                    "significant_improvements": len(significant_improvements),
                    "best_variant": (
                        max(
                            significant_improvements,
                            key=lambda x: x["response_time_improvement_percent"],
                        )
                        if significant_improvements
                        else None
                    ),
                    "recommendation": (
                        "Continue with best variant"
                        if significant_improvements
                        else "No significant improvement found"
                    ),
                },
            }

        except Exception as e:
            logger.error(
                "test_significance_analysis_failed", test_id=test_id, error=str(e)
            )
            return {"error": str(e)}

    def get_active_tests_for_endpoint(self, endpoint: str) -> List[str]:
        """특정 엔드포인트에 대한 활성 테스트 목록 조회"""
        active_tests = []

        for test_id, test in self.ab_tests.items():
            if (
                test.status == ABTestStatus.RUNNING
                and endpoint in test.target_endpoints
            ):
                active_tests.append(test_id)

        return active_tests

    def get_test_summary(self) -> Dict[str, Any]:
        """전체 테스트 요약 조회"""
        try:
            summary = {
                "total_tests": len(self.ab_tests),
                "running_tests": len(
                    [
                        t
                        for t in self.ab_tests.values()
                        if t.status == ABTestStatus.RUNNING
                    ]
                ),
                "completed_tests": len(
                    [
                        t
                        for t in self.ab_tests.values()
                        if t.status == ABTestStatus.COMPLETED
                    ]
                ),
                "draft_tests": len(
                    [
                        t
                        for t in self.ab_tests.values()
                        if t.status == ABTestStatus.DRAFT
                    ]
                ),
                "stopped_tests": len(
                    [
                        t
                        for t in self.ab_tests.values()
                        if t.status == ABTestStatus.STOPPED
                    ]
                ),
                "total_results": sum(
                    len(results) for results in self.test_results.values()
                ),
                "active_users": len(self.user_assignments),
                "tests": [],
            }

            for test in self.ab_tests.values():
                test_info = {
                    "id": test.id,
                    "name": test.name,
                    "status": test.status.value,
                    "variants_count": len(test.variants),
                    "target_endpoints": test.target_endpoints,
                    "start_time": (
                        test.start_time.isoformat() if test.start_time else None
                    ),
                    "end_time": test.end_time.isoformat() if test.end_time else None,
                    "results_count": len(self.test_results.get(test.id, [])),
                }
                summary["tests"].append(test_info)

            return summary

        except Exception as e:
            logger.error("test_summary_failed", error=str(e))
            return {"error": str(e)}


# 글로벌 A/B 테스트 시스템 인스턴스
_ab_test_system = None


def get_ab_test_system() -> ABTestSystem:
    """글로벌 A/B 테스트 시스템 인스턴스 조회"""
    global _ab_test_system
    if _ab_test_system is None:
        _ab_test_system = ABTestSystem()
    return _ab_test_system
