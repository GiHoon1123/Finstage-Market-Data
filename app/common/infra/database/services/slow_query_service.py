"""
슬로우 쿼리 서비스

슬로우 쿼리 로그의 저장, 조회, 분석 기능을 제공합니다.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_
from sqlalchemy.exc import SQLAlchemyError

from app.common.infra.database.config.database_config import SessionLocal
from app.common.infra.database.models.slow_query_log import SlowQueryLog
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class SlowQueryService:
    """슬로우 쿼리 관리 서비스"""

    def __init__(self):
        self.batch_size = 100  # 배치 저장 크기
        self.pending_queries = []  # 대기 중인 쿼리들
        self.batch_lock = asyncio.Lock()

    async def save_slow_query(
        self,
        query_hash: str,
        query_template: str,
        original_query: str,
        duration: float,
        affected_rows: int,
        table_names: List[str],
        operation_type: str,
        execution_timestamp: datetime,
    ) -> bool:
        """슬로우 쿼리를 데이터베이스에 저장"""
        try:
            # 배치 저장을 위해 대기열에 추가
            slow_query_data = {
                "query_hash": query_hash,
                "query_template": query_template,
                "original_query": original_query,
                "duration": duration,
                "affected_rows": affected_rows,
                "table_names": table_names,
                "operation_type": operation_type,
                "execution_timestamp": execution_timestamp,
            }

            async with self.batch_lock:
                self.pending_queries.append(slow_query_data)

                # 배치 크기에 도달하면 저장
                if len(self.pending_queries) >= self.batch_size:
                    await self._flush_batch()

            return True

        except Exception as e:
            logger.error("slow_query_save_failed", error=str(e), query_hash=query_hash)
            return False

    async def _flush_batch(self):
        """대기 중인 슬로우 쿼리들을 배치로 저장"""
        if not self.pending_queries:
            return

        queries_to_save = self.pending_queries.copy()
        self.pending_queries.clear()

        # 별도 스레드에서 DB 저장 실행
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._save_batch_to_db, queries_to_save)

    def _save_batch_to_db(self, queries_data: List[Dict]):
        """실제 데이터베이스에 배치 저장"""
        db = SessionLocal()
        try:
            slow_query_logs = []

            for data in queries_data:
                slow_query_log = SlowQueryLog.from_slow_query_data(**data)
                slow_query_logs.append(slow_query_log)

            # 배치 저장
            db.add_all(slow_query_logs)
            db.commit()

            logger.info("slow_queries_batch_saved", count=len(slow_query_logs))

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(
                "slow_queries_batch_save_failed", error=str(e), count=len(queries_data)
            )
        finally:
            db.close()

    def get_slow_queries(
        self,
        hours: int = 24,
        limit: int = 100,
        min_duration: Optional[float] = None,
        operation_type: Optional[str] = None,
        table_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """슬로우 쿼리 조회"""
        db = SessionLocal()
        try:
            # 기본 쿼리
            query = db.query(SlowQueryLog)

            # 시간 범위 필터
            cutoff_time = datetime.now() - timedelta(hours=hours)
            query = query.filter(SlowQueryLog.execution_timestamp >= cutoff_time)

            # 추가 필터들
            if min_duration:
                query = query.filter(SlowQueryLog.duration >= min_duration)

            if operation_type:
                query = query.filter(
                    SlowQueryLog.operation_type == operation_type.upper()
                )

            if table_name:
                query = query.filter(SlowQueryLog.table_names.contains(table_name))

            # 정렬 및 제한
            slow_queries = (
                query.order_by(desc(SlowQueryLog.duration)).limit(limit).all()
            )

            return [sq.to_dict() for sq in slow_queries]

        except SQLAlchemyError as e:
            logger.error("slow_queries_retrieval_failed", error=str(e))
            return []
        finally:
            db.close()

    def get_slow_query_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """슬로우 쿼리 통계"""
        db = SessionLocal()
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            # 기본 통계
            total_count = (
                db.query(SlowQueryLog)
                .filter(SlowQueryLog.execution_timestamp >= cutoff_time)
                .count()
            )

            if total_count == 0:
                return {
                    "total_count": 0,
                    "avg_duration": 0,
                    "max_duration": 0,
                    "min_duration": 0,
                    "by_operation": {},
                    "by_table": {},
                    "hourly_distribution": [],
                }

            # 집계 쿼리
            stats = (
                db.query(
                    func.avg(SlowQueryLog.duration).label("avg_duration"),
                    func.max(SlowQueryLog.duration).label("max_duration"),
                    func.min(SlowQueryLog.duration).label("min_duration"),
                )
                .filter(SlowQueryLog.execution_timestamp >= cutoff_time)
                .first()
            )

            # 작업 타입별 통계
            operation_stats = (
                db.query(
                    SlowQueryLog.operation_type,
                    func.count(SlowQueryLog.id).label("count"),
                    func.avg(SlowQueryLog.duration).label("avg_duration"),
                )
                .filter(SlowQueryLog.execution_timestamp >= cutoff_time)
                .group_by(SlowQueryLog.operation_type)
                .all()
            )

            # 테이블별 통계 (상위 10개)
            table_stats = (
                db.query(
                    SlowQueryLog.table_names,
                    func.count(SlowQueryLog.id).label("count"),
                    func.avg(SlowQueryLog.duration).label("avg_duration"),
                )
                .filter(
                    and_(
                        SlowQueryLog.execution_timestamp >= cutoff_time,
                        SlowQueryLog.table_names.isnot(None),
                    )
                )
                .group_by(SlowQueryLog.table_names)
                .order_by(desc(func.count(SlowQueryLog.id)))
                .limit(10)
                .all()
            )

            # 시간대별 분포 (최근 24시간을 1시간 단위로)
            hourly_stats = []
            for i in range(24):
                hour_start = datetime.now() - timedelta(hours=i + 1)
                hour_end = datetime.now() - timedelta(hours=i)

                hour_count = (
                    db.query(SlowQueryLog)
                    .filter(
                        and_(
                            SlowQueryLog.execution_timestamp >= hour_start,
                            SlowQueryLog.execution_timestamp < hour_end,
                        )
                    )
                    .count()
                )

                hourly_stats.append(
                    {"hour": hour_start.strftime("%Y-%m-%d %H:00"), "count": hour_count}
                )

            return {
                "total_count": total_count,
                "avg_duration": float(stats.avg_duration) if stats.avg_duration else 0,
                "max_duration": float(stats.max_duration) if stats.max_duration else 0,
                "min_duration": float(stats.min_duration) if stats.min_duration else 0,
                "by_operation": {
                    op.operation_type
                    or "UNKNOWN": {
                        "count": op.count,
                        "avg_duration": float(op.avg_duration),
                    }
                    for op in operation_stats
                },
                "by_table": {
                    table.table_names: {
                        "count": table.count,
                        "avg_duration": float(table.avg_duration),
                    }
                    for table in table_stats
                },
                "hourly_distribution": list(reversed(hourly_stats)),  # 최신 순으로
            }

        except SQLAlchemyError as e:
            logger.error("slow_query_statistics_failed", error=str(e))
            return {}
        finally:
            db.close()

    def get_query_pattern_analysis(self, hours: int = 24) -> Dict[str, Any]:
        """쿼리 패턴 분석"""
        db = SessionLocal()
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            # 가장 자주 발생하는 슬로우 쿼리 패턴
            frequent_patterns = (
                db.query(
                    SlowQueryLog.query_hash,
                    SlowQueryLog.query_template,
                    func.count(SlowQueryLog.id).label("occurrence_count"),
                    func.avg(SlowQueryLog.duration).label("avg_duration"),
                    func.max(SlowQueryLog.duration).label("max_duration"),
                    func.sum(SlowQueryLog.affected_rows).label("total_affected_rows"),
                )
                .filter(SlowQueryLog.execution_timestamp >= cutoff_time)
                .group_by(SlowQueryLog.query_hash, SlowQueryLog.query_template)
                .order_by(desc(func.count(SlowQueryLog.id)))
                .limit(20)
                .all()
            )

            # 가장 느린 쿼리 패턴
            slowest_patterns = (
                db.query(
                    SlowQueryLog.query_hash,
                    SlowQueryLog.query_template,
                    func.count(SlowQueryLog.id).label("occurrence_count"),
                    func.avg(SlowQueryLog.duration).label("avg_duration"),
                    func.max(SlowQueryLog.duration).label("max_duration"),
                )
                .filter(SlowQueryLog.execution_timestamp >= cutoff_time)
                .group_by(SlowQueryLog.query_hash, SlowQueryLog.query_template)
                .order_by(desc(func.avg(SlowQueryLog.duration)))
                .limit(20)
                .all()
            )

            return {
                "most_frequent_patterns": [
                    {
                        "query_hash": pattern.query_hash,
                        "query_template": pattern.query_template[:200],  # 길이 제한
                        "occurrence_count": pattern.occurrence_count,
                        "avg_duration": float(pattern.avg_duration),
                        "max_duration": float(pattern.max_duration),
                        "total_affected_rows": pattern.total_affected_rows or 0,
                    }
                    for pattern in frequent_patterns
                ],
                "slowest_patterns": [
                    {
                        "query_hash": pattern.query_hash,
                        "query_template": pattern.query_template[:200],
                        "occurrence_count": pattern.occurrence_count,
                        "avg_duration": float(pattern.avg_duration),
                        "max_duration": float(pattern.max_duration),
                    }
                    for pattern in slowest_patterns
                ],
            }

        except SQLAlchemyError as e:
            logger.error("query_pattern_analysis_failed", error=str(e))
            return {"most_frequent_patterns": [], "slowest_patterns": []}
        finally:
            db.close()

    async def cleanup_old_logs(self, days: int = 30):
        """오래된 슬로우 쿼리 로그 정리"""
        cutoff_time = datetime.now() - timedelta(days=days)

        loop = asyncio.get_event_loop()
        deleted_count = await loop.run_in_executor(
            None, self._delete_old_logs, cutoff_time
        )

        logger.info("slow_query_logs_cleaned", deleted_count=deleted_count, days=days)
        return deleted_count

    def _delete_old_logs(self, cutoff_time: datetime) -> int:
        """실제 오래된 로그 삭제"""
        db = SessionLocal()
        try:
            deleted_count = (
                db.query(SlowQueryLog)
                .filter(SlowQueryLog.execution_timestamp < cutoff_time)
                .delete()
            )

            db.commit()
            return deleted_count

        except SQLAlchemyError as e:
            db.rollback()
            logger.error("slow_query_logs_cleanup_failed", error=str(e))
            return 0
        finally:
            db.close()

    async def force_flush(self):
        """대기 중인 모든 쿼리를 강제로 저장"""
        async with self.batch_lock:
            await self._flush_batch()


# 전역 슬로우 쿼리 서비스 인스턴스
slow_query_service = SlowQueryService()
