"""
데이터베이스 최적화 관련 API 엔드포인트

데이터베이스 성능 모니터링, 인덱스 분석, 연결 풀 상태 등을 제공합니다.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
import asyncio

from app.common.infra.database.config.database_config import engine
from app.common.infra.database.monitoring.query_monitor import query_monitor
from app.common.infra.database.optimization.index_optimizer import (
    IndexOptimizer,
    analyze_database_indexes,
    generate_index_optimization_sql,
)
from app.common.infra.database.optimization.connection_pool_manager import (
    get_pool_manager,
)
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)

# 데이터베이스 최적화 라우터 생성
db_router = APIRouter(prefix="/database", tags=["database"])


@db_router.get("/query-stats", summary="쿼리 통계 조회")
async def get_query_statistics(
    limit: int = Query(50, description="조회할 쿼리 수", ge=1, le=100)
) -> Dict[str, Any]:
    """
    데이터베이스 쿼리 실행 통계를 조회합니다.

    가장 느린 쿼리, 자주 실행되는 쿼리 등의 정보를 제공합니다.
    """
    try:
        stats = query_monitor.get_query_statistics(limit)
        performance_summary = query_monitor.get_performance_summary()

        return {
            "query_statistics": stats,
            "performance_summary": performance_summary,
            "total_queries": len(stats),
        }

    except Exception as e:
        logger.error("query_statistics_retrieval_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to retrieve query statistics"
        )


@db_router.get("/slow-queries", summary="슬로우 쿼리 조회")
async def get_slow_queries(
    hours: int = Query(24, description="조회할 시간 범위 (시간)", ge=1, le=168)
) -> Dict[str, Any]:
    """
    지정된 시간 범위 내의 슬로우 쿼리를 조회합니다.
    """
    try:
        slow_queries = query_monitor.get_slow_queries(hours)

        return {
            "slow_queries": slow_queries,
            "total_count": len(slow_queries),
            "time_range_hours": hours,
            "threshold_seconds": query_monitor.slow_query_threshold,
        }

    except Exception as e:
        logger.error("slow_queries_retrieval_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve slow queries")


@db_router.get("/connection-pool", summary="연결 풀 상태 조회")
async def get_connection_pool_status() -> Dict[str, Any]:
    """
    데이터베이스 연결 풀의 현재 상태를 조회합니다.
    """
    try:
        pool_manager = get_pool_manager()
        if not pool_manager:
            raise HTTPException(
                status_code=503, detail="Connection pool manager not initialized"
            )

        status = pool_manager.get_pool_status()
        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.error("connection_pool_status_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to retrieve connection pool status"
        )


@db_router.post("/connection-pool/optimize", summary="연결 풀 최적화")
async def optimize_connection_pool() -> Dict[str, Any]:
    """
    연결 풀을 분석하고 최적화 권장사항을 제공합니다.
    """
    try:
        pool_manager = get_pool_manager()
        if not pool_manager:
            raise HTTPException(
                status_code=503, detail="Connection pool manager not initialized"
            )

        # 연결 풀 상태 확인 및 조정
        adjustment_result = await pool_manager.check_and_adjust_pool()

        # 최적화 권장사항 생성
        optimization_result = await pool_manager.optimize_pool_settings()

        return {
            "adjustment_result": adjustment_result,
            "optimization_recommendations": optimization_result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("connection_pool_optimization_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to optimize connection pool"
        )


@db_router.get("/connection-pool/metrics", summary="연결 풀 메트릭 히스토리")
async def get_connection_pool_metrics(
    hours: int = Query(24, description="조회할 시간 범위 (시간)", ge=1, le=168)
) -> Dict[str, Any]:
    """
    연결 풀의 과거 메트릭 데이터를 조회합니다.
    """
    try:
        pool_manager = get_pool_manager()
        if not pool_manager:
            raise HTTPException(
                status_code=503, detail="Connection pool manager not initialized"
            )

        metrics = pool_manager.get_historical_metrics(hours)

        return {
            "metrics": metrics,
            "total_records": len(metrics),
            "time_range_hours": hours,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("connection_pool_metrics_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to retrieve connection pool metrics"
        )


@db_router.get("/indexes/analysis", summary="인덱스 분석")
async def analyze_indexes() -> Dict[str, Any]:
    """
    데이터베이스의 모든 인덱스를 분석하고 최적화 권장사항을 제공합니다.
    """
    try:
        # 비동기로 인덱스 분석 실행 (시간이 오래 걸릴 수 있음)
        analysis_result = await asyncio.get_event_loop().run_in_executor(
            None, analyze_database_indexes, engine
        )

        return analysis_result

    except Exception as e:
        logger.error("index_analysis_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to analyze database indexes"
        )


@db_router.get("/indexes/optimization-sql", summary="인덱스 최적화 SQL 생성")
async def generate_optimization_sql(
    table_name: Optional[str] = Query(
        None, description="특정 테이블만 대상으로 할 경우"
    )
) -> Dict[str, Any]:
    """
    인덱스 최적화를 위한 SQL 문을 생성합니다.
    """
    try:
        # 비동기로 SQL 생성 실행
        sql_statements = await asyncio.get_event_loop().run_in_executor(
            None, generate_index_optimization_sql, engine, table_name
        )

        return {
            "sql_statements": sql_statements,
            "total_statements": len(sql_statements),
            "target_table": table_name,
            "warning": "Please review all SQL statements before execution in production",
        }

    except Exception as e:
        logger.error("optimization_sql_generation_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to generate optimization SQL"
        )


@db_router.get("/performance-summary", summary="데이터베이스 성능 요약")
async def get_performance_summary() -> Dict[str, Any]:
    """
    데이터베이스의 전반적인 성능 요약 정보를 제공합니다.
    """
    try:
        # 쿼리 성능 요약
        query_summary = query_monitor.get_performance_summary()

        # 연결 풀 상태
        pool_manager = get_pool_manager()
        pool_status = pool_manager.get_pool_status() if pool_manager else None

        # 인덱스 분석 요약 (캐시된 결과 사용)
        try:
            index_summary = await asyncio.get_event_loop().run_in_executor(
                None, analyze_database_indexes, engine
            )
            index_optimization_score = index_summary.get("summary", {}).get(
                "avg_optimization_score", 0
            )
        except Exception:
            index_optimization_score = None

        return {
            "query_performance": {
                "total_queries": query_summary["summary"]["total_queries"],
                "slow_queries": query_summary["summary"]["slow_queries"],
                "slow_query_rate": query_summary["summary"]["slow_query_rate"],
                "avg_query_time": query_summary["summary"]["avg_query_time"],
            },
            "connection_pool": {
                "status": pool_status["health_status"] if pool_status else "UNKNOWN",
                "utilization": (
                    pool_status["current_metrics"]["utilization"] if pool_status else 0
                ),
                "active_connections": (
                    pool_status["current_metrics"]["total_connections"]
                    if pool_status
                    else 0
                ),
            },
            "index_optimization": {
                "score": index_optimization_score,
                "status": (
                    "EXCELLENT"
                    if index_optimization_score and index_optimization_score >= 90
                    else (
                        "GOOD"
                        if index_optimization_score and index_optimization_score >= 80
                        else (
                            "NEEDS_IMPROVEMENT"
                            if index_optimization_score
                            and index_optimization_score >= 60
                            else "CRITICAL" if index_optimization_score else "UNKNOWN"
                        )
                    )
                ),
            },
            "overall_health": _calculate_overall_health(
                query_summary, pool_status, index_optimization_score
            ),
        }

    except Exception as e:
        logger.error("performance_summary_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to generate performance summary"
        )


@db_router.post("/maintenance/reset-metrics", summary="메트릭 초기화")
async def reset_metrics() -> Dict[str, Any]:
    """
    수집된 쿼리 메트릭을 초기화합니다. (개발/테스트 환경에서만 사용)
    """
    try:
        query_monitor.reset_metrics()

        return {
            "status": "success",
            "message": "Query metrics have been reset",
            "timestamp": query_monitor.get_performance_summary()["summary"][
                "total_queries"
            ],
        }

    except Exception as e:
        logger.error("metrics_reset_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to reset metrics")


def _calculate_overall_health(
    query_summary: Dict, pool_status: Optional[Dict], index_score: Optional[float]
) -> str:
    """전체 데이터베이스 건강 상태 계산"""
    health_score = 100

    # 쿼리 성능 점수
    slow_query_rate = query_summary["summary"]["slow_query_rate"]
    if slow_query_rate > 10:
        health_score -= 30
    elif slow_query_rate > 5:
        health_score -= 15

    avg_query_time = query_summary["summary"]["avg_query_time"]
    if avg_query_time > 1.0:
        health_score -= 20
    elif avg_query_time > 0.5:
        health_score -= 10

    # 연결 풀 점수
    if pool_status:
        pool_health = pool_status["health_status"]
        if pool_health == "CRITICAL":
            health_score -= 40
        elif pool_health == "WARNING":
            health_score -= 20

    # 인덱스 점수
    if index_score:
        if index_score < 60:
            health_score -= 25
        elif index_score < 80:
            health_score -= 10

    # 건강 상태 결정
    if health_score >= 90:
        return "EXCELLENT"
    elif health_score >= 80:
        return "GOOD"
    elif health_score >= 60:
        return "WARNING"
    else:
        return "CRITICAL"
