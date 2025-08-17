"""
데이터베이스 쿼리 모니터링 시스템

이 모듈은 SQLAlchemy 쿼리의 성능을 모니터링하고 슬로우 쿼리를 감지합니다.
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import re

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

from app.common.utils.logging_config import get_logger
from app.common.monitoring.metrics import metrics_collector
from app.common.monitoring.alerts import send_warning_alert, send_critical_alert
from app.common.infra.database.services.slow_query_service import slow_query_service

logger = get_logger(__name__)


@dataclass
class QueryMetrics:
    """쿼리 메트릭 데이터 구조"""

    query_hash: str
    query_template: str
    execution_count: int
    total_duration: float
    avg_duration: float
    min_duration: float
    max_duration: float
    last_execution: datetime
    slow_query_count: int
    affected_rows: int
    table_names: List[str]


@dataclass
class SlowQuery:
    """슬로우 쿼리 데이터 구조"""

    query_hash: str
    query: str
    duration: float
    timestamp: datetime
    parameters: Optional[Dict] = None
    stack_trace: Optional[str] = None
    affected_rows: int = 0


class QueryMonitor:
    """데이터베이스 쿼리 모니터링 클래스"""

    def __init__(self, slow_query_threshold: float = 1.0):
        self.slow_query_threshold = slow_query_threshold
        self.query_metrics: Dict[str, QueryMetrics] = {}
        self.slow_queries: deque = deque(maxlen=1000)  # 최근 1000개 슬로우 쿼리 보관
        self.connection_metrics = {
            "active_connections": 0,
            "total_connections": 0,
            "failed_connections": 0,
            "connection_errors": [],
        }
        self._lock = threading.Lock()

        # 쿼리 패턴 정규화를 위한 정규식
        self.normalization_patterns = [
            (re.compile(r"\b\d+\b"), "?"),  # 숫자를 ?로 치환
            (re.compile(r"'[^']*'"), "?"),  # 문자열을 ?로 치환
            (re.compile(r'"[^"]*"'), "?"),  # 문자열을 ?로 치환
            (re.compile(r"\s+"), " "),  # 연속 공백을 하나로
        ]

    def setup_monitoring(self, engine: Engine):
        """SQLAlchemy 엔진에 모니터링 이벤트 리스너 등록"""

        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            """쿼리 실행 전 이벤트"""
            context._query_start_time = time.time()
            context._query_statement = statement
            context._query_parameters = parameters

        @event.listens_for(engine, "after_cursor_execute")
        def after_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            """쿼리 실행 후 이벤트"""
            if not hasattr(context, "_query_start_time"):
                return

            duration = time.time() - context._query_start_time
            affected_rows = cursor.rowcount if hasattr(cursor, "rowcount") else 0

            # 쿼리 정규화 및 메트릭 기록
            self._record_query_metrics(statement, duration, affected_rows, parameters)

            # 슬로우 쿼리 감지
            if duration > self.slow_query_threshold:
                # 비동기 함수를 동기적으로 실행
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 이미 실행 중인 루프가 있으면 백그라운드 태스크로 실행
                        asyncio.create_task(self._handle_slow_query(statement, duration, parameters, affected_rows))
                    else:
                        # 루프가 없으면 새로 실행
                        loop.run_until_complete(self._handle_slow_query(statement, duration, parameters, affected_rows))
                except RuntimeError:
                    # 루프가 없는 경우 새로 생성
                    asyncio.run(self._handle_slow_query(statement, duration, parameters, affected_rows))

            # Prometheus 메트릭 기록
            table_name = self._extract_table_name(statement)
            operation = self._extract_operation(statement)
            status = "success"

            metrics_collector.record_db_operation(
                operation, table_name, status, duration
            )

        @event.listens_for(engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """데이터베이스 연결 시 이벤트"""
            with self._lock:
                self.connection_metrics["active_connections"] += 1
                self.connection_metrics["total_connections"] += 1

            logger.debug(
                "database_connection_established",
                active_connections=self.connection_metrics["active_connections"],
            )

        @event.listens_for(engine, "close")
        def on_close(dbapi_connection, connection_record):
            """데이터베이스 연결 종료 시 이벤트"""
            with self._lock:
                self.connection_metrics["active_connections"] -= 1

            logger.debug(
                "database_connection_closed",
                active_connections=self.connection_metrics["active_connections"],
            )

        @event.listens_for(Pool, "connect")
        def on_pool_connect(dbapi_connection, connection_record):
            """연결 풀 연결 시 이벤트"""
            logger.debug("connection_pool_connect")

        @event.listens_for(Pool, "checkout")
        def on_pool_checkout(dbapi_connection, connection_record, connection_proxy):
            """연결 풀에서 연결 체크아웃 시 이벤트"""
            logger.debug("connection_pool_checkout")

        @event.listens_for(Pool, "checkin")
        def on_pool_checkin(dbapi_connection, connection_record):
            """연결 풀에 연결 체크인 시 이벤트"""
            logger.debug("connection_pool_checkin")

        logger.info(
            "database_query_monitoring_enabled",
            slow_query_threshold=self.slow_query_threshold,
        )

    def _normalize_query(self, query: str) -> str:
        """쿼리를 정규화하여 패턴 추출"""
        normalized = query.strip().upper()

        for pattern, replacement in self.normalization_patterns:
            normalized = pattern.sub(replacement, normalized)

        return normalized

    def _generate_query_hash(self, query: str) -> str:
        """쿼리 해시 생성"""
        import hashlib

        normalized = self._normalize_query(query)
        return hashlib.md5(normalized.encode()).hexdigest()[:12]

    def _extract_table_name(self, query: str) -> str:
        """쿼리에서 테이블명 추출"""
        query_upper = query.upper().strip()

        # FROM 절에서 테이블명 추출
        from_match = re.search(r'FROM\s+([`"]?)(\w+)\1', query_upper)
        if from_match:
            return from_match.group(2).lower()

        # INSERT INTO에서 테이블명 추출
        insert_match = re.search(r'INSERT\s+INTO\s+([`"]?)(\w+)\1', query_upper)
        if insert_match:
            return insert_match.group(2).lower()

        # UPDATE에서 테이블명 추출
        update_match = re.search(r'UPDATE\s+([`"]?)(\w+)\1', query_upper)
        if update_match:
            return update_match.group(2).lower()

        # DELETE FROM에서 테이블명 추출
        delete_match = re.search(r'DELETE\s+FROM\s+([`"]?)(\w+)\1', query_upper)
        if delete_match:
            return delete_match.group(2).lower()

        return "unknown"

    def _extract_operation(self, query: str) -> str:
        """쿼리에서 작업 유형 추출"""
        query_upper = query.upper().strip()

        if query_upper.startswith("SELECT"):
            return "select"
        elif query_upper.startswith("INSERT"):
            return "insert"
        elif query_upper.startswith("UPDATE"):
            return "update"
        elif query_upper.startswith("DELETE"):
            return "delete"
        elif query_upper.startswith("CREATE"):
            return "create"
        elif query_upper.startswith("DROP"):
            return "drop"
        elif query_upper.startswith("ALTER"):
            return "alter"
        else:
            return "other"

    def _extract_table_names(self, query: str) -> List[str]:
        """쿼리에서 모든 테이블명 추출"""
        tables = set()
        query_upper = query.upper()

        # FROM, JOIN, INTO, UPDATE 등에서 테이블명 추출
        patterns = [
            r'FROM\s+([`"]?)(\w+)\1',
            r'JOIN\s+([`"]?)(\w+)\1',
            r'INTO\s+([`"]?)(\w+)\1',
            r'UPDATE\s+([`"]?)(\w+)\1',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, query_upper)
            for match in matches:
                tables.add(match[1].lower())

        return list(tables)

    def _record_query_metrics(
        self,
        query: str,
        duration: float,
        affected_rows: int,
        parameters: Optional[Dict] = None,
    ):
        """쿼리 메트릭 기록"""
        query_hash = self._generate_query_hash(query)
        query_template = self._normalize_query(query)
        table_names = self._extract_table_names(query)

        with self._lock:
            if query_hash in self.query_metrics:
                metrics = self.query_metrics[query_hash]
                metrics.execution_count += 1
                metrics.total_duration += duration
                metrics.avg_duration = metrics.total_duration / metrics.execution_count
                metrics.min_duration = min(metrics.min_duration, duration)
                metrics.max_duration = max(metrics.max_duration, duration)
                metrics.last_execution = datetime.now()
                metrics.affected_rows += affected_rows

                if duration > self.slow_query_threshold:
                    metrics.slow_query_count += 1
            else:
                self.query_metrics[query_hash] = QueryMetrics(
                    query_hash=query_hash,
                    query_template=query_template,
                    execution_count=1,
                    total_duration=duration,
                    avg_duration=duration,
                    min_duration=duration,
                    max_duration=duration,
                    last_execution=datetime.now(),
                    slow_query_count=1 if duration > self.slow_query_threshold else 0,
                    affected_rows=affected_rows,
                    table_names=table_names,
                )

    async def _handle_slow_query(
        self,
        query: str,
        duration: float,
        parameters: Optional[Dict],
        affected_rows: int,
    ):
        """슬로우 쿼리 처리"""
        query_hash = self._generate_query_hash(query)
        query_template = self._normalize_query(query)
        table_names = self._extract_table_names(query)
        operation_type = self._extract_operation(query)
        execution_timestamp = datetime.now()

        # 메모리에 슬로우 쿼리 기록 (기존 방식 유지)
        slow_query = SlowQuery(
            query_hash=query_hash,
            query=query[:1000],  # 쿼리 길이 제한
            duration=duration,
            timestamp=execution_timestamp,
            parameters=parameters,
            affected_rows=affected_rows,
        )

        self.slow_queries.append(slow_query)

        # 데이터베이스에 슬로우 쿼리 저장 (새로운 기능)
        try:
            await slow_query_service.save_slow_query(
                query_hash=query_hash,
                query_template=query_template,
                original_query=query,
                duration=duration,
                affected_rows=affected_rows,
                table_names=table_names,
                operation_type=operation_type,
                execution_timestamp=execution_timestamp,
            )
        except Exception as e:
            logger.error(
                "slow_query_db_save_failed", error=str(e), query_hash=query_hash
            )

        # 로그 기록
        logger.warning(
            "slow_query_detected",
            query_hash=query_hash,
            duration=duration,
            affected_rows=affected_rows,
            query=query[:200],
            saved_to_db=True,
        )

        # 매우 느린 쿼리는 즉시 알림
        if duration > 5.0:  # 5초 이상
            await send_critical_alert(
                title="Critical Slow Query Detected",
                message=f"Query took {duration:.2f} seconds to execute",
                component="database",
                details={
                    "query_hash": query_hash,
                    "duration": duration,
                    "affected_rows": affected_rows,
                    "query_preview": query[:200],
                },
            )
        elif duration > 2.0:  # 2초 이상
            await send_warning_alert(
                title="Slow Query Detected",
                message=f"Query took {duration:.2f} seconds to execute",
                component="database",
                details={
                    "query_hash": query_hash,
                    "duration": duration,
                    "affected_rows": affected_rows,
                },
            )

    def get_query_statistics(self, limit: int = 50) -> List[Dict[str, Any]]:
        """쿼리 통계 조회"""
        with self._lock:
            # 평균 실행 시간 기준으로 정렬
            sorted_metrics = sorted(
                self.query_metrics.values(), key=lambda x: x.avg_duration, reverse=True
            )

            return [asdict(metric) for metric in sorted_metrics[:limit]]

    def get_slow_queries(self, hours: int = 24) -> List[Dict[str, Any]]:
        """슬로우 쿼리 조회 (데이터베이스 우선, 메모리 백업)"""
        try:
            # 먼저 데이터베이스에서 조회 시도
            db_slow_queries = slow_query_service.get_slow_queries(hours=hours)
            if db_slow_queries:
                return db_slow_queries
        except Exception as e:
            logger.error("db_slow_queries_retrieval_failed", error=str(e))

        # 데이터베이스 조회 실패 시 메모리에서 조회 (백업)
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_slow_queries = [
            asdict(sq) for sq in self.slow_queries if sq.timestamp >= cutoff_time
        ]
        return sorted(recent_slow_queries, key=lambda x: x["duration"], reverse=True)

    def get_connection_metrics(self) -> Dict[str, Any]:
        """연결 메트릭 조회"""
        with self._lock:
            return self.connection_metrics.copy()

    def get_performance_summary(self) -> Dict[str, Any]:
        """성능 요약 정보"""
        with self._lock:
            total_queries = sum(m.execution_count for m in self.query_metrics.values())
            total_slow_queries = sum(
                m.slow_query_count for m in self.query_metrics.values()
            )
            avg_query_time = (
                sum(
                    m.avg_duration * m.execution_count
                    for m in self.query_metrics.values()
                )
                / total_queries
                if total_queries > 0
                else 0
            )

            # 가장 느린 쿼리들
            slowest_queries = sorted(
                self.query_metrics.values(), key=lambda x: x.max_duration, reverse=True
            )[:5]

            # 가장 자주 실행되는 쿼리들
            most_frequent_queries = sorted(
                self.query_metrics.values(),
                key=lambda x: x.execution_count,
                reverse=True,
            )[:5]

            return {
                "summary": {
                    "total_queries": total_queries,
                    "unique_query_patterns": len(self.query_metrics),
                    "slow_queries": total_slow_queries,
                    "slow_query_rate": (
                        (total_slow_queries / total_queries * 100)
                        if total_queries > 0
                        else 0
                    ),
                    "avg_query_time": avg_query_time,
                    "active_connections": self.connection_metrics["active_connections"],
                    "total_connections": self.connection_metrics["total_connections"],
                },
                "slowest_queries": [
                    {
                        "query_hash": q.query_hash,
                        "query_template": q.query_template[:100],
                        "max_duration": q.max_duration,
                        "avg_duration": q.avg_duration,
                        "execution_count": q.execution_count,
                    }
                    for q in slowest_queries
                ],
                "most_frequent_queries": [
                    {
                        "query_hash": q.query_hash,
                        "query_template": q.query_template[:100],
                        "execution_count": q.execution_count,
                        "avg_duration": q.avg_duration,
                        "total_duration": q.total_duration,
                    }
                    for q in most_frequent_queries
                ],
            }

    def reset_metrics(self):
        """메트릭 초기화"""
        with self._lock:
            self.query_metrics.clear()
            self.slow_queries.clear()
            logger.info("query_metrics_reset")


# 전역 쿼리 모니터 인스턴스
query_monitor = QueryMonitor(slow_query_threshold=1.0)
