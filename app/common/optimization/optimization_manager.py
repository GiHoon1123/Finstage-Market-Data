"""
점진적 최적화 적용 매니저

최적화를 단계별로 활성화/비활성화하고 롤백 메커니즘을 제공하는 시스템입니다.
"""

import json
import os
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time

from app.common.utils.logging_config import get_logger
from app.common.utils.memory_optimizer import memory_monitor
from app.common.monitoring.performance_metrics_collector import get_metrics_collector

logger = get_logger(__name__)


class OptimizationStatus(Enum):
    """최적화 상태"""

    DISABLED = "disabled"
    ENABLED = "enabled"
    TESTING = "testing"
    ROLLBACK = "rollback"
    ERROR = "error"


class OptimizationType(Enum):
    """최적화 유형"""

    MEMORY_OPTIMIZATION = "memory_optimization"
    CACHING = "caching"
    ASYNC_PROCESSING = "async_processing"
    BACKGROUND_TASKS = "background_tasks"
    WEBSOCKET_STREAMING = "websocket_streaming"
    DATABASE_OPTIMIZATION = "database_optimization"


@dataclass
class OptimizationRule:
    """최적화 규칙"""

    id: str
    name: str
    description: str
    optimization_type: OptimizationType
    target_services: List[str]
    status: OptimizationStatus
    enabled_at: Optional[datetime] = None
    disabled_at: Optional[datetime] = None
    rollback_condition: Optional[Dict[str, Any]] = None
    performance_threshold: Optional[Dict[str, float]] = None
    dependencies: List[str] = None  # 의존성 있는 다른 최적화 ID들


@dataclass
class OptimizationResult:
    """최적화 적용 결과"""

    rule_id: str
    status: OptimizationStatus
    applied_at: datetime
    performance_before: Dict[str, float]
    performance_after: Optional[Dict[str, float]] = None
    error_message: Optional[str] = None
    rollback_reason: Optional[str] = None


