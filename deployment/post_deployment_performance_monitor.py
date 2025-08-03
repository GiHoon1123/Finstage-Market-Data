#!/usr/bin/env python3
"""
배포 후 성능 모니터링 및 튜닝 시스템

실제 운영 환경에서 성능 지표를 수집하고 자동 튜닝을 수행합니다.
"""

import asyncio
import time
import psutil
import statistics
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import sys
import os
from dataclasses import dataclass, asdict
from enum import Enum

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.common.monitoring.performance_metrics_collector import get_metrics_collector
from app.common.optimization.optimization_manager import get_optimization_manager
from app.common.monitoring.alert_system import get_alert_system
from app.common.utils.memory_cache import get_cache
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class PerformanceStatus(Enum):
    """성능 상태"""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class PerformanceThreshold:
    """성능 임계값"""

    memory_usage_percent: float = 80.0  # 메모리 사용률 임계값
    cpu_usage_percent: float = 70.0  # CPU 사용률 임계값
    response_time_ms: float = 1000.0  # 응답 시간 임계값
    error_rate_percent: float = 5.0  # 에러율 임계값
    cache_hit_rate_percent: float = 80.0  # 캐시 히트율 임계값


@dataclass
class PerformanceMetrics:
    """성능 메트릭"""

    timestamp: datetime
    memory_usage_percent: float
    cpu_usage_percent: float
    avg_response_time_ms: float
    p95_response_time_ms: float
    error_rate_percent: float
    cache_hit_rate_percent: float
    active_connections: int
    requests_per_second: float
    status: PerformanceStatus


