"""
모니터링 관련 API 라우트

헬스체크, 메트릭, 상태 확인 등의 엔드포인트를 제공합니다.
"""

import re
import sys
import time
import platform
import psutil
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.common.monitoring.health import (
    get_health_status,
    get_readiness_status,
    get_liveness_status,
)
from app.common.monitoring.metrics import metrics_collector
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)

# 모니터링 라우터 생성
monitoring_router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@monitoring_router.get("/health", summary="전체 헬스체크")
async def health_check() -> Dict[str, Any]:
    """
    애플리케이션의 전체 헬스 상태를 확인합니다.

    모든 컴포넌트(데이터베이스, 외부 API, 시스템 리소스 등)의 상태를 종합적으로 점검합니다.
    """
    try:
        start_time = time.time()
        health_status = await get_health_status()
        duration = time.time() - start_time

        # 메트릭 기록
        status_code = 200 if health_status["status"] == "healthy" else 503
        metrics_collector.record_http_request(
            "GET", "/monitoring/health", status_code, duration
        )

        logger.info(
            "health_check_requested", status=health_status["status"], duration=duration
        )

        if health_status["status"] != "healthy":
            raise HTTPException(status_code=503, detail=health_status)

        return health_status

    except HTTPException:
        raise
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        metrics_collector.record_error(type(e).__name__, "health_check")
        raise HTTPException(status_code=500, detail="Health check failed")


@monitoring_router.get("/health/ready", summary="준비 상태 확인")
async def readiness_check() -> Dict[str, Any]:
    """
    애플리케이션의 준비 상태를 확인합니다.

    Kubernetes readiness probe에서 사용됩니다.
    핵심 서비스만 빠르게 확인하여 트래픽을 받을 준비가 되었는지 판단합니다.
    """
    try:
        start_time = time.time()
        readiness_status = await get_readiness_status()
        duration = time.time() - start_time

        status_code = 200 if readiness_status["status"] == "ready" else 503
        metrics_collector.record_http_request(
            "GET", "/monitoring/health/ready", status_code, duration
        )

        if readiness_status["status"] != "ready":
            raise HTTPException(status_code=503, detail=readiness_status)

        return readiness_status

    except HTTPException:
        raise
    except Exception as e:
        logger.error("readiness_check_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Readiness check failed")


@monitoring_router.get("/health/live", summary="생존 상태 확인")
async def liveness_check() -> Dict[str, Any]:
    """
    애플리케이션의 생존 상태를 확인합니다.

    Kubernetes liveness probe에서 사용됩니다.
    애플리케이션이 살아있는지만 확인하는 가장 기본적인 체크입니다.
    """
    try:
        start_time = time.time()
        liveness_status = await get_liveness_status()
        duration = time.time() - start_time

        metrics_collector.record_http_request(
            "GET", "/monitoring/health/live", 200, duration
        )

        return liveness_status

    except Exception as e:
        logger.error("liveness_check_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Liveness check failed")


@monitoring_router.get(
    "/metrics", response_class=PlainTextResponse, summary="Prometheus 메트릭"
)
async def get_metrics() -> str:
    """
    Prometheus 형태의 메트릭을 반환합니다.

    Prometheus 서버에서 스크래핑할 수 있는 형태로 모든 메트릭을 제공합니다.
    """
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

        start_time = time.time()
        metrics_data = generate_latest()
        duration = time.time() - start_time

        metrics_collector.record_http_request(
            "GET", "/monitoring/metrics", 200, duration
        )

        return metrics_data.decode("utf-8")

    except Exception as e:
        logger.error("metrics_endpoint_failed", error=str(e))
        metrics_collector.record_error(type(e).__name__, "metrics_endpoint")
        raise HTTPException(status_code=500, detail="Metrics generation failed")


@monitoring_router.get("/status", summary="간단한 상태 확인")
async def get_status() -> Dict[str, Any]:
    """
    애플리케이션의 기본 상태 정보를 반환합니다.

    빠른 상태 확인용으로 사용됩니다.
    """
    try:
        from datetime import datetime
        import psutil

        start_time = time.time()

        # 기본 상태 정보
        status_info = {
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",  # 실제 버전으로 교체
            "environment": "production",  # 실제 환경으로 교체
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": (
                    psutil.disk_usage("/").used / psutil.disk_usage("/").total
                )
                * 100,
            },
        }

        duration = time.time() - start_time
        metrics_collector.record_http_request(
            "GET", "/monitoring/status", 200, duration
        )

        return status_info

    except Exception as e:
        logger.error("status_endpoint_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Status check failed")


@monitoring_router.get("/info", summary="애플리케이션 정보")
async def get_app_info() -> Dict[str, Any]:
    """
    애플리케이션의 상세 정보를 반환합니다.
    """
    try:
        import sys
        import platform
        from datetime import datetime

        start_time = time.time()

        app_info = {
            "application": {
                "name": "Finstage Market Data Backend",
                "version": "1.0.0",
                "description": "Financial market data collection and analysis system",
                "environment": "production",  # 실제 환경으로 교체
            },
            "system": {
                "platform": platform.platform(),
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "architecture": platform.architecture()[0],
                "hostname": platform.node(),
            },
            "runtime": {
                "timestamp": datetime.now().isoformat(),
                "timezone": str(datetime.now().astimezone().tzinfo),
            },
        }

        duration = time.time() - start_time
        metrics_collector.record_http_request("GET", "/monitoring/info", 200, duration)

        return app_info

    except Exception as e:
        logger.error("app_info_endpoint_failed", error=str(e))
        raise HTTPException(status_code=500, detail="App info retrieval failed")


# HTTP 요청 메트릭 수집 미들웨어
async def metrics_middleware(request: Request, call_next):
    """HTTP 요청 메트릭을 자동으로 수집하는 미들웨어"""
    start_time = time.time()

    # 요청 처리
    response = await call_next(request)

    # 메트릭 기록
    duration = time.time() - start_time
    method = request.method
    path = request.url.path
    status_code = response.status_code

    # 경로 정규화 (파라미터 제거)
    normalized_path = _normalize_path(path)

    metrics_collector.record_http_request(
        method, normalized_path, status_code, duration
    )

    return response


def _normalize_path(path: str) -> str:
    """경로를 정규화하여 메트릭 카디널리티 제한"""
    # 동적 경로 파라미터를 플레이스홀더로 교체
    import re

    # UUID 패턴 교체
    path = re.sub(
        r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "/{uuid}",
        path,
    )

    # 숫자 ID 패턴 교체
    path = re.sub(r"/\d+", "/{id}", path)

    # 심볼 패턴 교체 (대문자 3-5자)
    path = re.sub(r"/[A-Z]{3,5}$", "/{symbol}", path)

    return path