class OptimizationManager:
    """점진적 최적화 적용 매니저"""

    def __init__(self, config_file: str = "config/optimization_config.json"):
        self.config_file = config_file
        self.metrics_collector = get_metrics_collector()

        # 최적화 규칙들
        self.optimization_rules: Dict[str, OptimizationRule] = {}

        # 적용 결과 히스토리
        self.optimization_history: List[OptimizationResult] = []

        # 성능 기준선
        self.performance_baseline: Dict[str, float] = {}

        # 모니터링 상태
        self.is_monitoring = False
        self.monitoring_thread = None

        # 롤백 조건 체크 함수들
        self.rollback_checkers: Dict[str, Callable] = {}

        # 설정 로드
        self._load_configuration()

        # 기본 최적화 규칙 설정
        self._setup_default_rules()

    def _load_configuration(self):
        """설정 파일 로드"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)

                # 최적화 규칙 로드
                if "optimization_rules" in config:
                    for rule_data in config["optimization_rules"]:
                        rule = OptimizationRule(
                            id=rule_data["id"],
                            name=rule_data["name"],
                            description=rule_data["description"],
                            optimization_type=OptimizationType(
                                rule_data["optimization_type"]
                            ),
                            target_services=rule_data["target_services"],
                            status=OptimizationStatus(rule_data["status"]),
                            enabled_at=(
                                datetime.fromisoformat(rule_data["enabled_at"])
                                if rule_data.get("enabled_at")
                                else None
                            ),
                            disabled_at=(
                                datetime.fromisoformat(rule_data["disabled_at"])
                                if rule_data.get("disabled_at")
                                else None
                            ),
                            rollback_condition=rule_data.get("rollback_condition"),
                            performance_threshold=rule_data.get(
                                "performance_threshold"
                            ),
                            dependencies=rule_data.get("dependencies", []),
                        )
                        self.optimization_rules[rule.id] = rule

                # 성능 기준선 로드
                if "performance_baseline" in config:
                    self.performance_baseline = config["performance_baseline"]

                logger.info(
                    "optimization_config_loaded",
                    rules_count=len(self.optimization_rules),
                    baseline_metrics=len(self.performance_baseline),
                )
            else:
                logger.info("optimization_config_not_found", creating_default=True)

        except Exception as e:
            logger.error("optimization_config_load_failed", error=str(e))

    def _save_configuration(self):
        """설정 파일 저장"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

            config = {
                "optimization_rules": [],
                "performance_baseline": self.performance_baseline,
                "last_updated": datetime.now().isoformat(),
            }

            # 최적화 규칙 저장
            for rule in self.optimization_rules.values():
                rule_data = asdict(rule)
                # datetime 객체를 문자열로 변환
                if rule_data["enabled_at"]:
                    rule_data["enabled_at"] = rule.enabled_at.isoformat()
                if rule_data["disabled_at"]:
                    rule_data["disabled_at"] = rule.disabled_at.isoformat()
                # Enum을 문자열로 변환
                rule_data["optimization_type"] = rule.optimization_type.value
                rule_data["status"] = rule.status.value

                config["optimization_rules"].append(rule_data)

            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            logger.info("optimization_config_saved")

        except Exception as e:
            logger.error("optimization_config_save_failed", error=str(e))

    def _setup_default_rules(self):
        """기본 최적화 규칙 설정"""
        if self.optimization_rules:
            return  # 이미 규칙이 있으면 스킵

        default_rules = [
            OptimizationRule(
                id="memory_optimization_basic",
                name="기본 메모리 최적화",
                description="메모리 모니터링 및 기본 최적화 데코레이터 적용",
                optimization_type=OptimizationType.MEMORY_OPTIMIZATION,
                target_services=["all"],
                status=OptimizationStatus.DISABLED,
                performance_threshold={
                    "memory_usage_increase_percent": 10.0,
                    "response_time_increase_percent": 15.0,
                },
            ),
            OptimizationRule(
                id="caching_technical_analysis",
                name="기술적 분석 캐싱",
                description="기술적 분석 결과 캐싱으로 성능 향상",
                optimization_type=OptimizationType.CACHING,
                target_services=[
                    "TechnicalIndicatorService",
                    "SignalGeneratorService",
                    "PatternAnalysisService",
                ],
                status=OptimizationStatus.DISABLED,
                dependencies=["memory_optimization_basic"],
                performance_threshold={
                    "cache_hit_rate_minimum": 70.0,
                    "response_time_improvement_minimum": 20.0,
                },
            ),
            OptimizationRule(
                id="caching_price_data",
                name="가격 데이터 캐싱",
                description="가격 데이터 조회 결과 캐싱",
                optimization_type=OptimizationType.CACHING,
                target_services=[
                    "PriceMonitorService",
                    "PriceSnapshotService",
                    "PriceHighRecordService",
                ],
                status=OptimizationStatus.DISABLED,
                dependencies=["memory_optimization_basic"],
                performance_threshold={
                    "cache_hit_rate_minimum": 80.0,
                    "response_time_improvement_minimum": 30.0,
                },
            ),
            OptimizationRule(
                id="async_api_endpoints",
                name="비동기 API 엔드포인트",
                description="API 엔드포인트의 비동기 처리 적용",
                optimization_type=OptimizationType.ASYNC_PROCESSING,
                target_services=["technical_analysis_api", "price_data_api"],
                status=OptimizationStatus.DISABLED,
                dependencies=["caching_technical_analysis", "caching_price_data"],
                performance_threshold={
                    "concurrent_request_improvement": 50.0,
                    "average_response_time_improvement": 25.0,
                },
            ),
            OptimizationRule(
                id="background_heavy_tasks",
                name="무거운 작업 백그라운드 처리",
                description="무거운 작업들을 백그라운드 작업 큐로 이전",
                optimization_type=OptimizationType.BACKGROUND_TASKS,
                target_services=[
                    "DailyComprehensiveReportService",
                    "HistoricalDataService",
                    "BatchAnalysisService",
                ],
                status=OptimizationStatus.DISABLED,
                dependencies=["async_api_endpoints"],
                performance_threshold={
                    "api_response_time_improvement": 40.0,
                    "system_load_reduction": 30.0,
                },
            ),
            OptimizationRule(
                id="websocket_streaming",
                name="실시간 데이터 스트리밍",
                description="WebSocket을 통한 실시간 데이터 스트리밍",
                optimization_type=OptimizationType.WEBSOCKET_STREAMING,
                target_services=["RealtimePriceStreamer", "WebSocketManager"],
                status=OptimizationStatus.DISABLED,
                dependencies=["background_heavy_tasks"],
                performance_threshold={
                    "streaming_latency_maximum": 100.0,
                    "connection_stability_minimum": 95.0,
                },
            ),
        ]

        for rule in default_rules:
            self.optimization_rules[rule.id] = rule

        # 설정 저장
        self._save_configuration()

        logger.info("default_optimization_rules_created", count=len(default_rules))

    @memory_monitor
    def set_performance_baseline(self):
        """성능 기준선 설정"""
        try:
            # 현재 성능 메트릭 수집
            current_metrics = self.metrics_collector._get_current_metrics_summary()

            if current_metrics:
                self.performance_baseline = current_metrics.copy()
                self.performance_baseline["timestamp"] = datetime.now().isoformat()

                # 설정 저장
                self._save_configuration()

                logger.info(
                    "performance_baseline_set", metrics_count=len(current_metrics)
                )
                return True
            else:
                logger.warning("no_metrics_available_for_baseline")
                return False

        except Exception as e:
            logger.error("performance_baseline_set_failed", error=str(e))
            return False

    @memory_monitor
    def enable_optimization(
        self, rule_id: str, force: bool = False
    ) -> OptimizationResult:
        """
        최적화 활성화

        Args:
            rule_id: 활성화할 최적화 규칙 ID
            force: 의존성 무시하고 강제 활성화

        Returns:
            최적화 적용 결과
        """
        try:
            if rule_id not in self.optimization_rules:
                raise ValueError(f"Optimization rule not found: {rule_id}")

            rule = self.optimization_rules[rule_id]

            # 이미 활성화된 경우
            if rule.status == OptimizationStatus.ENABLED:
                logger.warning("optimization_already_enabled", rule_id=rule_id)
                return OptimizationResult(
                    rule_id=rule_id,
                    status=OptimizationStatus.ENABLED,
                    applied_at=datetime.now(),
                    performance_before={},
                    error_message="Already enabled",
                )

            # 의존성 확인
            if not force and rule.dependencies:
                for dep_id in rule.dependencies:
                    if dep_id not in self.optimization_rules:
                        raise ValueError(f"Dependency not found: {dep_id}")

                    dep_rule = self.optimization_rules[dep_id]
                    if dep_rule.status != OptimizationStatus.ENABLED:
                        raise ValueError(f"Dependency not enabled: {dep_id}")

            # 현재 성능 측정
            performance_before = self._measure_current_performance()

            # 최적화 적용
            success = self._apply_optimization(rule)

            if success:
                # 상태 업데이트
                rule.status = OptimizationStatus.ENABLED
                rule.enabled_at = datetime.now()
                rule.disabled_at = None

                # 설정 저장
                self._save_configuration()

                # 결과 생성
                result = OptimizationResult(
                    rule_id=rule_id,
                    status=OptimizationStatus.ENABLED,
                    applied_at=datetime.now(),
                    performance_before=performance_before,
                )

                # 히스토리에 추가
                self.optimization_history.append(result)

                logger.info(
                    "optimization_enabled", rule_id=rule_id, rule_name=rule.name
                )

                return result
            else:
                # 실패 시 에러 상태로 설정
                rule.status = OptimizationStatus.ERROR

                result = OptimizationResult(
                    rule_id=rule_id,
                    status=OptimizationStatus.ERROR,
                    applied_at=datetime.now(),
                    performance_before=performance_before,
                    error_message="Failed to apply optimization",
                )

                self.optimization_history.append(result)

                logger.error("optimization_enable_failed", rule_id=rule_id)

                return result

        except Exception as e:
            logger.error("optimization_enable_error", rule_id=rule_id, error=str(e))

            return OptimizationResult(
                rule_id=rule_id,
                status=OptimizationStatus.ERROR,
                applied_at=datetime.now(),
                performance_before={},
                error_message=str(e),
            )

    @memory_monitor
    def disable_optimization(
        self, rule_id: str, reason: str = ""
    ) -> OptimizationResult:
        """
        최적화 비활성화

        Args:
            rule_id: 비활성화할 최적화 규칙 ID
            reason: 비활성화 이유

        Returns:
            최적화 비활성화 결과
        """
        try:
            if rule_id not in self.optimization_rules:
                raise ValueError(f"Optimization rule not found: {rule_id}")

            rule = self.optimization_rules[rule_id]

            # 이미 비활성화된 경우
            if rule.status == OptimizationStatus.DISABLED:
                logger.warning("optimization_already_disabled", rule_id=rule_id)
                return OptimizationResult(
                    rule_id=rule_id,
                    status=OptimizationStatus.DISABLED,
                    applied_at=datetime.now(),
                    performance_before={},
                    error_message="Already disabled",
                )

            # 의존하는 다른 최적화들 확인
            dependent_rules = [
                r
                for r in self.optimization_rules.values()
                if r.dependencies
                and rule_id in r.dependencies
                and r.status == OptimizationStatus.ENABLED
            ]

            if dependent_rules:
                dependent_names = [r.name for r in dependent_rules]
                logger.warning(
                    "optimization_has_dependencies",
                    rule_id=rule_id,
                    dependents=dependent_names,
                )
                # 의존하는 최적화들도 함께 비활성화할지 사용자에게 확인 필요
                # 여기서는 경고만 로그로 남김

            # 현재 성능 측정
            performance_before = self._measure_current_performance()

            # 최적화 비활성화
            success = self._remove_optimization(rule)

            if success:
                # 상태 업데이트
                rule.status = OptimizationStatus.DISABLED
                rule.disabled_at = datetime.now()

                # 설정 저장
                self._save_configuration()

                # 결과 생성
                result = OptimizationResult(
                    rule_id=rule_id,
                    status=OptimizationStatus.DISABLED,
                    applied_at=datetime.now(),
                    performance_before=performance_before,
                    rollback_reason=reason,
                )

                # 히스토리에 추가
                self.optimization_history.append(result)

                logger.info(
                    "optimization_disabled",
                    rule_id=rule_id,
                    rule_name=rule.name,
                    reason=reason,
                )

                return result
            else:
                # 실패 시 에러 상태로 설정
                rule.status = OptimizationStatus.ERROR

                result = OptimizationResult(
                    rule_id=rule_id,
                    status=OptimizationStatus.ERROR,
                    applied_at=datetime.now(),
                    performance_before=performance_before,
                    error_message="Failed to remove optimization",
                )

                self.optimization_history.append(result)

                logger.error("optimization_disable_failed", rule_id=rule_id)

                return result

        except Exception as e:
            logger.error("optimization_disable_error", rule_id=rule_id, error=str(e))

            return OptimizationResult(
                rule_id=rule_id,
                status=OptimizationStatus.ERROR,
                applied_at=datetime.now(),
                performance_before={},
                error_message=str(e),
            )

    def _apply_optimization(self, rule: OptimizationRule) -> bool:
        """최적화 적용 (실제 구현은 각 최적화 유형별로 다름)"""
        try:
            if rule.optimization_type == OptimizationType.MEMORY_OPTIMIZATION:
                return self._apply_memory_optimization(rule)
            elif rule.optimization_type == OptimizationType.CACHING:
                return self._apply_caching_optimization(rule)
            elif rule.optimization_type == OptimizationType.ASYNC_PROCESSING:
                return self._apply_async_optimization(rule)
            elif rule.optimization_type == OptimizationType.BACKGROUND_TASKS:
                return self._apply_background_tasks_optimization(rule)
            elif rule.optimization_type == OptimizationType.WEBSOCKET_STREAMING:
                return self._apply_websocket_optimization(rule)
            else:
                logger.warning(
                    "unknown_optimization_type",
                    rule_id=rule.id,
                    type=rule.optimization_type.value,
                )
                return False

        except Exception as e:
            logger.error("optimization_apply_failed", rule_id=rule.id, error=str(e))
            return False

    def _remove_optimization(self, rule: OptimizationRule) -> bool:
        """최적화 제거 (실제 구현은 각 최적화 유형별로 다름)"""
        try:
            if rule.optimization_type == OptimizationType.MEMORY_OPTIMIZATION:
                return self._remove_memory_optimization(rule)
            elif rule.optimization_type == OptimizationType.CACHING:
                return self._remove_caching_optimization(rule)
            elif rule.optimization_type == OptimizationType.ASYNC_PROCESSING:
                return self._remove_async_optimization(rule)
            elif rule.optimization_type == OptimizationType.BACKGROUND_TASKS:
                return self._remove_background_tasks_optimization(rule)
            elif rule.optimization_type == OptimizationType.WEBSOCKET_STREAMING:
                return self._remove_websocket_optimization(rule)
            else:
                logger.warning(
                    "unknown_optimization_type",
                    rule_id=rule.id,
                    type=rule.optimization_type.value,
                )
                return False

        except Exception as e:
            logger.error("optimization_remove_failed", rule_id=rule.id, error=str(e))
            return False

    def _apply_memory_optimization(self, rule: OptimizationRule) -> bool:
        """메모리 최적화 적용"""
        # 실제로는 각 서비스에 메모리 최적화 데코레이터를 동적으로 적용
        # 여기서는 시뮬레이션
        logger.info(
            "applying_memory_optimization",
            rule_id=rule.id,
            services=rule.target_services,
        )
        return True

    def _remove_memory_optimization(self, rule: OptimizationRule) -> bool:
        """메모리 최적화 제거"""
        logger.info(
            "removing_memory_optimization",
            rule_id=rule.id,
            services=rule.target_services,
        )
        return True

    def _apply_caching_optimization(self, rule: OptimizationRule) -> bool:
        """캐싱 최적화 적용"""
        logger.info(
            "applying_caching_optimization",
            rule_id=rule.id,
            services=rule.target_services,
        )
        return True

    def _remove_caching_optimization(self, rule: OptimizationRule) -> bool:
        """캐싱 최적화 제거"""
        logger.info(
            "removing_caching_optimization",
            rule_id=rule.id,
            services=rule.target_services,
        )
        return True

    def _apply_async_optimization(self, rule: OptimizationRule) -> bool:
        """비동기 처리 최적화 적용"""
        logger.info(
            "applying_async_optimization",
            rule_id=rule.id,
            services=rule.target_services,
        )
        return True

    def _remove_async_optimization(self, rule: OptimizationRule) -> bool:
        """비동기 처리 최적화 제거"""
        logger.info(
            "removing_async_optimization",
            rule_id=rule.id,
            services=rule.target_services,
        )
        return True

    def _apply_background_tasks_optimization(self, rule: OptimizationRule) -> bool:
        """백그라운드 작업 최적화 적용"""
        logger.info(
            "applying_background_tasks_optimization",
            rule_id=rule.id,
            services=rule.target_services,
        )
        return True

    def _remove_background_tasks_optimization(self, rule: OptimizationRule) -> bool:
        """백그라운드 작업 최적화 제거"""
        logger.info(
            "removing_background_tasks_optimization",
            rule_id=rule.id,
            services=rule.target_services,
        )
        return True

    def _apply_websocket_optimization(self, rule: OptimizationRule) -> bool:
        """WebSocket 최적화 적용"""
        logger.info(
            "applying_websocket_optimization",
            rule_id=rule.id,
            services=rule.target_services,
        )
        return True

    def _remove_websocket_optimization(self, rule: OptimizationRule) -> bool:
        """WebSocket 최적화 제거"""
        logger.info(
            "removing_websocket_optimization",
            rule_id=rule.id,
            services=rule.target_services,
        )
        return True

    def _measure_current_performance(self) -> Dict[str, float]:
        """현재 성능 측정"""
        try:
            return self.metrics_collector._get_current_metrics_summary()
        except Exception as e:
            logger.error("performance_measurement_failed", error=str(e))
            return {}

    @memory_monitor
    def start_monitoring(self, check_interval: int = 60):
        """자동 모니터링 시작 (롤백 조건 체크)"""
        if self.is_monitoring:
            logger.warning("optimization_monitoring_already_running")
            return

        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop, args=(check_interval,), daemon=True
        )
        self.monitoring_thread.start()

        logger.info("optimization_monitoring_started", interval=check_interval)

    def stop_monitoring(self):
        """자동 모니터링 중지"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)

        logger.info("optimization_monitoring_stopped")

    def _monitoring_loop(self, check_interval: int):
        """모니터링 루프"""
        while self.is_monitoring:
            try:
                self._check_rollback_conditions()
                time.sleep(check_interval)
            except Exception as e:
                logger.error("optimization_monitoring_error", error=str(e))
                time.sleep(check_interval)

    def _check_rollback_conditions(self):
        """롤백 조건 확인"""
        try:
            current_performance = self._measure_current_performance()

            for rule_id, rule in self.optimization_rules.items():
                if rule.status != OptimizationStatus.ENABLED:
                    continue

                if not rule.performance_threshold:
                    continue

                # 성능 임계값 확인
                should_rollback = self._should_rollback(rule, current_performance)

                if should_rollback:
                    logger.warning(
                        "rollback_condition_met", rule_id=rule_id, rule_name=rule.name
                    )

                    # 자동 롤백 수행
                    self.disable_optimization(rule_id, "Performance threshold exceeded")

        except Exception as e:
            logger.error("rollback_condition_check_failed", error=str(e))

    def _should_rollback(
        self, rule: OptimizationRule, current_performance: Dict[str, float]
    ) -> bool:
        """롤백 여부 판단"""
        try:
            if not self.performance_baseline or not rule.performance_threshold:
                return False

            for metric, threshold in rule.performance_threshold.items():
                baseline_value = self.performance_baseline.get(
                    metric.replace("_increase_percent", "").replace("_minimum", "")
                )
                current_value = current_performance.get(
                    metric.replace("_increase_percent", "").replace("_minimum", "")
                )

                if baseline_value is None or current_value is None:
                    continue

                if "_increase_percent" in metric:
                    # 증가율 체크 (예: 메모리 사용량 증가)
                    if baseline_value > 0:
                        increase_percent = (
                            (current_value - baseline_value) / baseline_value
                        ) * 100
                        if increase_percent > threshold:
                            logger.warning(
                                "performance_degradation_detected",
                                metric=metric,
                                baseline=baseline_value,
                                current=current_value,
                                increase_percent=increase_percent,
                                threshold=threshold,
                            )
                            return True

                elif "_minimum" in metric:
                    # 최소값 체크 (예: 캐시 히트율)
                    if current_value < threshold:
                        logger.warning(
                            "performance_below_minimum",
                            metric=metric,
                            current=current_value,
                            minimum=threshold,
                        )
                        return True

            return False

        except Exception as e:
            logger.error("rollback_check_failed", rule_id=rule.id, error=str(e))
            return False

    def get_optimization_status(self) -> Dict[str, Any]:
        """최적화 상태 조회"""
        try:
            status_summary = {
                "total_rules": len(self.optimization_rules),
                "enabled_rules": len(
                    [
                        r
                        for r in self.optimization_rules.values()
                        if r.status == OptimizationStatus.ENABLED
                    ]
                ),
                "disabled_rules": len(
                    [
                        r
                        for r in self.optimization_rules.values()
                        if r.status == OptimizationStatus.DISABLED
                    ]
                ),
                "error_rules": len(
                    [
                        r
                        for r in self.optimization_rules.values()
                        if r.status == OptimizationStatus.ERROR
                    ]
                ),
                "monitoring_active": self.is_monitoring,
                "baseline_set": bool(self.performance_baseline),
                "rules": [],
            }

            for rule in self.optimization_rules.values():
                rule_info = {
                    "id": rule.id,
                    "name": rule.name,
                    "description": rule.description,
                    "type": rule.optimization_type.value,
                    "status": rule.status.value,
                    "target_services": rule.target_services,
                    "enabled_at": (
                        rule.enabled_at.isoformat() if rule.enabled_at else None
                    ),
                    "disabled_at": (
                        rule.disabled_at.isoformat() if rule.disabled_at else None
                    ),
                    "dependencies": rule.dependencies or [],
                }
                status_summary["rules"].append(rule_info)

            return status_summary

        except Exception as e:
            logger.error("optimization_status_retrieval_failed", error=str(e))
            return {"error": str(e)}

    def get_optimization_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """최적화 적용 히스토리 조회"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            recent_history = [
                result
                for result in self.optimization_history
                if result.applied_at >= cutoff_time
            ]

            history_data = []
            for result in recent_history:
                history_data.append(
                    {
                        "rule_id": result.rule_id,
                        "status": result.status.value,
                        "applied_at": result.applied_at.isoformat(),
                        "performance_before": result.performance_before,
                        "performance_after": result.performance_after,
                        "error_message": result.error_message,
                        "rollback_reason": result.rollback_reason,
                    }
                )

            return history_data

        except Exception as e:
            logger.error("optimization_history_retrieval_failed", error=str(e))
            return []


# 글로벌 최적화 매니저 인스턴스
_optimization_manager = None


def get_optimization_manager() -> OptimizationManager:
    """글로벌 최적화 매니저 인스턴스 조회"""
    global _optimization_manager
    if _optimization_manager is None:
        _optimization_manager = OptimizationManager()
    return _optimization_manager
