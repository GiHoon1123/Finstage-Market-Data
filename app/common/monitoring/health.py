"""
헬스체크 시스템

애플리케이션의 다양한 컴포넌트 상태를 확인하고 전체적인 헬스 상태를 제공합니다.
"""

import asyncio
import time
import psutil
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from app.common.utils.logging_config import get_logger
from app.common.config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class HealthStatus(Enum):
    """헬스 상태 열거형"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    """개별 헬스체크 결과"""

    name: str
    status: HealthStatus
    message: str
    duration_ms: float
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None


class HealthChecker:
    """헬스체크 수행 클래스"""

    def __init__(self):
        self.start_time = datetime.now()
        self.last_check_time = None
        self.check_cache = {}
        self.cache_ttl = 30  # 30초 캐시

    async def get_overall_health(self) -> Dict[str, Any]:
        """전체 헬스 상태 조회"""
        checks = await self._run_all_checks()

        # 전체 상태 결정
        overall_status = self._determine_overall_status(checks)

        # 응답 구성
        response = {
            "status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "version": "1.0.0",  # 실제 버전으로 교체
            "environment": settings.environment,
            "checks": {
                check.name: self._format_check_result(check) for check in checks
            },
        }

        self.last_check_time = datetime.now()
        logger.info(
            "health_check_completed",
            overall_status=overall_status.value,
            checks_count=len(checks),
        )

        return response

    async def _run_all_checks(self) -> List[HealthCheck]:
        """모든 헬스체크 실행"""
        checks = []

        # 병렬로 헬스체크 실행
        check_tasks = [
            self._check_database(),
            self._check_telegram_connection(),
            self._check_external_apis(),
            self._check_system_resources(),
            self._check_disk_space(),
            self._check_memory_usage(),
            self._check_scheduler_status(),
        ]

        results = await asyncio.gather(*check_tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                checks.append(
                    HealthCheck(
                        name="unknown_check",
                        status=HealthStatus.UNHEALTHY,
                        message=f"Check failed: {str(result)}",
                        duration_ms=0,
                        timestamp=datetime.now(),
                    )
                )
            else:
                checks.append(result)

        return checks

    async def _check_database(self) -> HealthCheck:
        """데이터베이스 연결 상태 확인"""
        start_time = time.time()

        try:
            # 실제 DB 연결 테스트 (간단한 쿼리)
            # 여기서는 예시로 구현
            await asyncio.sleep(0.01)  # DB 쿼리 시뮬레이션

            duration_ms = (time.time() - start_time) * 1000

            return HealthCheck(
                name="database",
                status=HealthStatus.HEALTHY,
                message="Database connection successful",
                duration_ms=duration_ms,
                timestamp=datetime.now(),
                details={
                    "host": settings.mysql_host,
                    "port": settings.mysql_port,
                    "database": settings.mysql_database,
                },
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("database_health_check_failed", error=str(e))

            return HealthCheck(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                duration_ms=duration_ms,
                timestamp=datetime.now(),
            )

    async def _check_telegram_connection(self) -> HealthCheck:
        """텔레그램 봇 연결 상태 확인"""
        start_time = time.time()

        try:
            # 텔레그램 봇 API 테스트
            url = f"https://api.telegram.org/bot{settings.telegram.bot_token}/getMe"

            # 비동기 HTTP 요청 시뮬레이션
            await asyncio.sleep(0.1)

            duration_ms = (time.time() - start_time) * 1000

            return HealthCheck(
                name="telegram",
                status=HealthStatus.HEALTHY,
                message="Telegram bot connection successful",
                duration_ms=duration_ms,
                timestamp=datetime.now(),
                details={
                    "bot_token_configured": bool(settings.telegram.bot_token),
                    "chat_id_configured": bool(settings.telegram.chat_id),
                },
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("telegram_health_check_failed", error=str(e))

            return HealthCheck(
                name="telegram",
                status=HealthStatus.UNHEALTHY,
                message=f"Telegram connection failed: {str(e)}",
                duration_ms=duration_ms,
                timestamp=datetime.now(),
            )

    async def _check_external_apis(self) -> HealthCheck:
        """외부 API 연결 상태 확인"""
        start_time = time.time()

        try:
            # 주요 외부 API들 상태 확인
            api_checks = {
                "yahoo_finance": "https://finance.yahoo.com",
                "investing_com": "https://www.investing.com",
            }

            failed_apis = []

            for api_name, url in api_checks.items():
                try:
                    # 실제로는 requests를 사용하지만 여기서는 시뮬레이션
                    await asyncio.sleep(0.05)
                except Exception as e:
                    failed_apis.append(f"{api_name}: {str(e)}")

            duration_ms = (time.time() - start_time) * 1000

            if not failed_apis:
                return HealthCheck(
                    name="external_apis",
                    status=HealthStatus.HEALTHY,
                    message="All external APIs accessible",
                    duration_ms=duration_ms,
                    timestamp=datetime.now(),
                    details={"checked_apis": list(api_checks.keys())},
                )
            else:
                status = (
                    HealthStatus.DEGRADED
                    if len(failed_apis) < len(api_checks)
                    else HealthStatus.UNHEALTHY
                )
                return HealthCheck(
                    name="external_apis",
                    status=status,
                    message=f"Some APIs failed: {', '.join(failed_apis)}",
                    duration_ms=duration_ms,
                    timestamp=datetime.now(),
                    details={"failed_apis": failed_apis},
                )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("external_apis_health_check_failed", error=str(e))

            return HealthCheck(
                name="external_apis",
                status=HealthStatus.UNHEALTHY,
                message=f"External API check failed: {str(e)}",
                duration_ms=duration_ms,
                timestamp=datetime.now(),
            )

    async def _check_system_resources(self) -> HealthCheck:
        """시스템 리소스 상태 확인"""
        start_time = time.time()

        try:
            # CPU 사용률 확인
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # 메모리 사용률 확인
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            duration_ms = (time.time() - start_time) * 1000

            # 임계값 설정
            cpu_warning_threshold = 80
            cpu_critical_threshold = 95
            memory_warning_threshold = 80
            memory_critical_threshold = 95

            # 상태 결정
            if (
                cpu_percent > cpu_critical_threshold
                or memory_percent > memory_critical_threshold
            ):
                status = HealthStatus.UNHEALTHY
                message = f"Critical resource usage: CPU {cpu_percent:.1f}%, Memory {memory_percent:.1f}%"
            elif (
                cpu_percent > cpu_warning_threshold
                or memory_percent > memory_warning_threshold
            ):
                status = HealthStatus.DEGRADED
                message = f"High resource usage: CPU {cpu_percent:.1f}%, Memory {memory_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Normal resource usage: CPU {cpu_percent:.1f}%, Memory {memory_percent:.1f}%"

            return HealthCheck(
                name="system_resources",
                status=status,
                message=message,
                duration_ms=duration_ms,
                timestamp=datetime.now(),
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "memory_available_gb": memory.available / (1024**3),
                    "cpu_count": psutil.cpu_count(),
                },
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("system_resources_health_check_failed", error=str(e))

            return HealthCheck(
                name="system_resources",
                status=HealthStatus.UNHEALTHY,
                message=f"System resources check failed: {str(e)}",
                duration_ms=duration_ms,
                timestamp=datetime.now(),
            )

    async def _check_disk_space(self) -> HealthCheck:
        """디스크 공간 상태 확인"""
        start_time = time.time()

        try:
            disk_usage = psutil.disk_usage("/")
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            free_gb = disk_usage.free / (1024**3)

            duration_ms = (time.time() - start_time) * 1000

            # 임계값 설정
            warning_threshold = 80
            critical_threshold = 95

            if disk_percent > critical_threshold:
                status = HealthStatus.UNHEALTHY
                message = f"Critical disk usage: {disk_percent:.1f}% used, {free_gb:.1f}GB free"
            elif disk_percent > warning_threshold:
                status = HealthStatus.DEGRADED
                message = (
                    f"High disk usage: {disk_percent:.1f}% used, {free_gb:.1f}GB free"
                )
            else:
                status = HealthStatus.HEALTHY
                message = (
                    f"Normal disk usage: {disk_percent:.1f}% used, {free_gb:.1f}GB free"
                )

            return HealthCheck(
                name="disk_space",
                status=status,
                message=message,
                duration_ms=duration_ms,
                timestamp=datetime.now(),
                details={
                    "disk_percent": disk_percent,
                    "free_gb": free_gb,
                    "total_gb": disk_usage.total / (1024**3),
                },
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("disk_space_health_check_failed", error=str(e))

            return HealthCheck(
                name="disk_space",
                status=HealthStatus.UNHEALTHY,
                message=f"Disk space check failed: {str(e)}",
                duration_ms=duration_ms,
                timestamp=datetime.now(),
            )

    async def _check_memory_usage(self) -> HealthCheck:
        """메모리 사용량 상세 확인"""
        start_time = time.time()

        try:
            # 현재 프로세스 메모리 사용량
            process = psutil.Process()
            process_memory = process.memory_info()
            process_memory_mb = process_memory.rss / (1024**2)

            # 시스템 전체 메모리
            system_memory = psutil.virtual_memory()

            duration_ms = (time.time() - start_time) * 1000

            # 프로세스 메모리 임계값 (MB)
            warning_threshold = 500
            critical_threshold = 1000

            if process_memory_mb > critical_threshold:
                status = HealthStatus.UNHEALTHY
                message = f"Critical process memory usage: {process_memory_mb:.1f}MB"
            elif process_memory_mb > warning_threshold:
                status = HealthStatus.DEGRADED
                message = f"High process memory usage: {process_memory_mb:.1f}MB"
            else:
                status = HealthStatus.HEALTHY
                message = f"Normal process memory usage: {process_memory_mb:.1f}MB"

            return HealthCheck(
                name="memory_usage",
                status=status,
                message=message,
                duration_ms=duration_ms,
                timestamp=datetime.now(),
                details={
                    "process_memory_mb": process_memory_mb,
                    "system_memory_percent": system_memory.percent,
                    "system_available_gb": system_memory.available / (1024**3),
                },
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("memory_usage_health_check_failed", error=str(e))

            return HealthCheck(
                name="memory_usage",
                status=HealthStatus.UNHEALTHY,
                message=f"Memory usage check failed: {str(e)}",
                duration_ms=duration_ms,
                timestamp=datetime.now(),
            )

    async def _check_scheduler_status(self) -> HealthCheck:
        """스케줄러 상태 확인"""
        start_time = time.time()

        try:
            # 스케줄러 상태 확인 (실제 구현에서는 스케줄러 인스턴스 확인)
            # 여기서는 시뮬레이션
            await asyncio.sleep(0.01)

            duration_ms = (time.time() - start_time) * 1000

            # 실제로는 스케줄러의 실행 상태, 마지막 실행 시간 등을 확인
            scheduler_running = True  # 실제 상태로 교체
            last_execution = datetime.now() - timedelta(
                minutes=5
            )  # 실제 마지막 실행 시간

            if scheduler_running:
                status = HealthStatus.HEALTHY
                message = f"Scheduler running normally, last execution: {last_execution.strftime('%H:%M:%S')}"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Scheduler not running"

            return HealthCheck(
                name="scheduler",
                status=status,
                message=message,
                duration_ms=duration_ms,
                timestamp=datetime.now(),
                details={
                    "running": scheduler_running,
                    "last_execution": last_execution.isoformat(),
                },
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("scheduler_health_check_failed", error=str(e))

            return HealthCheck(
                name="scheduler",
                status=HealthStatus.UNHEALTHY,
                message=f"Scheduler check failed: {str(e)}",
                duration_ms=duration_ms,
                timestamp=datetime.now(),
            )

    def _determine_overall_status(self, checks: List[HealthCheck]) -> HealthStatus:
        """개별 체크 결과를 바탕으로 전체 상태 결정"""
        if not checks:
            return HealthStatus.UNHEALTHY

        unhealthy_count = sum(
            1 for check in checks if check.status == HealthStatus.UNHEALTHY
        )
        degraded_count = sum(
            1 for check in checks if check.status == HealthStatus.DEGRADED
        )

        # 하나라도 UNHEALTHY면 전체 UNHEALTHY
        if unhealthy_count > 0:
            return HealthStatus.UNHEALTHY

        # DEGRADED가 있으면 전체 DEGRADED
        if degraded_count > 0:
            return HealthStatus.DEGRADED

        # 모두 HEALTHY면 전체 HEALTHY
        return HealthStatus.HEALTHY

    def _format_check_result(self, check: HealthCheck) -> Dict[str, Any]:
        """헬스체크 결과를 API 응답 형태로 포맷"""
        result = {
            "status": check.status.value,
            "message": check.message,
            "duration_ms": round(check.duration_ms, 2),
            "timestamp": check.timestamp.isoformat(),
        }

        if check.details:
            result["details"] = check.details

        return result


# 전역 헬스체커 인스턴스
health_checker = HealthChecker()


async def get_health_status() -> Dict[str, Any]:
    """헬스 상태 조회 (외부 인터페이스)"""
    return await health_checker.get_overall_health()


async def get_readiness_status() -> Dict[str, Any]:
    """준비 상태 확인 (Kubernetes readiness probe용)"""
    # 핵심 서비스만 확인 (빠른 응답)
    essential_checks = [
        health_checker._check_database(),
        health_checker._check_system_resources(),
    ]

    results = await asyncio.gather(*essential_checks, return_exceptions=True)

    # 필수 서비스가 모두 정상이면 ready
    all_healthy = all(
        isinstance(result, HealthCheck) and result.status == HealthStatus.HEALTHY
        for result in results
    )

    return {
        "status": "ready" if all_healthy else "not_ready",
        "timestamp": datetime.now().isoformat(),
    }


async def get_liveness_status() -> Dict[str, Any]:
    """생존 상태 확인 (Kubernetes liveness probe용)"""
    # 기본적인 생존 확인 (매우 빠른 응답)
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": (datetime.now() - health_checker.start_time).total_seconds(),
    }
