"""
슬로우 쿼리 로그 모델

데이터베이스에서 실행된 슬로우 쿼리들을 저장하고 관리합니다.
"""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Index
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, Any, Optional

from app.common.infra.database.config.database_config import Base


class SlowQueryLog(Base):
    """슬로우 쿼리 로그 테이블"""

    __tablename__ = "slow_query_logs"

    # 기본 필드
    id = Column(Integer, primary_key=True, autoincrement=True)
    query_hash = Column(
        String(32),
        nullable=False,
        index=True,
        comment="쿼리 해시 (정규화된 쿼리 식별자)",
    )
    query_template = Column(Text, nullable=False, comment="정규화된 쿼리 템플릿")
    original_query = Column(Text, nullable=True, comment="원본 쿼리 (최대 2000자)")

    # 성능 메트릭
    duration = Column(Float, nullable=False, index=True, comment="실행 시간 (초)")
    affected_rows = Column(Integer, default=0, comment="영향받은 행 수")

    # 메타데이터
    table_names = Column(
        String(500), nullable=True, comment="관련 테이블명들 (쉼표 구분)"
    )
    operation_type = Column(
        String(20),
        nullable=True,
        index=True,
        comment="쿼리 타입 (SELECT, INSERT, etc.)",
    )

    # 시간 정보
    created_at = Column(
        DateTime, default=func.now(), nullable=False, index=True, comment="기록 시간"
    )
    execution_timestamp = Column(
        DateTime, nullable=False, index=True, comment="쿼리 실행 시간"
    )

    # 인덱스 정의
    __table_args__ = (
        Index("idx_slow_query_hash_time", "query_hash", "execution_timestamp"),
        Index("idx_slow_query_duration_time", "duration", "execution_timestamp"),
        Index("idx_slow_query_operation_time", "operation_type", "execution_timestamp"),
        Index("idx_slow_query_execution_time", "execution_timestamp"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "query_hash": self.query_hash,
            "query_template": self.query_template,
            "original_query": self.original_query,
            "duration": self.duration,
            "affected_rows": self.affected_rows,
            "table_names": self.table_names.split(",") if self.table_names else [],
            "operation_type": self.operation_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "execution_timestamp": (
                self.execution_timestamp.isoformat()
                if self.execution_timestamp
                else None
            ),
        }

    @classmethod
    def from_slow_query_data(
        cls,
        query_hash: str,
        query_template: str,
        original_query: str,
        duration: float,
        affected_rows: int,
        table_names: list,
        operation_type: str,
        execution_timestamp: datetime,
    ) -> "SlowQueryLog":
        """슬로우 쿼리 데이터로부터 인스턴스 생성"""
        return cls(
            query_hash=query_hash,
            query_template=query_template,
            original_query=(
                original_query[:2000] if original_query else None
            ),  # 길이 제한
            duration=duration,
            affected_rows=affected_rows,
            table_names=",".join(table_names) if table_names else None,
            operation_type=operation_type,
            execution_timestamp=execution_timestamp,
        )

    def __repr__(self):
        return f"<SlowQueryLog(id={self.id}, hash={self.query_hash}, duration={self.duration}s)>"