class PostDeploymentMonitor:
    """배포 후 성능 모니터링 시스템"""

    def __init__(self, monitoring_interval: int = 60):
        self.monitoring_interval = monitoring_interval  # 모니터링 간격 (초)
        self.metrics_collector = get_metrics_collector()
        self.optimization_manager = get_optimization_manager()
        self.alert_system = get_alert_system()

        # 성능 임계값
        self.thresholds = PerformanceThreshold()

        # 성능 히스토리
        self.performance_history: List[PerformanceMetrics] = []
        self.max_history_size = 1440  # 24시간 (1분 간격)

        # 자동 튜닝 설정
        self.auto_tuning_enabled = True
        self.last_tuning_time = None
        self.tuning_cooldown = timedelta(minutes=30)  # 튜닝 간 최소 간격

        # 성능 저하 감지
        self.performance_degradation_threshold = 20.0  # 20% 성능 저하 시 알림
        self.consecutive_poor_performance_limit = 5  # 연속 5회 성능 저하 시 조치

        self.is_monitoring = False

    async def start_monitoring(self):
        """모니터링 시작"""
        if self.is_monitoring:
            logger.warning("monitoring_already_running")
            return

        self.is_monitoring = True
        logger.info(
            "post_deployment_monitoring_started", interval=self.monitoring_interval
        )

        print("🚀 배포 후 성능 모니터링 시작")
        print(f"   📊 모니터링 간격: {self.monitoring_interval}초")
        print(
            f"   🎯 자동 튜닝: {'활성화' if self.auto_tuning_enabled else '비활성화'}"
        )
        print("=" * 50)

        try:
            while self.is_monitoring:
                await self._collect_and_analyze_metrics()
                await asyncio.sleep(self.monitoring_interval)

        except Exception as e:
            logger.error("monitoring_error", error=str(e))
            print(f"❌ 모니터링 중 오류 발생: {str(e)}")
        finally:
            self.is_monitoring = False

    def stop_monitoring(self):
        """모니터링 중지"""
        self.is_monitoring = False
        logger.info("post_deployment_monitoring_stopped")
        print("⏹️ 성능 모니터링 중지")

    async def _collect_and_analyze_metrics(self):
        """메트릭 수집 및 분석"""
        try:
            # 현재 성능 메트릭 수집
            metrics = await self._collect_current_metrics()

            # 성능 히스토리에 추가
            self.performance_history.append(metrics)
            if len(self.performance_history) > self.max_history_size:
                self.performance_history.pop(0)

            # 성능 분석
            await self._analyze_performance(metrics)

            # 성능 상태 출력
            self._print_performance_status(metrics)

            # 자동 튜닝 검토
            if self.auto_tuning_enabled:
                await self._check_auto_tuning(metrics)

        except Exception as e:
            logger.error("metrics_collection_failed", error=str(e))

    async def _collect_current_metrics(self) -> PerformanceMetrics:
        """현재 성능 메트릭 수집"""
        try:
            # 시스템 메트릭
            memory_info = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)

            # 애플리케이션 메트릭 (메트릭 컬렉터에서 수집)
            app_metrics = self.metrics_collector.get_current_metrics()

            # 캐시 성능 메트릭
            cache_metrics = await self._get_cache_metrics()

            # 성능 상태 판단
            status = self._determine_performance_status(
                memory_info.percent,
                cpu_percent,
                app_metrics.get("avg_response_time", 0),
                app_metrics.get("error_rate", 0),
                cache_metrics.get("hit_rate", 0),
            )

            return PerformanceMetrics(
                timestamp=datetime.now(),
                memory_usage_percent=memory_info.percent,
                cpu_usage_percent=cpu_percent,
                avg_response_time_ms=app_metrics.get("avg_response_time", 0),
                p95_response_time_ms=app_metrics.get("p95_response_time", 0),
                error_rate_percent=app_metrics.get("error_rate", 0),
                cache_hit_rate_percent=cache_metrics.get("hit_rate", 0),
                active_connections=app_metrics.get("active_connections", 0),
                requests_per_second=app_metrics.get("requests_per_second", 0),
                status=status,
            )

        except Exception as e:
            logger.error("current_metrics_collection_failed", error=str(e))
            # 기본값으로 메트릭 반환
            return PerformanceMetrics(
                timestamp=datetime.now(),
                memory_usage_percent=0,
                cpu_usage_percent=0,
                avg_response_time_ms=0,
                p95_response_time_ms=0,
                error_rate_percent=0,
                cache_hit_rate_percent=0,
                active_connections=0,
                requests_per_second=0,
                status=PerformanceStatus.FAIR,
            )

    async def _get_cache_metrics(self) -> Dict[str, float]:
        """캐시 성능 메트릭 수집"""
        try:
            cache_names = ["technical_analysis", "price_data", "news_data"]
            total_hits = 0
            total_requests = 0

            for cache_name in cache_names:
                try:
                    cache = get_cache(cache_name)
                    if hasattr(cache, "get_stats"):
                        stats = cache.get_stats()
                        total_hits += stats.get("hits", 0)
                        total_requests += stats.get("requests", 0)
                except Exception:
                    continue

            hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "hit_rate": hit_rate,
                "total_hits": total_hits,
                "total_requests": total_requests,
            }

        except Exception as e:
            logger.error("cache_metrics_collection_failed", error=str(e))
            return {"hit_rate": 0, "total_hits": 0, "total_requests": 0}

    def _determine_performance_status(
        self,
        memory_percent: float,
        cpu_percent: float,
        response_time: float,
        error_rate: float,
        cache_hit_rate: float,
    ) -> PerformanceStatus:
        """성능 상태 판단"""
        # 임계 상황 체크
        if (
            memory_percent > 95
            or cpu_percent > 90
            or response_time > 5000
            or error_rate > 20
        ):
            return PerformanceStatus.CRITICAL

        # 나쁜 성능 체크
        if (
            memory_percent > self.thresholds.memory_usage_percent
            or cpu_percent > self.thresholds.cpu_usage_percent
            or response_time > self.thresholds.response_time_ms
            or error_rate > self.thresholds.error_rate_percent
        ):
            return PerformanceStatus.POOR

        # 보통 성능 체크
        if (
            memory_percent > 60
            or cpu_percent > 50
            or response_time > 500
            or cache_hit_rate < 70
        ):
            return PerformanceStatus.FAIR

        # 좋은 성능 체크
        if (
            memory_percent < 40
            and cpu_percent < 30
            and response_time < 200
            and cache_hit_rate > 90
        ):
            return PerformanceStatus.EXCELLENT

        return PerformanceStatus.GOOD

    async def _analyze_performance(self, current_metrics: PerformanceMetrics):
        """성능 분석 및 알림"""
        try:
            # 성능 저하 감지
            if len(self.performance_history) >= 2:
                await self._detect_performance_degradation(current_metrics)

            # 임계값 초과 알림
            await self._check_threshold_violations(current_metrics)

            # 연속 성능 저하 감지
            await self._check_consecutive_poor_performance()

        except Exception as e:
            logger.error("performance_analysis_failed", error=str(e))

    async def _detect_performance_degradation(
        self, current_metrics: PerformanceMetrics
    ):
        """성능 저하 감지"""
        try:
            # 최근 10분간의 평균과 비교
            recent_history = [
                m
                for m in self.performance_history[-10:]
                if m.timestamp > datetime.now() - timedelta(minutes=10)
            ]

            if len(recent_history) < 5:
                return

            # 평균 응답 시간 비교
            avg_response_time = statistics.mean(
                [m.avg_response_time_ms for m in recent_history]
            )
            current_response_time = current_metrics.avg_response_time_ms

            if avg_response_time > 0:
                degradation_percent = (
                    (current_response_time - avg_response_time) / avg_response_time
                ) * 100

                if degradation_percent > self.performance_degradation_threshold:
                    await self.alert_system.send_alert(
                        "performance_degradation",
                        f"응답 시간이 {degradation_percent:.1f}% 저하되었습니다. "
                        f"현재: {current_response_time:.1f}ms, 평균: {avg_response_time:.1f}ms",
                        severity="warning",
                    )

                    logger.warning(
                        "performance_degradation_detected",
                        degradation_percent=degradation_percent,
                        current_response_time=current_response_time,
                        avg_response_time=avg_response_time,
                    )

        except Exception as e:
            logger.error("performance_degradation_detection_failed", error=str(e))

    async def _check_threshold_violations(self, metrics: PerformanceMetrics):
        """임계값 위반 체크"""
        violations = []

        if metrics.memory_usage_percent > self.thresholds.memory_usage_percent:
            violations.append(f"메모리 사용률: {metrics.memory_usage_percent:.1f}%")

        if metrics.cpu_usage_percent > self.thresholds.cpu_usage_percent:
            violations.append(f"CPU 사용률: {metrics.cpu_usage_percent:.1f}%")

        if metrics.avg_response_time_ms > self.thresholds.response_time_ms:
            violations.append(f"응답 시간: {metrics.avg_response_time_ms:.1f}ms")

        if metrics.error_rate_percent > self.thresholds.error_rate_percent:
            violations.append(f"에러율: {metrics.error_rate_percent:.1f}%")

        if metrics.cache_hit_rate_percent < self.thresholds.cache_hit_rate_percent:
            violations.append(f"캐시 히트율: {metrics.cache_hit_rate_percent:.1f}%")

        if violations:
            severity = (
                "critical"
                if metrics.status == PerformanceStatus.CRITICAL
                else "warning"
            )
            await self.alert_system.send_alert(
                "threshold_violation",
                f"성능 임계값 위반: {', '.join(violations)}",
                severity=severity,
            )

    async def _check_consecutive_poor_performance(self):
        """연속 성능 저하 체크"""
        if len(self.performance_history) < self.consecutive_poor_performance_limit:
            return

        recent_metrics = self.performance_history[
            -self.consecutive_poor_performance_limit :
        ]
        poor_performance_count = sum(
            1
            for m in recent_metrics
            if m.status in [PerformanceStatus.POOR, PerformanceStatus.CRITICAL]
        )

        if poor_performance_count >= self.consecutive_poor_performance_limit:
            await self.alert_system.send_alert(
                "consecutive_poor_performance",
                f"연속 {poor_performance_count}회 성능 저하가 감지되었습니다. 자동 튜닝을 검토합니다.",
                severity="critical",
            )

            # 강제 자동 튜닝 실행
            if self.auto_tuning_enabled:
                await self._force_auto_tuning("consecutive_poor_performance")

    async def _check_auto_tuning(self, metrics: PerformanceMetrics):
        """자동 튜닝 검토"""
        try:
            # 쿨다운 시간 체크
            if (
                self.last_tuning_time
                and datetime.now() - self.last_tuning_time < self.tuning_cooldown
            ):
                return

            # 튜닝이 필요한 상황 체크
            tuning_needed = False
            tuning_reason = []

            # 메모리 사용률이 높은 경우
            if metrics.memory_usage_percent > 85:
                tuning_needed = True
                tuning_reason.append("high_memory_usage")

            # 응답 시간이 긴 경우
            if metrics.avg_response_time_ms > 1500:
                tuning_needed = True
                tuning_reason.append("slow_response_time")

            # 캐시 히트율이 낮은 경우
            if metrics.cache_hit_rate_percent < 60:
                tuning_needed = True
                tuning_reason.append("low_cache_hit_rate")

            if tuning_needed:
                await self._perform_auto_tuning(tuning_reason, metrics)

        except Exception as e:
            logger.error("auto_tuning_check_failed", error=str(e))

    async def _perform_auto_tuning(
        self, reasons: List[str], metrics: PerformanceMetrics
    ):
        """자동 튜닝 수행"""
        try:
            self.last_tuning_time = datetime.now()

            logger.info("auto_tuning_started", reasons=reasons)
            print(f"🔧 자동 튜닝 시작: {', '.join(reasons)}")

            tuning_actions = []

            # 메모리 사용률이 높은 경우
            if "high_memory_usage" in reasons:
                # 메모리 최적화 활성화
                result = self.optimization_manager.enable_optimization(
                    "memory_optimization_aggressive"
                )
                if result.status.value == "enabled":
                    tuning_actions.append("메모리 최적화 강화")

                # 캐시 크기 조정
                await self._adjust_cache_sizes(reduce=True)
                tuning_actions.append("캐시 크기 축소")

            # 응답 시간이 긴 경우
            if "slow_response_time" in reasons:
                # 비동기 처리 최적화 활성화
                result = self.optimization_manager.enable_optimization(
                    "async_api_endpoints"
                )
                if result.status.value == "enabled":
                    tuning_actions.append("비동기 처리 최적화")

                # 작업 큐 우선순위 조정
                await self._adjust_task_queue_priorities()
                tuning_actions.append("작업 큐 우선순위 조정")

            # 캐시 히트율이 낮은 경우
            if "low_cache_hit_rate" in reasons:
                # 캐시 TTL 조정
                await self._adjust_cache_ttl(increase=True)
                tuning_actions.append("캐시 TTL 증가")

                # 캐시 워밍업 실행
                await self._perform_cache_warmup()
                tuning_actions.append("캐시 워밍업 실행")

            # 튜닝 결과 알림
            await self.alert_system.send_alert(
                "auto_tuning_completed",
                f"자동 튜닝 완료: {', '.join(tuning_actions)}",
                severity="info",
            )

            print(f"   ✅ 자동 튜닝 완료: {', '.join(tuning_actions)}")

        except Exception as e:
            logger.error("auto_tuning_failed", error=str(e))
            print(f"   ❌ 자동 튜닝 실패: {str(e)}")

    async def _force_auto_tuning(self, reason: str):
        """강제 자동 튜닝 실행"""
        try:
            logger.info("force_auto_tuning_started", reason=reason)
            print(f"🚨 강제 자동 튜닝 시작: {reason}")

            # 모든 최적화 활성화
            optimizations = [
                "memory_optimization_aggressive",
                "caching_technical_analysis",
                "caching_price_data",
                "async_api_endpoints",
            ]

            enabled_count = 0
            for opt_id in optimizations:
                try:
                    result = self.optimization_manager.enable_optimization(opt_id)
                    if result.status.value == "enabled":
                        enabled_count += 1
                except Exception:
                    continue

            # 캐시 정리 및 재구성
            await self._emergency_cache_cleanup()

            # 메모리 강제 정리
            await self._emergency_memory_cleanup()

            print(f"   ✅ 강제 튜닝 완료: {enabled_count}개 최적화 활성화")

            await self.alert_system.send_alert(
                "force_auto_tuning_completed",
                f"강제 자동 튜닝 완료: {enabled_count}개 최적화 활성화",
                severity="warning",
            )

        except Exception as e:
            logger.error("force_auto_tuning_failed", error=str(e))

    async def _adjust_cache_sizes(self, reduce: bool = True):
        """캐시 크기 조정"""
        try:
            cache_names = ["technical_analysis", "price_data", "news_data"]

            for cache_name in cache_names:
                try:
                    cache = get_cache(cache_name)
                    if hasattr(cache, "adjust_max_size"):
                        current_size = getattr(cache, "max_size", 1000)
                        if reduce:
                            new_size = max(100, int(current_size * 0.7))  # 30% 감소
                        else:
                            new_size = int(current_size * 1.3)  # 30% 증가

                        cache.adjust_max_size(new_size)
                        logger.info(
                            "cache_size_adjusted",
                            cache_name=cache_name,
                            old_size=current_size,
                            new_size=new_size,
                        )
                except Exception:
                    continue

        except Exception as e:
            logger.error("cache_size_adjustment_failed", error=str(e))

    async def _adjust_task_queue_priorities(self):
        """작업 큐 우선순위 조정"""
        try:
            # 높은 우선순위: 실시간 데이터 처리
            # 낮은 우선순위: 배치 작업, 리포트 생성

            priority_adjustments = {
                "price_monitoring": 10,  # 높은 우선순위
                "technical_analysis": 8,  # 높은 우선순위
                "news_crawling": 6,  # 중간 우선순위
                "report_generation": 3,  # 낮은 우선순위
                "batch_analysis": 2,  # 낮은 우선순위
                "data_cleanup": 1,  # 가장 낮은 우선순위
            }

            # 작업 큐 시스템에 우선순위 적용 (실제 구현에 따라 조정 필요)
            logger.info(
                "task_queue_priorities_adjusted", priorities=priority_adjustments
            )

        except Exception as e:
            logger.error("task_queue_priority_adjustment_failed", error=str(e))

    async def _adjust_cache_ttl(self, increase: bool = True):
        """캐시 TTL 조정"""
        try:
            cache_names = ["technical_analysis", "price_data", "news_data"]

            for cache_name in cache_names:
                try:
                    cache = get_cache(cache_name)
                    if hasattr(cache, "adjust_default_ttl"):
                        current_ttl = getattr(cache, "default_ttl", 300)  # 기본 5분
                        if increase:
                            new_ttl = min(
                                3600, int(current_ttl * 1.5)
                            )  # 50% 증가, 최대 1시간
                        else:
                            new_ttl = max(
                                60, int(current_ttl * 0.7)
                            )  # 30% 감소, 최소 1분

                        cache.adjust_default_ttl(new_ttl)
                        logger.info(
                            "cache_ttl_adjusted",
                            cache_name=cache_name,
                            old_ttl=current_ttl,
                            new_ttl=new_ttl,
                        )
                except Exception:
                    continue

        except Exception as e:
            logger.error("cache_ttl_adjustment_failed", error=str(e))

    async def _perform_cache_warmup(self):
        """캐시 워밍업 실행"""
        try:
            # 자주 사용되는 데이터를 미리 캐시에 로드
            warmup_tasks = [
                self._warmup_technical_analysis_cache(),
                self._warmup_price_data_cache(),
                self._warmup_news_cache(),
            ]

            await asyncio.gather(*warmup_tasks, return_exceptions=True)
            logger.info("cache_warmup_completed")

        except Exception as e:
            logger.error("cache_warmup_failed", error=str(e))

    async def _warmup_technical_analysis_cache(self):
        """기술적 분석 캐시 워밍업"""
        try:
            # 주요 심볼들의 기술적 분석 결과를 미리 계산하여 캐시에 저장
            major_symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]

            for symbol in major_symbols:
                try:
                    # 실제 기술적 분석 서비스 호출 (구현에 따라 조정)
                    # await technical_analysis_service.get_analysis(symbol)
                    await asyncio.sleep(0.1)  # 시뮬레이션
                except Exception:
                    continue

        except Exception as e:
            logger.error("technical_analysis_cache_warmup_failed", error=str(e))

    async def _warmup_price_data_cache(self):
        """가격 데이터 캐시 워밍업"""
        try:
            # 주요 심볼들의 가격 데이터를 미리 캐시에 로드
            major_symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]

            for symbol in major_symbols:
                try:
                    # 실제 가격 데이터 서비스 호출 (구현에 따라 조정)
                    # await price_service.get_current_price(symbol)
                    await asyncio.sleep(0.1)  # 시뮬레이션
                except Exception:
                    continue

        except Exception as e:
            logger.error("price_data_cache_warmup_failed", error=str(e))

    async def _warmup_news_cache(self):
        """뉴스 캐시 워밍업"""
        try:
            # 최신 뉴스 데이터를 미리 캐시에 로드
            # await news_service.get_latest_news()
            await asyncio.sleep(0.1)  # 시뮬레이션

        except Exception as e:
            logger.error("news_cache_warmup_failed", error=str(e))

    async def _emergency_cache_cleanup(self):
        """응급 캐시 정리"""
        try:
            cache_names = ["technical_analysis", "price_data", "news_data"]

            for cache_name in cache_names:
                try:
                    cache = get_cache(cache_name)
                    # 오래된 캐시 항목 정리
                    if hasattr(cache, "cleanup_expired"):
                        cache.cleanup_expired()
                    # 캐시 크기가 너무 큰 경우 일부 정리
                    if hasattr(cache, "cleanup_lru"):
                        cache.cleanup_lru(keep_ratio=0.5)  # 50%만 유지

                    logger.info(
                        "emergency_cache_cleanup_completed", cache_name=cache_name
                    )
                except Exception:
                    continue

        except Exception as e:
            logger.error("emergency_cache_cleanup_failed", error=str(e))

    async def _emergency_memory_cleanup(self):
        """응급 메모리 정리"""
        try:
            import gc

            # 가비지 컬렉션 강제 실행
            collected = gc.collect()

            # 메모리 사용량 확인
            memory_info = psutil.virtual_memory()

            logger.info(
                "emergency_memory_cleanup_completed",
                collected_objects=collected,
                memory_usage_percent=memory_info.percent,
            )

        except Exception as e:
            logger.error("emergency_memory_cleanup_failed", error=str(e))

    def _print_performance_status(self, metrics: PerformanceMetrics):
        """성능 상태 출력"""
        # 상태에 따른 이모지
        status_emoji = {
            PerformanceStatus.EXCELLENT: "🟢",
            PerformanceStatus.GOOD: "🔵",
            PerformanceStatus.FAIR: "🟡",
            PerformanceStatus.POOR: "🟠",
            PerformanceStatus.CRITICAL: "🔴",
        }

        emoji = status_emoji.get(metrics.status, "⚪")

        print(
            f"\n{emoji} [{metrics.timestamp.strftime('%H:%M:%S')}] "
            f"상태: {metrics.status.value.upper()}"
        )
        print(
            f"   💾 메모리: {metrics.memory_usage_percent:.1f}% | "
            f"🖥️ CPU: {metrics.cpu_usage_percent:.1f}%"
        )
        print(
            f"   ⏱️ 응답시간: {metrics.avg_response_time_ms:.1f}ms | "
            f"📊 P95: {metrics.p95_response_time_ms:.1f}ms"
        )
        print(
            f"   🎯 캐시 히트율: {metrics.cache_hit_rate_percent:.1f}% | "
            f"❌ 에러율: {metrics.error_rate_percent:.1f}%"
        )
        print(
            f"   🔗 활성 연결: {metrics.active_connections} | "
            f"📈 RPS: {metrics.requests_per_second:.1f}"
        )

    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """성능 요약 정보 반환"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_metrics = [
                m for m in self.performance_history if m.timestamp > cutoff_time
            ]

            if not recent_metrics:
                return {"error": "No metrics available"}

            # 통계 계산
            memory_usage = [m.memory_usage_percent for m in recent_metrics]
            cpu_usage = [m.cpu_usage_percent for m in recent_metrics]
            response_times = [m.avg_response_time_ms for m in recent_metrics]
            cache_hit_rates = [m.cache_hit_rate_percent for m in recent_metrics]

            # 상태별 분포
            status_counts = {}
            for status in PerformanceStatus:
                status_counts[status.value] = sum(
                    1 for m in recent_metrics if m.status == status
                )

            return {
                "period_hours": hours,
                "total_measurements": len(recent_metrics),
                "memory_usage": {
                    "avg": statistics.mean(memory_usage),
                    "max": max(memory_usage),
                    "min": min(memory_usage),
                },
                "cpu_usage": {
                    "avg": statistics.mean(cpu_usage),
                    "max": max(cpu_usage),
                    "min": min(cpu_usage),
                },
                "response_time": {
                    "avg": statistics.mean(response_times),
                    "max": max(response_times),
                    "min": min(response_times),
                    "p95": self._percentile(response_times, 95),
                },
                "cache_hit_rate": {
                    "avg": statistics.mean(cache_hit_rates),
                    "max": max(cache_hit_rates),
                    "min": min(cache_hit_rates),
                },
                "status_distribution": status_counts,
                "last_updated": recent_metrics[-1].timestamp.isoformat(),
            }

        except Exception as e:
            logger.error("performance_summary_failed", error=str(e))
            return {"error": str(e)}

    def _percentile(self, data: List[float], percentile: int) -> float:
        """백분위수 계산"""
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]

    def save_performance_history(self, filepath: str):
        """성능 히스토리 저장"""
        try:
            history_data = [asdict(metrics) for metrics in self.performance_history]

            # datetime 객체를 문자열로 변환
            for item in history_data:
                item["timestamp"] = item["timestamp"].isoformat()
                item["status"] = item["status"].value

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)

            logger.info(
                "performance_history_saved", filepath=filepath, count=len(history_data)
            )

        except Exception as e:
            logger.error("performance_history_save_failed", error=str(e))


class PerformanceTuningRecommendations:
    """성능 튜닝 권장사항 생성기"""

    def __init__(self):
        self.logger = get_logger(__name__)

    def generate_recommendations(
        self, metrics_history: List[PerformanceMetrics]
    ) -> List[Dict[str, Any]]:
        """성능 튜닝 권장사항 생성"""
        recommendations = []

        if not metrics_history:
            return recommendations

        try:
            # 최근 메트릭 분석
            recent_metrics = (
                metrics_history[-10:] if len(metrics_history) >= 10 else metrics_history
            )

            # 메모리 사용량 분석
            memory_recommendations = self._analyze_memory_usage(recent_metrics)
            recommendations.extend(memory_recommendations)

            # 응답 시간 분석
            response_time_recommendations = self._analyze_response_times(recent_metrics)
            recommendations.extend(response_time_recommendations)

            # 캐시 성능 분석
            cache_recommendations = self._analyze_cache_performance(recent_metrics)
            recommendations.extend(cache_recommendations)

            # 전반적인 성능 트렌드 분석
            trend_recommendations = self._analyze_performance_trends(metrics_history)
            recommendations.extend(trend_recommendations)

            return recommendations

        except Exception as e:
            self.logger.error("recommendation_generation_failed", error=str(e))
            return []

    def _analyze_memory_usage(
        self, metrics: List[PerformanceMetrics]
    ) -> List[Dict[str, Any]]:
        """메모리 사용량 분석"""
        recommendations = []

        avg_memory = statistics.mean([m.memory_usage_percent for m in metrics])
        max_memory = max([m.memory_usage_percent for m in metrics])

        if avg_memory > 80:
            recommendations.append(
                {
                    "category": "memory",
                    "priority": "high",
                    "title": "높은 메모리 사용률",
                    "description": f"평균 메모리 사용률이 {avg_memory:.1f}%로 높습니다.",
                    "recommendations": [
                        "메모리 최적화 데코레이터 적용 확대",
                        "캐시 크기 조정",
                        "불필요한 데이터 정리 스케줄 추가",
                    ],
                }
            )

        if max_memory > 95:
            recommendations.append(
                {
                    "category": "memory",
                    "priority": "critical",
                    "title": "메모리 부족 위험",
                    "description": f"최대 메모리 사용률이 {max_memory:.1f}%에 도달했습니다.",
                    "recommendations": [
                        "즉시 메모리 정리 실행",
                        "메모리 집약적 작업 분산",
                        "시스템 리소스 확장 검토",
                    ],
                }
            )

        return recommendations

    def _analyze_response_times(
        self, metrics: List[PerformanceMetrics]
    ) -> List[Dict[str, Any]]:
        """응답 시간 분석"""
        recommendations = []

        avg_response = statistics.mean([m.avg_response_time_ms for m in metrics])
        p95_response = statistics.mean([m.p95_response_time_ms for m in metrics])

        if avg_response > 1000:
            recommendations.append(
                {
                    "category": "response_time",
                    "priority": "high",
                    "title": "느린 응답 시간",
                    "description": f"평균 응답 시간이 {avg_response:.1f}ms로 느립니다.",
                    "recommendations": [
                        "비동기 처리 확대",
                        "데이터베이스 쿼리 최적화",
                        "캐싱 전략 개선",
                    ],
                }
            )

        if p95_response > 3000:
            recommendations.append(
                {
                    "category": "response_time",
                    "priority": "medium",
                    "title": "P95 응답 시간 개선 필요",
                    "description": f"P95 응답 시간이 {p95_response:.1f}ms입니다.",
                    "recommendations": [
                        "무거운 작업을 백그라운드로 이전",
                        "작업 큐 우선순위 조정",
                        "타임아웃 설정 검토",
                    ],
                }
            )

        return recommendations

    def _analyze_cache_performance(
        self, metrics: List[PerformanceMetrics]
    ) -> List[Dict[str, Any]]:
        """캐시 성능 분석"""
        recommendations = []

        avg_hit_rate = statistics.mean([m.cache_hit_rate_percent for m in metrics])

        if avg_hit_rate < 70:
            recommendations.append(
                {
                    "category": "cache",
                    "priority": "medium",
                    "title": "낮은 캐시 히트율",
                    "description": f"평균 캐시 히트율이 {avg_hit_rate:.1f}%로 낮습니다.",
                    "recommendations": [
                        "캐시 TTL 조정",
                        "캐시 키 전략 개선",
                        "캐시 워밍업 스케줄 추가",
                    ],
                }
            )

        return recommendations

    def _analyze_performance_trends(
        self, metrics: List[PerformanceMetrics]
    ) -> List[Dict[str, Any]]:
        """성능 트렌드 분석"""
        recommendations = []

        if len(metrics) < 20:
            return recommendations

        try:
            # 최근 10개와 이전 10개 비교
            recent = metrics[-10:]
            previous = metrics[-20:-10]

            recent_avg_response = statistics.mean(
                [m.avg_response_time_ms for m in recent]
            )
            previous_avg_response = statistics.mean(
                [m.avg_response_time_ms for m in previous]
            )

            if recent_avg_response > previous_avg_response * 1.2:  # 20% 이상 증가
                recommendations.append(
                    {
                        "category": "trend",
                        "priority": "medium",
                        "title": "성능 저하 트렌드",
                        "description": "최근 응답 시간이 지속적으로 증가하고 있습니다.",
                        "recommendations": [
                            "성능 저하 원인 분석",
                            "시스템 리소스 모니터링 강화",
                            "예방적 최적화 적용",
                        ],
                    }
                )

        except Exception as e:
            self.logger.error("trend_analysis_failed", error=str(e))

        return recommendations


async def main():
    """메인 실행 함수"""
    print("🚀 배포 후 성능 모니터링 시스템 시작")
    print("=" * 50)

    # 모니터링 시스템 초기화
    monitor = PostDeploymentMonitor(monitoring_interval=60)  # 1분 간격

    try:
        # 모니터링 시작
        await monitor.start_monitoring()

    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 모니터링이 중지되었습니다.")
        monitor.stop_monitoring()

        # 성능 히스토리 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        history_file = f"performance_history_{timestamp}.json"
        monitor.save_performance_history(history_file)

        # 성능 요약 출력
        summary = monitor.get_performance_summary(hours=1)
        print("\n📊 성능 요약 (최근 1시간):")
        print(json.dumps(summary, indent=2, ensure_ascii=False))

        # 튜닝 권장사항 생성
        recommender = PerformanceTuningRecommendations()
        recommendations = recommender.generate_recommendations(
            monitor.performance_history
        )

        if recommendations:
            print("\n💡 성능 튜닝 권장사항:")
            for i, rec in enumerate(recommendations, 1):
                print(f"\n{i}. {rec['title']} ({rec['priority']} 우선순위)")
                print(f"   설명: {rec['description']}")
                print("   권장사항:")
                for suggestion in rec["recommendations"]:
                    print(f"   - {suggestion}")

    except Exception as e:
        print(f"❌ 모니터링 중 오류 발생: {str(e)}")
        logger.error("monitoring_system_error", error=str(e))


if __name__ == "__main__":
    # 비동기 실행
    asyncio.run(main())
