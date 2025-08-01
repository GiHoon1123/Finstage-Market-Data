"""
데이터 정리 및 아카이빙 시스템

이 모듈은 오래된 데이터를 정리하고 아카이빙하는 기능을 제공합니다.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from sqlalchemy import text, and_
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine

from app.common.utils.logging_config import get_logger
from app.common.monitoring.metrics import metrics_collector
from app.common.monitoring.alerts import send_info_alert, send_warning_alert

logger = get_logger(__name__)


@dataclass
class CleanupRule:
    """데이터 정리 규칙"""

    table_name: str
    retention_days: int
    date_column: str
    condition: Optional[str] = None
    archive_before_delete: bool = True
    batch_size: int = 1000


@dataclass
class CleanupResult:
    """정리 작업 결과"""

    table_name: str
    records_processed: int
    records_deleted: int
    records_archived: int
    execution_time: float
    errors: List[str]


class DataCleanupManager:
    """데이터 정리 관리자"""

    def __init__(self, engine: Engine):
        self.engine = engine

        # 기본 정리 규칙 설정
        self.cleanup_rules = [
            # 뉴스 콘텐츠: 1년 후 아카이빙
            CleanupRule(
                table_name="contents",
                retention_days=365,
                date_column="published_at",
                archive_before_delete=True,
                batch_size=500,
            ),
            # 기술적 신호: 6개월 후 아카이빙
            CleanupRule(
                table_name="technical_signals",
                retention_days=180,
                date_column="triggered_at",
                archive_before_delete=True,
                batch_size=1000,
            ),
            # 신호 결과: 6개월 후 아카이빙
            CleanupRule(
                table_name="signal_outcomes",
                retention_days=180,
                date_column="outcome_date",
                archive_before_delete=True,
                batch_size=1000,
            ),
            # 일봉 데이터: 5년 후 아카이빙 (장기 보관)
            CleanupRule(
                table_name="daily_prices",
                retention_days=1825,  # 5년
                date_column="date",
                archive_before_delete=True,
                batch_size=2000,
            ),
            # 중복 뉴스 제거 (content_hash 기준)
            CleanupRule(
                table_name="contents",
                retention_days=0,  # 즉시 처리
                date_column="created_at",
                condition="duplicate_content_hash",
                archive_before_delete=False,
                batch_size=100,
            ),
        ]

    async def run_cleanup(
        self, table_name: Optional[str] = None, dry_run: bool = False
    ) -> List[CleanupResult]:
        """데이터 정리 실행"""
        results = []

        # 특정 테이블만 처리하거나 모든 테이블 처리
        rules_to_process = (
            [rule for rule in self.cleanup_rules if rule.table_name == table_name]
            if table_name
            else self.cleanup_rules
        )

        for rule in rules_to_process:
            try:
                logger.info(
                    "data_cleanup_started",
                    table=rule.table_name,
                    retention_days=rule.retention_days,
                    dry_run=dry_run,
                )

                result = await self._process_cleanup_rule(rule, dry_run)
                results.append(result)

                # 메트릭 기록
                metrics_collector.record_db_operation(
                    "cleanup", rule.table_name, "success", result.execution_time
                )

                logger.info(
                    "data_cleanup_completed",
                    table=rule.table_name,
                    processed=result.records_processed,
                    deleted=result.records_deleted,
                    archived=result.records_archived,
                    execution_time=result.execution_time,
                )

            except Exception as e:
                error_result = CleanupResult(
                    table_name=rule.table_name,
                    records_processed=0,
                    records_deleted=0,
                    records_archived=0,
                    execution_time=0,
                    errors=[str(e)],
                )
                results.append(error_result)

                logger.error("data_cleanup_failed", table=rule.table_name, error=str(e))

                metrics_collector.record_error("DataCleanupError", "data_cleanup")

        # 정리 결과 알림
        await self._send_cleanup_notification(results, dry_run)

        return results

    async def _process_cleanup_rule(
        self, rule: CleanupRule, dry_run: bool
    ) -> CleanupResult:
        """개별 정리 규칙 처리"""
        start_time = datetime.now()

        if rule.condition == "duplicate_content_hash":
            return await self._cleanup_duplicate_content(rule, dry_run)
        else:
            return await self._cleanup_old_records(rule, dry_run)

    async def _cleanup_old_records(
        self, rule: CleanupRule, dry_run: bool
    ) -> CleanupResult:
        """오래된 레코드 정리"""
        cutoff_date = datetime.now() - timedelta(days=rule.retention_days)

        records_processed = 0
        records_deleted = 0
        records_archived = 0
        errors = []

        try:
            with Session(self.engine) as session:
                # 정리 대상 레코드 수 조회
                count_query = text(
                    f"""
                    SELECT COUNT(*) 
                    FROM {rule.table_name} 
                    WHERE {rule.date_column} < :cutoff_date
                """
                )

                result = session.execute(count_query, {"cutoff_date": cutoff_date})
                total_records = result.scalar()

                if total_records == 0:
                    logger.info("no_records_to_cleanup", table=rule.table_name)
                    return CleanupResult(
                        table_name=rule.table_name,
                        records_processed=0,
                        records_deleted=0,
                        records_archived=0,
                        execution_time=(datetime.now() - start_time).total_seconds(),
                        errors=[],
                    )

                logger.info(
                    "cleanup_target_identified",
                    table=rule.table_name,
                    total_records=total_records,
                    cutoff_date=cutoff_date,
                )

                # 배치 단위로 처리
                processed = 0
                while processed < total_records:
                    batch_size = min(rule.batch_size, total_records - processed)

                    if rule.archive_before_delete and not dry_run:
                        # 아카이빙 먼저 수행
                        archived = await self._archive_records(
                            session, rule, cutoff_date, batch_size
                        )
                        records_archived += archived

                    if not dry_run:
                        # 레코드 삭제
                        delete_query = text(
                            f"""
                            DELETE FROM {rule.table_name} 
                            WHERE {rule.date_column} < :cutoff_date 
                            LIMIT :batch_size
                        """
                        )

                        delete_result = session.execute(
                            delete_query,
                            {"cutoff_date": cutoff_date, "batch_size": batch_size},
                        )

                        deleted_count = delete_result.rowcount
                        records_deleted += deleted_count
                        session.commit()

                        logger.debug(
                            "batch_cleanup_completed",
                            table=rule.table_name,
                            batch_deleted=deleted_count,
                        )

                    processed += batch_size
                    records_processed += batch_size

                    # 배치 간 잠시 대기 (DB 부하 방지)
                    await asyncio.sleep(0.1)

        except Exception as e:
            errors.append(str(e))
            logger.error(
                "cleanup_processing_error", table=rule.table_name, error=str(e)
            )

        execution_time = (datetime.now() - start_time).total_seconds()

        return CleanupResult(
            table_name=rule.table_name,
            records_processed=records_processed,
            records_deleted=records_deleted,
            records_archived=records_archived,
            execution_time=execution_time,
            errors=errors,
        )

    async def _cleanup_duplicate_content(
        self, rule: CleanupRule, dry_run: bool
    ) -> CleanupResult:
        """중복 콘텐츠 정리"""
        start_time = datetime.now()

        records_processed = 0
        records_deleted = 0
        errors = []

        try:
            with Session(self.engine) as session:
                # 중복 content_hash 찾기
                duplicate_query = text(
                    """
                    SELECT content_hash, COUNT(*) as cnt, MIN(id) as keep_id
                    FROM contents 
                    GROUP BY content_hash 
                    HAVING COUNT(*) > 1
                """
                )

                duplicates = session.execute(duplicate_query).fetchall()

                logger.info("duplicate_content_found", duplicate_groups=len(duplicates))

                for duplicate in duplicates:
                    content_hash = duplicate[0]
                    count = duplicate[1]
                    keep_id = duplicate[2]

                    if not dry_run:
                        # 가장 오래된 것을 제외하고 삭제
                        delete_query = text(
                            """
                            DELETE FROM contents 
                            WHERE content_hash = :content_hash 
                            AND id != :keep_id
                        """
                        )

                        delete_result = session.execute(
                            delete_query,
                            {"content_hash": content_hash, "keep_id": keep_id},
                        )

                        deleted_count = delete_result.rowcount
                        records_deleted += deleted_count
                        session.commit()

                    records_processed += count - 1  # 삭제될 레코드 수

        except Exception as e:
            errors.append(str(e))
            logger.error("duplicate_cleanup_error", error=str(e))

        execution_time = (datetime.now() - start_time).total_seconds()

        return CleanupResult(
            table_name=rule.table_name,
            records_processed=records_processed,
            records_deleted=records_deleted,
            records_archived=0,
            execution_time=execution_time,
            errors=errors,
        )

    async def _archive_records(
        self,
        session: Session,
        rule: CleanupRule,
        cutoff_date: datetime,
        batch_size: int,
    ) -> int:
        """레코드 아카이빙"""
        try:
            archive_table = f"{rule.table_name}_archive"

            # 아카이브 테이블이 없으면 생성
            await self._ensure_archive_table_exists(
                session, rule.table_name, archive_table
            )

            # 데이터를 아카이브 테이블로 복사
            archive_query = text(
                f"""
                INSERT INTO {archive_table} 
                SELECT * FROM {rule.table_name} 
                WHERE {rule.date_column} < :cutoff_date 
                LIMIT :batch_size
            """
            )

            result = session.execute(
                archive_query, {"cutoff_date": cutoff_date, "batch_size": batch_size}
            )

            archived_count = result.rowcount
            session.commit()

            logger.debug(
                "records_archived", table=rule.table_name, archived_count=archived_count
            )

            return archived_count

        except Exception as e:
            logger.error("archiving_failed", table=rule.table_name, error=str(e))
            return 0

    async def _ensure_archive_table_exists(
        self, session: Session, source_table: str, archive_table: str
    ):
        """아카이브 테이블 존재 확인 및 생성"""
        try:
            # 테이블 존재 확인
            check_query = text(
                """
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = :table_name
            """
            )

            result = session.execute(check_query, {"table_name": archive_table})
            exists = result.scalar() > 0

            if not exists:
                # 원본 테이블과 동일한 구조로 아카이브 테이블 생성
                create_query = text(
                    f"""
                    CREATE TABLE {archive_table} LIKE {source_table}
                """
                )

                session.execute(create_query)
                session.commit()

                logger.info(
                    "archive_table_created",
                    source_table=source_table,
                    archive_table=archive_table,
                )

        except Exception as e:
            logger.error(
                "archive_table_creation_failed",
                source_table=source_table,
                archive_table=archive_table,
                error=str(e),
            )
            raise

    async def _send_cleanup_notification(
        self, results: List[CleanupResult], dry_run: bool
    ):
        """정리 작업 결과 알림"""
        total_processed = sum(r.records_processed for r in results)
        total_deleted = sum(r.records_deleted for r in results)
        total_archived = sum(r.records_archived for r in results)
        total_errors = sum(len(r.errors) for r in results)

        if total_processed == 0:
            return

        # 성공적인 정리 작업 알림
        if total_errors == 0:
            await send_info_alert(
                title=f"Database Cleanup {'Simulation' if dry_run else 'Completed'}",
                message=f"Processed {total_processed} records, deleted {total_deleted}, archived {total_archived}",
                component="database_cleanup",
                details={
                    "dry_run": dry_run,
                    "tables_processed": len(results),
                    "total_processed": total_processed,
                    "total_deleted": total_deleted,
                    "total_archived": total_archived,
                    "results": [
                        {
                            "table": r.table_name,
                            "processed": r.records_processed,
                            "deleted": r.records_deleted,
                            "archived": r.records_archived,
                        }
                        for r in results
                        if r.records_processed > 0
                    ],
                },
            )
        else:
            # 에러가 있는 경우 경고 알림
            await send_warning_alert(
                title=f"Database Cleanup {'Simulation' if dry_run else 'Completed'} with Errors",
                message=f"Processed {total_processed} records with {total_errors} errors",
                component="database_cleanup",
                details={
                    "dry_run": dry_run,
                    "total_errors": total_errors,
                    "error_tables": [r.table_name for r in results if r.errors],
                    "results": [
                        {
                            "table": r.table_name,
                            "processed": r.records_processed,
                            "errors": r.errors,
                        }
                        for r in results
                    ],
                },
            )

    def get_cleanup_status(self) -> Dict[str, Any]:
        """정리 작업 상태 조회"""
        status = {"cleanup_rules": [], "estimated_cleanup_sizes": {}}

        try:
            with Session(self.engine) as session:
                for rule in self.cleanup_rules:
                    if rule.condition == "duplicate_content_hash":
                        # 중복 콘텐츠 수 조회
                        duplicate_query = text(
                            """
                            SELECT COUNT(*) - COUNT(DISTINCT content_hash) as duplicates
                            FROM contents
                        """
                        )
                        result = session.execute(duplicate_query)
                        estimated_size = result.scalar() or 0
                    else:
                        # 오래된 레코드 수 조회
                        cutoff_date = datetime.now() - timedelta(
                            days=rule.retention_days
                        )
                        count_query = text(
                            f"""
                            SELECT COUNT(*) 
                            FROM {rule.table_name} 
                            WHERE {rule.date_column} < :cutoff_date
                        """
                        )
                        result = session.execute(
                            count_query, {"cutoff_date": cutoff_date}
                        )
                        estimated_size = result.scalar() or 0

                    status["cleanup_rules"].append(
                        {
                            "table_name": rule.table_name,
                            "retention_days": rule.retention_days,
                            "date_column": rule.date_column,
                            "condition": rule.condition,
                            "archive_before_delete": rule.archive_before_delete,
                            "estimated_records_to_cleanup": estimated_size,
                        }
                    )

                    status["estimated_cleanup_sizes"][rule.table_name] = estimated_size

        except Exception as e:
            logger.error("cleanup_status_query_failed", error=str(e))
            status["error"] = str(e)

        return status

    async def schedule_cleanup(
        self, cron_expression: str = "0 2 * * 0"
    ):  # 매주 일요일 오전 2시
        """정기적인 데이터 정리 스케줄링"""
        # 실제 구현에서는 APScheduler 등을 사용
        logger.info("cleanup_scheduled", cron=cron_expression)

        # 예시: 매주 실행
        while True:
            try:
                # 일주일 대기
                await asyncio.sleep(7 * 24 * 3600)

                # 정리 작업 실행
                results = await self.run_cleanup()

                logger.info("scheduled_cleanup_completed", results_count=len(results))

            except Exception as e:
                logger.error("scheduled_cleanup_failed", error=str(e))
                await asyncio.sleep(3600)  # 1시간 후 재시도


# 편의 함수들
async def run_database_cleanup(
    engine: Engine, table_name: Optional[str] = None, dry_run: bool = True
) -> List[CleanupResult]:
    """데이터베이스 정리 실행"""
    manager = DataCleanupManager(engine)
    return await manager.run_cleanup(table_name, dry_run)


def get_cleanup_status(engine: Engine) -> Dict[str, Any]:
    """정리 작업 상태 조회"""
    manager = DataCleanupManager(engine)
    return manager.get_cleanup_status()
