"""
데이터베이스 인덱스 최적화 시스템

이 모듈은 데이터베이스 테이블의 인덱스를 분석하고 최적화 권장사항을 제공합니다.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy import text, Index
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.common.utils.logging_config import get_logger
from app.common.infra.database.config.database_config import Base

logger = get_logger(__name__)


@dataclass
class IndexAnalysis:
    """인덱스 분석 결과"""

    table_name: str
    index_name: str
    columns: List[str]
    is_unique: bool
    cardinality: int
    size_mb: float
    usage_count: int
    last_used: Optional[str]
    efficiency_score: float
    recommendation: str


@dataclass
class TableAnalysis:
    """테이블 분석 결과"""

    table_name: str
    row_count: int
    size_mb: float
    indexes: List[IndexAnalysis]
    missing_indexes: List[Dict[str, Any]]
    redundant_indexes: List[str]
    optimization_score: float


class IndexOptimizer:
    """인덱스 최적화 클래스"""

    def __init__(self, engine: Engine):
        self.engine = engine

        # 주요 테이블별 권장 인덱스 패턴
        self.recommended_indexes = {
            "contents": [
                {"columns": ["symbol", "published_at"], "type": "composite"},
                {"columns": ["content_hash"], "type": "unique"},
                {"columns": ["source", "crawled_at"], "type": "composite"},
                {"columns": ["published_at"], "type": "single"},
            ],
            "technical_signals": [
                {"columns": ["symbol", "triggered_at"], "type": "composite"},
                {"columns": ["signal_type"], "type": "single"},
                {
                    "columns": ["symbol", "signal_type", "timeframe"],
                    "type": "composite",
                },
                {"columns": ["triggered_at"], "type": "single"},
                {"columns": ["alert_sent", "created_at"], "type": "composite"},
            ],
            "daily_prices": [
                {"columns": ["symbol", "date"], "type": "unique"},
                {"columns": ["symbol"], "type": "single"},
                {"columns": ["date"], "type": "single"},
            ],
            "signal_outcomes": [
                {"columns": ["signal_id"], "type": "unique"},
                {"columns": ["symbol", "outcome_date"], "type": "composite"},
                {"columns": ["outcome_type"], "type": "single"},
            ],
            "symbols": [
                {"columns": ["symbol"], "type": "unique"},
                {"columns": ["country"], "type": "single"},
            ],
        }

    def analyze_all_tables(self) -> List[TableAnalysis]:
        """모든 테이블의 인덱스 분석"""
        analyses = []

        with Session(self.engine) as session:
            # 모든 테이블 목록 조회
            tables = self._get_all_tables(session)

            for table_name in tables:
                try:
                    analysis = self._analyze_table(session, table_name)
                    if analysis:
                        analyses.append(analysis)
                except Exception as e:
                    logger.error(
                        "table_analysis_failed", table=table_name, error=str(e)
                    )

        return analyses

    def _get_all_tables(self, session: Session) -> List[str]:
        """데이터베이스의 모든 테이블 목록 조회"""
        try:
            # MySQL용 쿼리
            result = session.execute(
                text(
                    """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE()
                AND table_type = 'BASE TABLE'
            """
                )
            )

            return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.error("failed_to_get_tables", error=str(e))
            return []

    def _analyze_table(
        self, session: Session, table_name: str
    ) -> Optional[TableAnalysis]:
        """개별 테이블 분석"""
        try:
            # 테이블 기본 정보
            table_info = self._get_table_info(session, table_name)
            if not table_info:
                return None

            # 인덱스 분석
            indexes = self._analyze_table_indexes(session, table_name)

            # 누락된 인덱스 찾기
            missing_indexes = self._find_missing_indexes(table_name, indexes)

            # 중복 인덱스 찾기
            redundant_indexes = self._find_redundant_indexes(indexes)

            # 최적화 점수 계산
            optimization_score = self._calculate_optimization_score(
                table_name, indexes, missing_indexes, redundant_indexes
            )

            return TableAnalysis(
                table_name=table_name,
                row_count=table_info["row_count"],
                size_mb=table_info["size_mb"],
                indexes=indexes,
                missing_indexes=missing_indexes,
                redundant_indexes=redundant_indexes,
                optimization_score=optimization_score,
            )

        except Exception as e:
            logger.error("table_analysis_error", table=table_name, error=str(e))
            return None

    def _get_table_info(
        self, session: Session, table_name: str
    ) -> Optional[Dict[str, Any]]:
        """테이블 기본 정보 조회"""
        try:
            result = session.execute(
                text(
                    f"""
                SELECT 
                    table_rows as row_count,
                    ROUND((data_length + index_length) / 1024 / 1024, 2) as size_mb
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = :table_name
            """
                ),
                {"table_name": table_name},
            )

            row = result.fetchone()
            if row:
                return {"row_count": row[0] or 0, "size_mb": float(row[1] or 0)}
            return None

        except Exception as e:
            logger.error("failed_to_get_table_info", table=table_name, error=str(e))
            return None

    def _analyze_table_indexes(
        self, session: Session, table_name: str
    ) -> List[IndexAnalysis]:
        """테이블의 모든 인덱스 분석"""
        indexes = []

        try:
            # 인덱스 기본 정보 조회
            result = session.execute(
                text(
                    f"""
                SELECT 
                    index_name,
                    column_name,
                    non_unique,
                    cardinality,
                    seq_in_index
                FROM information_schema.statistics 
                WHERE table_schema = DATABASE() 
                AND table_name = :table_name
                ORDER BY index_name, seq_in_index
            """
                ),
                {"table_name": table_name},
            )

            # 인덱스별로 그룹화
            index_groups = {}
            for row in result.fetchall():
                index_name = row[0]
                if index_name not in index_groups:
                    index_groups[index_name] = {
                        "columns": [],
                        "is_unique": row[2] == 0,
                        "cardinality": row[3] or 0,
                    }
                index_groups[index_name]["columns"].append(row[1])

            # 각 인덱스 분석
            for index_name, info in index_groups.items():
                try:
                    # 인덱스 크기 조회
                    size_mb = self._get_index_size(session, table_name, index_name)

                    # 사용 통계 조회 (MySQL 5.7+)
                    usage_stats = self._get_index_usage_stats(
                        session, table_name, index_name
                    )

                    # 효율성 점수 계산
                    efficiency_score = self._calculate_index_efficiency(
                        info["cardinality"], size_mb, usage_stats["usage_count"]
                    )

                    # 권장사항 생성
                    recommendation = self._generate_index_recommendation(
                        table_name, index_name, info, efficiency_score
                    )

                    indexes.append(
                        IndexAnalysis(
                            table_name=table_name,
                            index_name=index_name,
                            columns=info["columns"],
                            is_unique=info["is_unique"],
                            cardinality=info["cardinality"],
                            size_mb=size_mb,
                            usage_count=usage_stats["usage_count"],
                            last_used=usage_stats["last_used"],
                            efficiency_score=efficiency_score,
                            recommendation=recommendation,
                        )
                    )

                except Exception as e:
                    logger.error(
                        "index_analysis_error",
                        table=table_name,
                        index=index_name,
                        error=str(e),
                    )

            return indexes

        except Exception as e:
            logger.error("failed_to_analyze_indexes", table=table_name, error=str(e))
            return []

    def _get_index_size(
        self, session: Session, table_name: str, index_name: str
    ) -> float:
        """인덱스 크기 조회 (MB)"""
        try:
            result = session.execute(
                text(
                    f"""
                SELECT ROUND(
                    (SELECT SUM(stat_value) 
                     FROM mysql.innodb_index_stats 
                     WHERE table_name = :table_name 
                     AND index_name = :index_name 
                     AND stat_name = 'size') * 16 / 1024 / 1024, 2
                ) as size_mb
            """
                ),
                {"table_name": table_name, "index_name": index_name},
            )

            row = result.fetchone()
            return float(row[0] or 0) if row else 0.0

        except Exception:
            # 인덱스 크기를 정확히 구할 수 없는 경우 추정값 사용
            return 0.1

    def _get_index_usage_stats(
        self, session: Session, table_name: str, index_name: str
    ) -> Dict[str, Any]:
        """인덱스 사용 통계 조회"""
        try:
            # performance_schema가 활성화된 경우에만 사용 가능
            result = session.execute(
                text(
                    f"""
                SELECT COUNT_READ, COUNT_WRITE, COUNT_FETCH
                FROM performance_schema.table_io_waits_summary_by_index_usage
                WHERE OBJECT_SCHEMA = DATABASE()
                AND OBJECT_NAME = :table_name
                AND INDEX_NAME = :index_name
            """
                ),
                {"table_name": table_name, "index_name": index_name},
            )

            row = result.fetchone()
            if row:
                return {
                    "usage_count": (row[0] or 0) + (row[1] or 0) + (row[2] or 0),
                    "last_used": None,  # MySQL에서는 마지막 사용 시간을 직접 제공하지 않음
                }
        except Exception:
            pass

        # 기본값 반환
        return {"usage_count": 0, "last_used": None}

    def _calculate_index_efficiency(
        self, cardinality: int, size_mb: float, usage_count: int
    ) -> float:
        """인덱스 효율성 점수 계산 (0-100)"""
        # 기본 점수
        score = 50.0

        # 카디널리티 점수 (높을수록 좋음)
        if cardinality > 1000:
            score += 20
        elif cardinality > 100:
            score += 10
        elif cardinality < 10:
            score -= 20

        # 사용 빈도 점수
        if usage_count > 1000:
            score += 20
        elif usage_count > 100:
            score += 10
        elif usage_count == 0:
            score -= 30

        # 크기 대비 효율성
        if size_mb > 0:
            efficiency_ratio = cardinality / size_mb
            if efficiency_ratio > 1000:
                score += 10
            elif efficiency_ratio < 100:
                score -= 10

        return max(0, min(100, score))

    def _generate_index_recommendation(
        self, table_name: str, index_name: str, info: Dict, efficiency_score: float
    ) -> str:
        """인덱스 권장사항 생성"""
        if efficiency_score < 30:
            if info["cardinality"] < 10:
                return "DROP - Low cardinality, consider removing this index"
            elif len(info["columns"]) > 3:
                return "OPTIMIZE - Too many columns, consider splitting"
            else:
                return "REVIEW - Low efficiency, check if still needed"

        elif efficiency_score < 50:
            return "MONITOR - Moderate efficiency, monitor usage"

        elif efficiency_score > 80:
            return "EXCELLENT - High efficiency index"

        else:
            return "GOOD - Well-performing index"

    def _find_missing_indexes(
        self, table_name: str, existing_indexes: List[IndexAnalysis]
    ) -> List[Dict[str, Any]]:
        """누락된 인덱스 찾기"""
        missing = []

        if table_name not in self.recommended_indexes:
            return missing

        recommended = self.recommended_indexes[table_name]
        existing_columns = set()

        # 기존 인덱스의 컬럼 조합 수집
        for index in existing_indexes:
            if len(index.columns) == 1:
                existing_columns.add(index.columns[0])
            else:
                existing_columns.add(tuple(index.columns))

        # 권장 인덱스와 비교
        for rec in recommended:
            columns = rec["columns"]
            if len(columns) == 1:
                key = columns[0]
            else:
                key = tuple(columns)

            if key not in existing_columns:
                missing.append(
                    {
                        "columns": columns,
                        "type": rec["type"],
                        "reason": f"Recommended for {table_name} table optimization",
                        "priority": "HIGH" if rec["type"] == "unique" else "MEDIUM",
                    }
                )

        return missing

    def _find_redundant_indexes(self, indexes: List[IndexAnalysis]) -> List[str]:
        """중복 인덱스 찾기"""
        redundant = []

        for i, index1 in enumerate(indexes):
            for j, index2 in enumerate(indexes[i + 1 :], i + 1):
                # 같은 컬럼으로 시작하는 인덱스 찾기
                if (
                    len(index1.columns) < len(index2.columns)
                    and index2.columns[: len(index1.columns)] == index1.columns
                ):

                    # 단일 컬럼 인덱스가 복합 인덱스에 포함되는 경우
                    redundant.append(
                        f"{index1.index_name} (covered by {index2.index_name})"
                    )

                elif (
                    len(index2.columns) < len(index1.columns)
                    and index1.columns[: len(index2.columns)] == index2.columns
                ):

                    redundant.append(
                        f"{index2.index_name} (covered by {index1.index_name})"
                    )

        return list(set(redundant))  # 중복 제거

    def _calculate_optimization_score(
        self,
        table_name: str,
        indexes: List[IndexAnalysis],
        missing_indexes: List[Dict],
        redundant_indexes: List[str],
    ) -> float:
        """테이블 최적화 점수 계산 (0-100)"""
        score = 70.0  # 기본 점수

        # 인덱스 효율성 평균
        if indexes:
            avg_efficiency = sum(idx.efficiency_score for idx in indexes) / len(indexes)
            score += (avg_efficiency - 50) * 0.3

        # 누락된 인덱스 페널티
        score -= len(missing_indexes) * 10

        # 중복 인덱스 페널티
        score -= len(redundant_indexes) * 5

        # 테이블별 특별 고려사항
        if table_name in ["technical_signals", "daily_prices", "contents"]:
            # 핵심 테이블은 더 엄격한 기준
            if len(missing_indexes) > 0:
                score -= 15

        return max(0, min(100, score))

    def generate_optimization_sql(self, analysis: TableAnalysis) -> List[str]:
        """최적화 SQL 생성"""
        sql_statements = []

        # 누락된 인덱스 생성
        for missing in analysis.missing_indexes:
            columns = ", ".join(missing["columns"])
            index_name = f"idx_{analysis.table_name}_{'_'.join(missing['columns'])}"

            if missing["type"] == "unique":
                sql = f"CREATE UNIQUE INDEX {index_name} ON {analysis.table_name} ({columns});"
            else:
                sql = f"CREATE INDEX {index_name} ON {analysis.table_name} ({columns});"

            sql_statements.append(sql)

        # 중복 인덱스 제거 (주의: 실제 실행 전 검토 필요)
        for redundant in analysis.redundant_indexes:
            index_name = redundant.split(" ")[0]
            sql = f"-- DROP INDEX {index_name} ON {analysis.table_name}; -- REVIEW BEFORE EXECUTION"
            sql_statements.append(sql)

        return sql_statements

    def get_optimization_report(self) -> Dict[str, Any]:
        """전체 최적화 보고서 생성"""
        analyses = self.analyze_all_tables()

        total_tables = len(analyses)
        total_indexes = sum(len(a.indexes) for a in analyses)
        total_missing = sum(len(a.missing_indexes) for a in analyses)
        total_redundant = sum(len(a.redundant_indexes) for a in analyses)
        avg_optimization_score = (
            sum(a.optimization_score for a in analyses) / total_tables
            if total_tables > 0
            else 0
        )

        # 가장 최적화가 필요한 테이블들
        needs_optimization = sorted(
            [a for a in analyses if a.optimization_score < 70],
            key=lambda x: x.optimization_score,
        )

        # 가장 비효율적인 인덱스들
        inefficient_indexes = []
        for analysis in analyses:
            for index in analysis.indexes:
                if index.efficiency_score < 40:
                    inefficient_indexes.append(
                        {
                            "table": analysis.table_name,
                            "index": index.index_name,
                            "efficiency_score": index.efficiency_score,
                            "recommendation": index.recommendation,
                        }
                    )

        inefficient_indexes.sort(key=lambda x: x["efficiency_score"])

        return {
            "summary": {
                "total_tables": total_tables,
                "total_indexes": total_indexes,
                "missing_indexes": total_missing,
                "redundant_indexes": total_redundant,
                "avg_optimization_score": round(avg_optimization_score, 2),
                "optimization_status": (
                    "EXCELLENT"
                    if avg_optimization_score >= 90
                    else (
                        "GOOD"
                        if avg_optimization_score >= 80
                        else (
                            "NEEDS_IMPROVEMENT"
                            if avg_optimization_score >= 60
                            else "CRITICAL"
                        )
                    )
                ),
            },
            "tables_needing_optimization": [
                {
                    "table_name": a.table_name,
                    "optimization_score": a.optimization_score,
                    "missing_indexes": len(a.missing_indexes),
                    "redundant_indexes": len(a.redundant_indexes),
                    "row_count": a.row_count,
                    "size_mb": a.size_mb,
                }
                for a in needs_optimization[:10]
            ],
            "inefficient_indexes": inefficient_indexes[:10],
            "detailed_analyses": [
                {
                    "table_name": a.table_name,
                    "optimization_score": a.optimization_score,
                    "indexes": len(a.indexes),
                    "missing_indexes": a.missing_indexes,
                    "redundant_indexes": a.redundant_indexes,
                }
                for a in analyses
            ],
        }


# 편의 함수
def analyze_database_indexes(engine: Engine) -> Dict[str, Any]:
    """데이터베이스 인덱스 분석 실행"""
    optimizer = IndexOptimizer(engine)
    return optimizer.get_optimization_report()


def generate_index_optimization_sql(
    engine: Engine, table_name: str = None
) -> List[str]:
    """인덱스 최적화 SQL 생성"""
    optimizer = IndexOptimizer(engine)
    analyses = optimizer.analyze_all_tables()

    all_sql = []
    for analysis in analyses:
        if table_name is None or analysis.table_name == table_name:
            sql_statements = optimizer.generate_optimization_sql(analysis)
            all_sql.extend(sql_statements)

    return all_sql
