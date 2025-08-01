"""
데이터베이스 연결 풀 최적화 관리자

이 모듈은 SQLAlchemy 연결 풀을 동적으로 관리하고 최적화합니다.
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from sqlalchemy import event

from app.common.utils.logging_config import get_logger
from app.common.monitoring.metrics import metrics_collector
from app.common.monitoring.alerts import send_warning_alert, send_critical_alert

logger = get_logger(__name__)


@dataclass
class ConnectionPoolMetrics:
    """연결 풀 메트릭"""

    pool_size: int
    checked_out: int
    overflow: int
    checked_in: int
    total_connections: int
    failed_connections: int
    avg_checkout_time: float
    max_checkout_time: float
    pool_utilization: float
    timestamp: datetime


@dataclass
class ConnectionPoolConfig:
    """연결 풀 설정"""

    min_pool_size: int = 5
    max_pool_size: int = 20
    max_overflow: int = 30
    pool_timeout: int = 300
    pool_recycle: int = 600
    pool_pre_ping: bool = True

    # 동적 조정 설정
    utilization_threshold_high: float = 0.8  # 80% 이상 사용 시 확장
    utilization_threshold_low: float = 0.3  # 30% 이하 사용 시 축소
    adjustment_interval: int = 300  # 5분마다 조정 검토
    max_adjustment_step: int = 5  # 한 번에 최대 5개 연결 조정


class ConnectionPoolManager:
    """연결 풀 관리자"""

    def __init__(self, engine: Engine, config: Optional[ConnectionPoolConfig] = None):
        self.engine = engine
        self.config = config or ConnectionPoolConfig()
        self.metrics_history = []
        self.last_adjustment = datetime.now()
        self._lock = threading.Lock()

        # 연결 풀 이벤트 추적
        self.connection_events = {
            "connect_count": 0,
            "disconnect_count": 0,
            "checkout_count": 0,
            "checkin_count": 0,
            "failed_count": 0,
            "checkout_times": [],
        }

        self._setup_pool_monitoring()

    def _setup_pool_monitoring(self):
        """연결 풀 모니터링 설정"""

        @event.listens_for(self.engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """연결 생성 시"""
            with self._lock:
                self.connection_events["connect_count"] += 1
            logger.debug("connection_pool_connect")

        @event.listens_for(self.engine, "close")
        def on_close(dbapi_connection, connection_record):
            """연결 종료 시"""
            with self._lock:
                self.connection_events["disconnect_count"] += 1
            logger.debug("connection_pool_disconnect")

        @event.listens_for(self.engine.pool, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            """연결 체크아웃 시"""
            connection_record._checkout_time = time.time()
            with self._lock:
                self.connection_events["checkout_count"] += 1
            logger.debug("connection_pool_checkout")

        @event.listens_for(self.engine.pool, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            """연결 체크인 시"""
            if hasattr(connection_record, "_checkout_time"):
                checkout_duration = time.time() - connection_record._checkout_time
                with self._lock:
                    self.connection_events["checkout_times"].append(checkout_duration)
                    # 최근 100개만 유지
                    if len(self.connection_events["checkout_times"]) > 100:
                        self.connection_events["checkout_times"].pop(0)

                # 긴 체크아웃 시간 경고
                if checkout_duration > 60:  # 1분 이상
                    logger.warning(
                        "long_connection_checkout", duration=checkout_duration
                    )

            with self._lock:
                self.connection_events["checkin_count"] += 1
            logger.debug("connection_pool_checkin")

        @event.listens_for(self.engine.pool, "connect")
        def on_pool_connect(dbapi_connection, connection_record):
            """풀에서 새 연결 생성 시"""
            logger.debug("connection_pool_new_connection")

        logger.info("connection_pool_monitoring_enabled")

    def get_current_metrics(self) -> ConnectionPoolMetrics:
        """현재 연결 풀 메트릭 조회"""
        pool = self.engine.pool

        # 기본 풀 정보
        pool_size = pool.size()
        checked_out = pool.checkedout()
        overflow = pool.overflow()
        checked_in = pool.checkedin()

        # 계산된 메트릭
        total_connections = pool_size + overflow
        pool_utilization = (
            (checked_out / total_connections) if total_connections > 0 else 0
        )

        # 체크아웃 시간 통계
        with self._lock:
            checkout_times = self.connection_events["checkout_times"].copy()
            failed_connections = self.connection_events["failed_count"]

        avg_checkout_time = (
            sum(checkout_times) / len(checkout_times) if checkout_times else 0
        )
        max_checkout_time = max(checkout_times) if checkout_times else 0

        metrics = ConnectionPoolMetrics(
            pool_size=pool_size,
            checked_out=checked_out,
            overflow=overflow,
            checked_in=checked_in,
            total_connections=total_connections,
            failed_connections=failed_connections,
            avg_checkout_time=avg_checkout_time,
            max_checkout_time=max_checkout_time,
            pool_utilization=pool_utilization,
            timestamp=datetime.now(),
        )

        # 메트릭 히스토리에 추가
        self.metrics_history.append(metrics)
        # 최근 24시간만 유지
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.metrics_history = [
            m for m in self.metrics_history if m.timestamp >= cutoff_time
        ]

        # Prometheus 메트릭 업데이트
        metrics_collector.update_db_connections(total_connections)

        return metrics

    async def check_and_adjust_pool(self) -> Dict[str, Any]:
        """연결 풀 상태 확인 및 동적 조정"""
        current_metrics = self.get_current_metrics()

        # 조정 간격 확인
        if datetime.now() - self.last_adjustment < timedelta(
            seconds=self.config.adjustment_interval
        ):
            return {"status": "no_adjustment", "reason": "too_soon"}

        adjustment_made = False
        adjustment_reason = ""

        # 높은 사용률 - 풀 확장
        if current_metrics.pool_utilization > self.config.utilization_threshold_high:
            if current_metrics.pool_size < self.config.max_pool_size:
                new_size = min(
                    current_metrics.pool_size + self.config.max_adjustment_step,
                    self.config.max_pool_size,
                )

                await self._adjust_pool_size(new_size)
                adjustment_made = True
                adjustment_reason = (
                    f"High utilization ({current_metrics.pool_utilization:.2%})"
                )

                await send_warning_alert(
                    title="Database Connection Pool Expanded",
                    message=f"Pool size increased to {new_size} due to high utilization",
                    component="database",
                    details={
                        "old_size": current_metrics.pool_size,
                        "new_size": new_size,
                        "utilization": current_metrics.pool_utilization,
                    },
                )

        # 낮은 사용률 - 풀 축소
        elif current_metrics.pool_utilization < self.config.utilization_threshold_low:
            if current_metrics.pool_size > self.config.min_pool_size:
                new_size = max(
                    current_metrics.pool_size - self.config.max_adjustment_step,
                    self.config.min_pool_size,
                )

                await self._adjust_pool_size(new_size)
                adjustment_made = True
                adjustment_reason = (
                    f"Low utilization ({current_metrics.pool_utilization:.2%})"
                )

        # 풀 고갈 경고
        if current_metrics.pool_utilization > 0.95:
            await send_critical_alert(
                title="Database Connection Pool Nearly Exhausted",
                message=f"Pool utilization at {current_metrics.pool_utilization:.2%}",
                component="database",
                details={
                    "pool_size": current_metrics.pool_size,
                    "checked_out": current_metrics.checked_out,
                    "overflow": current_metrics.overflow,
                },
            )

        # 긴 체크아웃 시간 경고
        if current_metrics.avg_checkout_time > 30:  # 30초 이상
            await send_warning_alert(
                title="Long Database Connection Checkout Time",
                message=f"Average checkout time: {current_metrics.avg_checkout_time:.2f}s",
                component="database",
                details={
                    "avg_checkout_time": current_metrics.avg_checkout_time,
                    "max_checkout_time": current_metrics.max_checkout_time,
                },
            )

        if adjustment_made:
            self.last_adjustment = datetime.now()
            logger.info(
                "connection_pool_adjusted",
                reason=adjustment_reason,
                new_size=(
                    new_size if "new_size" in locals() else current_metrics.pool_size
                ),
            )

        return {
            "status": "adjusted" if adjustment_made else "no_adjustment",
            "reason": adjustment_reason,
            "current_metrics": current_metrics.__dict__,
        }

    async def _adjust_pool_size(self, new_size: int):
        """연결 풀 크기 조정"""
        try:
            # SQLAlchemy의 QueuePool은 런타임에 크기 조정이 제한적
            # 실제 구현에서는 새로운 엔진을 생성하거나 풀을 재생성해야 할 수 있음
            logger.info(
                "connection_pool_size_adjustment_requested",
                current_size=self.engine.pool.size(),
                requested_size=new_size,
            )

            # 여기서는 로그만 기록하고 실제 조정은 애플리케이션 재시작 시 적용
            # 운영 환경에서는 더 정교한 구현이 필요

        except Exception as e:
            logger.error("connection_pool_adjustment_failed", error=str(e))

    def get_pool_status(self) -> Dict[str, Any]:
        """연결 풀 상태 조회"""
        current_metrics = self.get_current_metrics()

        # 최근 1시간 평균 사용률
        recent_metrics = [
            m
            for m in self.metrics_history
            if m.timestamp >= datetime.now() - timedelta(hours=1)
        ]

        avg_utilization = (
            sum(m.pool_utilization for m in recent_metrics) / len(recent_metrics)
            if recent_metrics
            else 0
        )

        # 연결 이벤트 통계
        with self._lock:
            events = self.connection_events.copy()

        return {
            "current_metrics": {
                "pool_size": current_metrics.pool_size,
                "checked_out": current_metrics.checked_out,
                "overflow": current_metrics.overflow,
                "total_connections": current_metrics.total_connections,
                "utilization": current_metrics.pool_utilization,
                "avg_checkout_time": current_metrics.avg_checkout_time,
                "max_checkout_time": current_metrics.max_checkout_time,
            },
            "statistics": {
                "avg_utilization_1h": avg_utilization,
                "total_connects": events["connect_count"],
                "total_disconnects": events["disconnect_count"],
                "total_checkouts": events["checkout_count"],
                "total_checkins": events["checkin_count"],
                "failed_connections": events["failed_count"],
            },
            "configuration": {
                "min_pool_size": self.config.min_pool_size,
                "max_pool_size": self.config.max_pool_size,
                "max_overflow": self.config.max_overflow,
                "pool_timeout": self.config.pool_timeout,
                "pool_recycle": self.config.pool_recycle,
            },
            "health_status": self._assess_pool_health(current_metrics),
            "recommendations": self._generate_recommendations(
                current_metrics, avg_utilization
            ),
        }

    def _assess_pool_health(self, metrics: ConnectionPoolMetrics) -> str:
        """연결 풀 건강 상태 평가"""
        if metrics.pool_utilization > 0.95:
            return "CRITICAL"
        elif metrics.pool_utilization > 0.8:
            return "WARNING"
        elif metrics.avg_checkout_time > 30:
            return "WARNING"
        elif metrics.failed_connections > 10:
            return "WARNING"
        else:
            return "HEALTHY"

    def _generate_recommendations(
        self, current_metrics: ConnectionPoolMetrics, avg_utilization: float
    ) -> List[str]:
        """최적화 권장사항 생성"""
        recommendations = []

        if current_metrics.pool_utilization > 0.9:
            recommendations.append("Consider increasing max_pool_size or max_overflow")

        if avg_utilization < 0.2:
            recommendations.append(
                "Pool size might be too large, consider reducing min_pool_size"
            )

        if current_metrics.avg_checkout_time > 10:
            recommendations.append(
                "Long checkout times detected, review connection usage patterns"
            )

        if current_metrics.failed_connections > 5:
            recommendations.append(
                "High connection failure rate, check database connectivity"
            )

        if current_metrics.overflow > current_metrics.pool_size:
            recommendations.append(
                "High overflow usage, consider increasing base pool_size"
            )

        if not recommendations:
            recommendations.append("Connection pool is operating optimally")

        return recommendations

    def get_historical_metrics(self, hours: int = 24) -> List[Dict[str, Any]]:
        """과거 메트릭 조회"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        return [
            {
                "timestamp": m.timestamp.isoformat(),
                "pool_size": m.pool_size,
                "checked_out": m.checked_out,
                "utilization": m.pool_utilization,
                "avg_checkout_time": m.avg_checkout_time,
            }
            for m in self.metrics_history
            if m.timestamp >= cutoff_time
        ]

    async def optimize_pool_settings(self) -> Dict[str, Any]:
        """연결 풀 설정 최적화 권장사항"""
        current_metrics = self.get_current_metrics()

        # 최근 24시간 데이터 분석
        recent_metrics = [
            m
            for m in self.metrics_history
            if m.timestamp >= datetime.now() - timedelta(hours=24)
        ]

        if not recent_metrics:
            return {"status": "insufficient_data"}

        # 통계 계산
        max_utilization = max(m.pool_utilization for m in recent_metrics)
        avg_utilization = sum(m.pool_utilization for m in recent_metrics) / len(
            recent_metrics
        )
        max_checkout_time = max(m.avg_checkout_time for m in recent_metrics)

        # 최적화 권장사항
        recommendations = {
            "current_config": {
                "pool_size": self.config.min_pool_size,
                "max_pool_size": self.config.max_pool_size,
                "max_overflow": self.config.max_overflow,
            },
            "recommended_config": {},
            "reasoning": [],
        }

        # 풀 크기 권장사항
        if max_utilization > 0.8:
            new_pool_size = min(self.config.max_pool_size + 5, 50)
            recommendations["recommended_config"]["pool_size"] = new_pool_size
            recommendations["reasoning"].append(
                f"Increase pool size due to high utilization ({max_utilization:.2%})"
            )

        elif avg_utilization < 0.3:
            new_pool_size = max(self.config.min_pool_size - 2, 3)
            recommendations["recommended_config"]["pool_size"] = new_pool_size
            recommendations["reasoning"].append(
                f"Decrease pool size due to low utilization ({avg_utilization:.2%})"
            )

        # 체크아웃 시간 기반 권장사항
        if max_checkout_time > 30:
            recommendations["recommended_config"]["pool_timeout"] = min(
                self.config.pool_timeout + 60, 600
            )
            recommendations["reasoning"].append(
                f"Increase timeout due to long checkout times ({max_checkout_time:.2f}s)"
            )

        return recommendations


# 전역 연결 풀 관리자 (엔진 설정 후 초기화)
_pool_manager: Optional[ConnectionPoolManager] = None


def initialize_pool_manager(
    engine: Engine, config: Optional[ConnectionPoolConfig] = None
):
    """연결 풀 관리자 초기화"""
    global _pool_manager
    _pool_manager = ConnectionPoolManager(engine, config)
    logger.info("connection_pool_manager_initialized")


def get_pool_manager() -> Optional[ConnectionPoolManager]:
    """연결 풀 관리자 조회"""
    return _pool_manager


async def monitor_connection_pool():
    """연결 풀 모니터링 (주기적 실행용)"""
    if _pool_manager:
        return await _pool_manager.check_and_adjust_pool()
    return {"status": "not_initialized"}
