"""
성능 메트릭 수집 시스템

최적화 전후 성능 비교 측정 및 메모리 사용량, 응답 시간, 처리량을 자동 수집하는 시스템
"""

import time
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import asyncio
import functools
import json

from app.common.utils.logging_config import get_logger
from app.common.utils.memory_optimizer import memory_monitor

logger = get_logger(__name__)


@dataclass
class PerformanceMetric:
    """성능 메트릭 데이터 클래스"""

    timestamp: str
    metric_type: str
    metric_name: str
    value: float
    unit: str
    tags: Dict[str, str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResponseTimeMetric:
    """응답 시간 메트릭"""

    function_name: str
    start_time: float
    end_time: float
    duration: float
    success: bool
    error: str = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryMetric:
    """메모리 사용량 메트릭"""

    timestamp: str
    process_memory_mb: float
    system_memory_percent: float
    available_memory_mb: float
    memory_diff_mb: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ThroughputMetric:
    """처리량 메트릭"""

    timestamp: str
    operation_name: str
    count: int
    duration_seconds: float
    throughput_per_second: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PerformanceMetricsCollector:
    """성능 메트릭 수집기"""

    def __init__(self, max_metrics: int = 10000):
        self.max_metrics = max_metrics
        self.metrics: deque = deque(maxlen=max_metrics)
        self.response_times: deque = deque(maxlen=max_metrics)
        self.memory_metrics: deque = deque(maxlen=max_metrics)
        self.throughput_metrics: deque = deque(maxlen=max_metrics)

        # 실시간 통계
        self.function_stats = defaultdict(list)
        self.memory_baseline = None
        self.collection_start_time = time.time()

        # 수집 활성화 플래그
        self.enabled = True

        # 백그라운드 수집 스레드
        self._collection_thread = None
        self._stop_collection = threading.Event()

        logger.info(
            "performance_metrics_collector_initialized", max_metrics=max_metrics
        )

    def start_background_collection(self, interval_seconds: int = 30):
        """백그라운드 메트릭 수집 시작"""
        if self._collection_thread and self._collection_thread.is_alive():
            return

        self._stop_collection.clear()
        self._collection_thread = threading.Thread(
            target=self._background_collection_loop,
            args=(interval_seconds,),
            daemon=True,
        )
        self._collection_thread.start()

        logger.info(
            "background_metrics_collection_started", interval_seconds=interval_seconds
        )

    def stop_background_collection(self):
        """백그라운드 메트릭 수집 중지"""
        if self._collection_thread:
            self._stop_collection.set()
            self._collection_thread.join(timeout=5)

        logger.info("background_metrics_collection_stopped")

    def _background_collection_loop(self, interval_seconds: int):
        """백그라운드 수집 루프"""
        while not self._stop_collection.wait(interval_seconds):
            try:
                self.collect_system_metrics()
            except Exception as e:
                logger.error("background_metrics_collection_failed", error=str(e))

    def collect_system_metrics(self):
        """시스템 메트릭 수집"""
        if not self.enabled:
            return

        try:
            # 메모리 메트릭
            process = psutil.Process()
            memory_info = process.memory_info()
            system_memory = psutil.virtual_memory()

            memory_metric = MemoryMetric(
                timestamp=datetime.now().isoformat(),
                process_memory_mb=memory_info.rss / 1024 / 1024,
                system_memory_percent=system_memory.percent,
                available_memory_mb=system_memory.available / 1024 / 1024,
            )

            # 메모리 베이스라인 설정
            if self.memory_baseline is None:
                self.memory_baseline = memory_metric.process_memory_mb
            else:
                memory_metric.memory_diff_mb = (
                    memory_metric.process_memory_mb - self.memory_baseline
                )

            self.memory_metrics.append(memory_metric)

            # CPU 메트릭
            cpu_percent = process.cpu_percent()
            self.add_metric(
                metric_type="system",
                metric_name="cpu_usage",
                value=cpu_percent,
                unit="percent",
            )

            # 스레드 수
            thread_count = process.num_threads()
            self.add_metric(
                metric_type="system",
                metric_name="thread_count",
                value=thread_count,
                unit="count",
            )

        except Exception as e:
            logger.error("system_metrics_collection_failed", error=str(e))

    def add_metric(
        self,
        metric_type: str,
        metric_name: str,
        value: float,
        unit: str,
        tags: Dict[str, str] = None,
    ):
        """메트릭 추가"""
        if not self.enabled:
            return

        metric = PerformanceMetric(
            timestamp=datetime.now().isoformat(),
            metric_type=metric_type,
            metric_name=metric_name,
            value=value,
            unit=unit,
            tags=tags or {},
        )

        self.metrics.append(metric)

    def record_response_time(
        self,
        function_name: str,
        duration: float,
        success: bool = True,
        error: str = None,
    ):
        """응답 시간 기록"""
        if not self.enabled:
            return

        response_metric = ResponseTimeMetric(
            function_name=function_name,
            start_time=time.time() - duration,
            end_time=time.time(),
            duration=duration,
            success=success,
            error=error,
        )

        self.response_times.append(response_metric)
        self.function_stats[function_name].append(duration)

        # 최근 100개만 유지
        if len(self.function_stats[function_name]) > 100:
            self.function_stats[function_name] = self.function_stats[function_name][
                -100:
            ]

    def record_throughput(
        self, operation_name: str, count: int, duration_seconds: float
    ):
        """처리량 기록"""
        if not self.enabled:
            return

        throughput = count / duration_seconds if duration_seconds > 0 else 0

        throughput_metric = ThroughputMetric(
            timestamp=datetime.now().isoformat(),
            operation_name=operation_name,
            count=count,
            duration_seconds=duration_seconds,
            throughput_per_second=throughput,
        )

        self.throughput_metrics.append(throughput_metric)

    def get_statistics(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """통계 조회"""
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
        cutoff_timestamp = cutoff_time.isoformat()

        # 응답 시간 통계
        recent_response_times = [
            rt for rt in self.response_times if rt.start_time >= cutoff_time.timestamp()
        ]

        response_stats = {}
        if recent_response_times:
            durations = [rt.duration for rt in recent_response_times]
            response_stats = {
                "count": len(durations),
                "avg_duration": sum(durations) / len(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "success_rate": sum(1 for rt in recent_response_times if rt.success)
                / len(recent_response_times)
                * 100,
            }

        # 메모리 통계
        recent_memory = [
            m for m in self.memory_metrics if m.timestamp >= cutoff_timestamp
        ]

        memory_stats = {}
        if recent_memory:
            memory_values = [m.process_memory_mb for m in recent_memory]
            memory_stats = {
                "current_memory_mb": memory_values[-1] if memory_values else 0,
                "avg_memory_mb": sum(memory_values) / len(memory_values),
                "min_memory_mb": min(memory_values),
                "max_memory_mb": max(memory_values),
                "memory_growth_mb": (
                    memory_values[-1] - memory_values[0]
                    if len(memory_values) > 1
                    else 0
                ),
            }

        # 처리량 통계
        recent_throughput = [
            t for t in self.throughput_metrics if t.timestamp >= cutoff_timestamp
        ]

        throughput_stats = {}
        if recent_throughput:
            throughput_values = [t.throughput_per_second for t in recent_throughput]
            throughput_stats = {
                "avg_throughput": sum(throughput_values) / len(throughput_values),
                "max_throughput": max(throughput_values),
                "total_operations": sum(t.count for t in recent_throughput),
            }

        return {
            "time_window_minutes": time_window_minutes,
            "collection_duration_hours": (time.time() - self.collection_start_time)
            / 3600,
            "response_time": response_stats,
            "memory": memory_stats,
            "throughput": throughput_stats,
            "total_metrics_collected": len(self.metrics),
            "generated_at": datetime.now().isoformat(),
        }

    def get_function_performance(self, function_name: str = None) -> Dict[str, Any]:
        """함수별 성능 통계"""
        if function_name:
            if function_name not in self.function_stats:
                return {"error": f"No data for function {function_name}"}

            durations = self.function_stats[function_name]
            return {
                "function_name": function_name,
                "call_count": len(durations),
                "avg_duration": sum(durations) / len(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "recent_calls": durations[-10:],  # 최근 10개 호출
            }
        else:
            # 모든 함수 통계
            all_stats = {}
            for func_name, durations in self.function_stats.items():
                all_stats[func_name] = {
                    "call_count": len(durations),
                    "avg_duration": sum(durations) / len(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                }

            return all_stats

    def export_metrics(self, format: str = "json") -> str:
        """메트릭 데이터 내보내기"""
        data = {
            "collection_info": {
                "start_time": datetime.fromtimestamp(
                    self.collection_start_time
                ).isoformat(),
                "export_time": datetime.now().isoformat(),
                "total_metrics": len(self.metrics),
            },
            "metrics": [m.to_dict() for m in self.metrics],
            "response_times": [rt.to_dict() for rt in self.response_times],
            "memory_metrics": [mm.to_dict() for mm in self.memory_metrics],
            "throughput_metrics": [tm.to_dict() for tm in self.throughput_metrics],
        }

        if format.lower() == "json":
            return json.dumps(data, indent=2)
        else:
            return str(data)

    def clear_metrics(self):
        """메트릭 데이터 초기화"""
        self.metrics.clear()
        self.response_times.clear()
        self.memory_metrics.clear()
        self.throughput_metrics.clear()
        self.function_stats.clear()
        self.memory_baseline = None
        self.collection_start_time = time.time()

        logger.info("performance_metrics_cleared")


# 전역 메트릭 수집기 인스턴스
_global_collector = PerformanceMetricsCollector()


def get_metrics_collector() -> PerformanceMetricsCollector:
    """전역 메트릭 수집기 반환"""
    return _global_collector


def performance_monitor(
    metric_name: str = None,
    collect_memory: bool = True,
    collect_throughput: bool = False,
):
    """성능 모니터링 데코레이터"""

    def decorator(func: Callable):
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            func_name = metric_name or f"{func.__module__}.{func.__name__}"

            # 메모리 측정 시작
            memory_before = None
            if collect_memory:
                try:
                    process = psutil.Process()
                    memory_before = process.memory_info().rss / 1024 / 1024
                except:
                    pass

            start_time = time.time()
            success = True
            error = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                end_time = time.time()
                duration = end_time - start_time

                # 응답 시간 기록
                collector.record_response_time(func_name, duration, success, error)

                # 메모리 사용량 기록
                if collect_memory and memory_before is not None:
                    try:
                        process = psutil.Process()
                        memory_after = process.memory_info().rss / 1024 / 1024
                        memory_diff = memory_after - memory_before

                        collector.add_metric(
                            metric_type="memory",
                            metric_name=f"{func_name}_memory_usage",
                            value=memory_diff,
                            unit="MB",
                        )
                    except:
                        pass

                # 처리량 기록 (단일 작업으로 가정)
                if collect_throughput:
                    collector.record_throughput(func_name, 1, duration)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            func_name = metric_name or f"{func.__module__}.{func.__name__}"

            # 메모리 측정 시작
            memory_before = None
            if collect_memory:
                try:
                    process = psutil.Process()
                    memory_before = process.memory_info().rss / 1024 / 1024
                except:
                    pass

            start_time = time.time()
            success = True
            error = None

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                end_time = time.time()
                duration = end_time - start_time

                # 응답 시간 기록
                collector.record_response_time(func_name, duration, success, error)

                # 메모리 사용량 기록
                if collect_memory and memory_before is not None:
                    try:
                        process = psutil.Process()
                        memory_after = process.memory_info().rss / 1024 / 1024
                        memory_diff = memory_after - memory_before

                        collector.add_metric(
                            metric_type="memory",
                            metric_name=f"{func_name}_memory_usage",
                            value=memory_diff,
                            unit="MB",
                        )
                    except:
                        pass

                # 처리량 기록
                if collect_throughput:
                    collector.record_throughput(func_name, 1, duration)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def batch_performance_monitor(operation_name: str):
    """배치 작업 성능 모니터링 데코레이터"""

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            collector = get_metrics_collector()

            start_time = time.time()
            success = True
            error = None
            count = 0

            try:
                result = func(*args, **kwargs)

                # 결과에서 처리된 항목 수 추출
                if isinstance(result, dict):
                    count = result.get("processed_count", result.get("total_count", 1))
                elif isinstance(result, (list, tuple)):
                    count = len(result)
                else:
                    count = 1

                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                end_time = time.time()
                duration = end_time - start_time

                # 응답 시간 기록
                collector.record_response_time(operation_name, duration, success, error)

                # 처리량 기록
                if count > 0:
                    collector.record_throughput(operation_name, count, duration)

        return wrapper

    return decorator


# 메트릭 수집 시작
def start_metrics_collection():
    """메트릭 수집 시작"""
    collector = get_metrics_collector()
    collector.start_background_collection()
    logger.info("global_metrics_collection_started")


def stop_metrics_collection():
    """메트릭 수집 중지"""
    collector = get_metrics_collector()
    collector.stop_background_collection()
    logger.info("global_metrics_collection_stopped")


# 애플리케이션 시작 시 자동으로 메트릭 수집 시작
start_metrics_collection()
