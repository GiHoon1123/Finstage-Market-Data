"""
성능 모니터링 시스템

애플리케이션의 성능 지표를 수집, 기록, 분석하는 도구
"""

import time
import logging
import threading
import functools
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from functools import wraps
from contextlib import contextmanager

# psutil 패키지 import - 이미 설치되어 있음
import psutil

# 로거 설정
logger = logging.getLogger("performance_monitor")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class PerformanceMetrics:
    """성능 지표 수집 및 관리"""

    def __init__(self):
        self.metrics = {}
        self.lock = threading.RLock()

    def record_execution_time(self, name: str, duration: float):
        """
        실행 시간 기록

        Args:
            name: 측정 이름
            duration: 실행 시간 (초)
        """
        with self.lock:
            if name not in self.metrics:
                self.metrics[name] = {
                    "count": 0,
                    "total_time": 0,
                    "min_time": float("inf"),
                    "max_time": 0,
                    "avg_time": 0,
                    "last_time": 0,
                    "timestamps": [],
                }

            metrics = self.metrics[name]
            metrics["count"] += 1
            metrics["total_time"] += duration
            metrics["min_time"] = min(metrics["min_time"], duration)
            metrics["max_time"] = max(metrics["max_time"], duration)
            metrics["avg_time"] = metrics["total_time"] / metrics["count"]
            metrics["last_time"] = duration

            # 최근 10개 타임스탬프만 유지
            timestamp = datetime.now().isoformat()
            metrics["timestamps"].append((timestamp, duration))
            if len(metrics["timestamps"]) > 10:
                metrics["timestamps"] = metrics["timestamps"][-10:]

    def record_resource_usage(self, name: str, cpu_percent: float, memory_mb: float):
        """
        리소스 사용량 기록

        Args:
            name: 측정 이름
            cpu_percent: CPU 사용률 (%)
            memory_mb: 메모리 사용량 (MB)
        """
        with self.lock:
            if name not in self.metrics:
                self.metrics[name] = {"cpu_usage": [], "memory_usage": []}

            metrics = self.metrics[name]
            timestamp = datetime.now().isoformat()

            # 최근 10개 측정값만 유지
            metrics["cpu_usage"].append((timestamp, cpu_percent))
            if len(metrics["cpu_usage"]) > 10:
                metrics["cpu_usage"] = metrics["cpu_usage"][-10:]

            metrics["memory_usage"].append((timestamp, memory_mb))
            if len(metrics["memory_usage"]) > 10:
                metrics["memory_usage"] = metrics["memory_usage"][-10:]

    def get_metrics(self, name: Optional[str] = None) -> Dict:
        """
        수집된 지표 조회

        Args:
            name: 특정 이름의 지표만 조회 (None이면 전체)

        Returns:
            지표 데이터
        """
        with self.lock:
            if name:
                return self.metrics.get(name, {})
            return self.metrics

    def reset_metrics(self, name: Optional[str] = None):
        """
        지표 초기화

        Args:
            name: 특정 이름의 지표만 초기화 (None이면 전체)
        """
        with self.lock:
            if name:
                if name in self.metrics:
                    del self.metrics[name]
            else:
                self.metrics.clear()


# 전역 성능 지표 인스턴스
performance_metrics = PerformanceMetrics()


def measure_time(name: str = None):
    """
    함수 실행 시간 측정 데코레이터

    Args:
        name: 측정 이름 (None이면 함수명 사용)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            metric_name = name or func.__name__
            start_time = time.time()

            try:
                return func(*args, **kwargs)
            finally:
                end_time = time.time()
                duration = end_time - start_time
                performance_metrics.record_execution_time(metric_name, duration)
                logger.debug(f"⏱️ {metric_name}: {duration:.4f}초")

        return wrapper

    return decorator


@contextmanager
def time_block(name: str):
    """
    코드 블록 실행 시간 측정 컨텍스트 매니저

    Args:
        name: 측정 이름

    사용 예:
    with time_block("데이터베이스 쿼리"):
        # 시간을 측정할 코드
    """
    start_time = time.time()
    try:
        yield
    finally:
        end_time = time.time()
        duration = end_time - start_time
        performance_metrics.record_execution_time(name, duration)
        logger.debug(f"⏱️ {name}: {duration:.4f}초")


class ResourceMonitor:
    """시스템 리소스 모니터링"""

    def __init__(self, interval: int = 60):
        """
        Args:
            interval: 측정 간격 (초)
        """
        self.interval = interval
        self.running = False
        self.thread = None

    def _monitor_resources(self):
        """리소스 모니터링 스레드"""
        while self.running:
            try:
                # CPU 사용률
                cpu_percent = psutil.cpu_percent(interval=1)

                # 메모리 사용량
                memory = psutil.Process().memory_info()
                memory_mb = memory.rss / (1024 * 1024)  # MB 단위

                # 지표 기록
                performance_metrics.record_resource_usage(
                    "system", cpu_percent, memory_mb
                )

                logger.debug(f"🖥️ CPU: {cpu_percent:.1f}%, 메모리: {memory_mb:.1f}MB")

                # 다음 측정까지 대기
                time.sleep(self.interval - 1)  # CPU 측정에 1초 사용했으므로 차감

            except Exception as e:
                logger.error(f"리소스 모니터링 오류: {e}")
                time.sleep(self.interval)

    def start(self):
        """모니터링 시작"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self.thread.start()
        logger.info("리소스 모니터링 시작")

    def stop(self):
        """모니터링 중지"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None
        logger.info("리소스 모니터링 중지")


# 리소스 모니터 인스턴스
resource_monitor = ResourceMonitor()


def start_monitoring():
    """성능 모니터링 시작"""
    resource_monitor.start()
    logger.info("성능 모니터링 시스템 시작")


def stop_monitoring():
    """성능 모니터링 중지"""
    resource_monitor.stop()
    logger.info("성능 모니터링 시스템 중지")


def get_performance_report() -> Dict:
    """
    성능 보고서 생성

    Returns:
        성능 지표 보고서
    """
    metrics = performance_metrics.get_metrics()

    # 실행 시간 기준 상위 5개 함수
    time_metrics = {}
    for name, data in metrics.items():
        if "avg_time" in data:
            time_metrics[name] = data["avg_time"]

    top_functions = sorted(time_metrics.items(), key=lambda x: x[1], reverse=True)[:5]

    # 시스템 리소스 사용량
    system_metrics = metrics.get("system", {})

    report = {
        "timestamp": datetime.now().isoformat(),
        "top_functions": [
            {"name": name, "avg_time": time} for name, time in top_functions
        ],
        "system_resources": {
            "cpu_usage": system_metrics.get("cpu_usage", []),
            "memory_usage": system_metrics.get("memory_usage", []),
        },
    }

    return report
