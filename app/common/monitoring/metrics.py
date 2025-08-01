"""
Prometheus 메트릭 수집 시스템

이 모듈은 애플리케이션의 다양한 메트릭을 수집하고 Prometheus 형태로 노출합니다.
"""

from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server
import time
import psutil
import threading
from typing import Dict, Any, Optional
from datetime import datetime
from functools import wraps

from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """메트릭 수집 및 관리 클래스"""

    def __init__(self):
        self._setup_metrics()
        self._system_info_updated = False

    def _setup_metrics(self):
        """Prometheus 메트릭 정의"""

        # 애플리케이션 정보
        self.app_info = Info("finstage_app_info", "Application information")

        # 뉴스 크롤링 메트릭
        self.news_processed_total = Counter(
            "finstage_news_processed_total",
            "Total number of news articles processed",
            ["source", "symbol", "status"],
        )

        self.news_processing_duration = Histogram(
            "finstage_news_processing_duration_seconds",
            "Time spent processing news articles",
            ["source", "symbol"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
        )

        # 기술적 분석 메트릭
        self.analysis_duration = Histogram(
            "finstage_analysis_duration_seconds",
            "Time spent on technical analysis",
            ["symbol", "strategy"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
        )

        self.signals_generated_total = Counter(
            "finstage_signals_generated_total",
            "Total number of trading signals generated",
            ["symbol", "signal_type", "confidence_level"],
        )

        self.active_signals_gauge = Gauge(
            "finstage_active_signals_total",
            "Number of active trading signals",
            ["signal_type"],
        )

        # 알림 메트릭
        self.notifications_sent_total = Counter(
            "finstage_notifications_sent_total",
            "Total number of notifications sent",
            ["channel", "status"],
        )

        self.notification_duration = Histogram(
            "finstage_notification_duration_seconds",
            "Time spent sending notifications",
            ["channel"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
        )

        # 데이터베이스 메트릭
        self.db_operations_total = Counter(
            "finstage_db_operations_total",
            "Total number of database operations",
            ["operation", "table", "status"],
        )

        self.db_operation_duration = Histogram(
            "finstage_db_operation_duration_seconds",
            "Time spent on database operations",
            ["operation", "table"],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
        )

        self.db_connections_active = Gauge(
            "finstage_db_connections_active", "Number of active database connections"
        )

        # 시스템 메트릭
        self.system_cpu_usage = Gauge(
            "finstage_system_cpu_usage_percent", "System CPU usage percentage"
        )

        self.system_memory_usage = Gauge(
            "finstage_system_memory_usage_bytes", "System memory usage in bytes"
        )

        self.system_disk_usage = Gauge(
            "finstage_system_disk_usage_percent", "System disk usage percentage"
        )

        # HTTP 요청 메트릭
        self.http_requests_total = Counter(
            "finstage_http_requests_total",
            "Total number of HTTP requests",
            ["method", "endpoint", "status_code"],
        )

        self.http_request_duration = Histogram(
            "finstage_http_request_duration_seconds",
            "HTTP request duration",
            ["method", "endpoint"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
        )

        # 에러 메트릭
        self.errors_total = Counter(
            "finstage_errors_total",
            "Total number of errors",
            ["error_type", "component"],
        )

        logger.info("prometheus_metrics_initialized")

    def set_app_info(self, version: str, environment: str, start_time: str):
        """애플리케이션 정보 설정"""
        if not self._system_info_updated:
            self.app_info.info(
                {
                    "version": version,
                    "environment": environment,
                    "start_time": start_time,
                    "python_version": f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}",
                }
            )
            self._system_info_updated = True
            logger.info(
                "app_info_metrics_set", version=version, environment=environment
            )

    def record_news_processing(
        self, source: str, symbol: str, status: str, duration: float
    ):
        """뉴스 처리 메트릭 기록"""
        self.news_processed_total.labels(
            source=source, symbol=symbol, status=status
        ).inc()
        if status == "success":
            self.news_processing_duration.labels(source=source, symbol=symbol).observe(
                duration
            )

    def record_analysis(self, symbol: str, strategy: str, duration: float):
        """기술적 분석 메트릭 기록"""
        self.analysis_duration.labels(symbol=symbol, strategy=strategy).observe(
            duration
        )

    def record_signal_generated(self, symbol: str, signal_type: str, confidence: float):
        """신호 생성 메트릭 기록"""
        confidence_level = self._get_confidence_level(confidence)
        self.signals_generated_total.labels(
            symbol=symbol, signal_type=signal_type, confidence_level=confidence_level
        ).inc()

    def update_active_signals(self, signal_counts: Dict[str, int]):
        """활성 신호 수 업데이트"""
        for signal_type, count in signal_counts.items():
            self.active_signals_gauge.labels(signal_type=signal_type).set(count)

    def record_notification(self, channel: str, status: str, duration: float):
        """알림 전송 메트릭 기록"""
        self.notifications_sent_total.labels(channel=channel, status=status).inc()
        if status == "success":
            self.notification_duration.labels(channel=channel).observe(duration)

    def record_db_operation(
        self, operation: str, table: str, status: str, duration: float
    ):
        """데이터베이스 작업 메트릭 기록"""
        self.db_operations_total.labels(
            operation=operation, table=table, status=status
        ).inc()
        if status == "success":
            self.db_operation_duration.labels(operation=operation, table=table).observe(
                duration
            )

    def update_db_connections(self, active_connections: int):
        """활성 DB 연결 수 업데이트"""
        self.db_connections_active.set(active_connections)

    def record_http_request(
        self, method: str, endpoint: str, status_code: int, duration: float
    ):
        """HTTP 요청 메트릭 기록"""
        self.http_requests_total.labels(
            method=method, endpoint=endpoint, status_code=str(status_code)
        ).inc()
        self.http_request_duration.labels(method=method, endpoint=endpoint).observe(
            duration
        )

    def record_error(self, error_type: str, component: str):
        """에러 메트릭 기록"""
        self.errors_total.labels(error_type=error_type, component=component).inc()

    def update_system_metrics(self):
        """시스템 메트릭 업데이트"""
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            self.system_cpu_usage.set(cpu_percent)

            # 메모리 사용률
            memory = psutil.virtual_memory()
            self.system_memory_usage.set(memory.used)

            # 디스크 사용률
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100
            self.system_disk_usage.set(disk_percent)

        except Exception as e:
            logger.error("system_metrics_update_failed", error=str(e))

    def _get_confidence_level(self, confidence: float) -> str:
        """신뢰도를 레벨로 변환"""
        if confidence >= 0.8:
            return "high"
        elif confidence >= 0.6:
            return "medium"
        else:
            return "low"


# 전역 메트릭 수집기 인스턴스
metrics_collector = MetricsCollector()


def measure_execution_time(metric_name: str = None, component: str = "general"):
    """실행 시간 측정 데코레이터"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            name = metric_name or f"{component}_{func.__name__}"

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # 컴포넌트별로 다른 메트릭에 기록
                if component == "news":
                    # 뉴스 관련 함수는 별도 처리 필요
                    pass
                elif component == "analysis":
                    # 분석 관련 함수는 별도 처리 필요
                    pass
                else:
                    # 일반적인 실행 시간은 로그로만 기록
                    logger.debug(
                        "function_execution_time", function=name, duration=duration
                    )

                return result

            except Exception as e:
                duration = time.time() - start_time
                metrics_collector.record_error(type(e).__name__, component)
                logger.error(
                    "function_execution_failed",
                    function=name,
                    duration=duration,
                    error=str(e),
                )
                raise

        return wrapper

    return decorator


def measure_news_processing(source: str, symbol: str):
    """뉴스 처리 시간 측정 데코레이터"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                metrics_collector.record_news_processing(
                    source, symbol, "success", duration
                )
                return result

            except Exception as e:
                duration = time.time() - start_time
                metrics_collector.record_news_processing(
                    source, symbol, "error", duration
                )
                metrics_collector.record_error(type(e).__name__, "news_processing")
                raise

        return wrapper

    return decorator


def measure_analysis_time(symbol: str, strategy: str):
    """기술적 분석 시간 측정 데코레이터"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                metrics_collector.record_analysis(symbol, strategy, duration)
                return result

            except Exception as e:
                duration = time.time() - start_time
                metrics_collector.record_error(type(e).__name__, "technical_analysis")
                raise

        return wrapper

    return decorator


def measure_db_operation(operation: str, table: str):
    """데이터베이스 작업 시간 측정 데코레이터"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                metrics_collector.record_db_operation(
                    operation, table, "success", duration
                )
                return result

            except Exception as e:
                duration = time.time() - start_time
                metrics_collector.record_db_operation(
                    operation, table, "error", duration
                )
                metrics_collector.record_error(type(e).__name__, "database")
                raise

        return wrapper

    return decorator


class SystemMetricsCollector:
    """시스템 메트릭 주기적 수집"""

    def __init__(self, interval: int = 30):
        self.interval = interval
        self.running = False
        self.thread = None

    def start(self):
        """메트릭 수집 시작"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._collect_loop, daemon=True)
        self.thread.start()
        logger.info("system_metrics_collection_started", interval=self.interval)

    def stop(self):
        """메트릭 수집 중지"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("system_metrics_collection_stopped")

    def _collect_loop(self):
        """메트릭 수집 루프"""
        while self.running:
            try:
                metrics_collector.update_system_metrics()
                time.sleep(self.interval)
            except Exception as e:
                logger.error("system_metrics_collection_error", error=str(e))
                time.sleep(self.interval)


# 전역 시스템 메트릭 수집기
system_metrics_collector = SystemMetricsCollector()


def start_metrics_server(port: int = 8001):
    """Prometheus 메트릭 서버 시작"""
    try:
        start_http_server(port)
        logger.info("prometheus_metrics_server_started", port=port)

        # 시스템 메트릭 수집 시작
        system_metrics_collector.start()

        # 앱 정보 설정
        metrics_collector.set_app_info(
            version="1.0.0",
            environment="production",  # 실제 환경에 맞게 수정
            start_time=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error("prometheus_metrics_server_start_failed", port=port, error=str(e))
        raise


def stop_metrics_server():
    """메트릭 서버 중지"""
    system_metrics_collector.stop()
    logger.info("prometheus_metrics_server_stopped")
