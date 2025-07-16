"""
기술적 신호 리포지토리

이 파일은 기술적 신호 데이터의 데이터베이스 접근을 담당합니다.
비즈니스 로직과 데이터 접근 로직을 분리하여 코드의 유지보수성을 높입니다.

주요 기능:
1. 신호 저장 (CREATE)
2. 신호 조회 (READ) - 다양한 조건으로 조회
3. 신호 수정 (UPDATE) - 알림 발송 상태 등 업데이트
4. 통계 조회 - 백테스팅 및 분석용 집계 쿼리

리포지토리 패턴의 장점:
- 데이터 접근 로직 중앙화
- 테스트 용이성 (Mock 객체 사용 가능)
- 데이터베이스 변경시 영향 최소화
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from app.technical_analysis.infra.model.entity.technical_signals import TechnicalSignal


class TechnicalSignalRepository:
    """
    기술적 신호 데이터 접근 객체

    모든 기술적 신호 관련 데이터베이스 작업을 담당합니다.
    """

    def __init__(self, session: Session):
        """
        리포지토리 초기화

        Args:
            session: SQLAlchemy 세션 객체
        """
        self.session = session

    # =================================================================
    # CREATE 작업 (신호 저장)
    # =================================================================

    def save(self, signal: TechnicalSignal) -> TechnicalSignal:
        """
        기술적 신호를 데이터베이스에 저장

        Args:
            signal: 저장할 기술적 신호 엔티티

        Returns:
            저장된 신호 엔티티 (ID가 할당됨)

        Example:
            signal = TechnicalSignal(
                symbol="NQ=F",
                signal_type="MA200_breakout_up",
                current_price=23050.75
            )
            saved_signal = repository.save(signal)
        """
        try:
            self.session.add(signal)
            self.session.flush()  # ID 할당을 위해 flush (commit은 서비스에서)
            return signal
        except Exception as e:
            self.session.rollback()
            raise Exception(f"신호 저장 실패: {e}")

    def bulk_save(self, signals: List[TechnicalSignal]) -> List[TechnicalSignal]:
        """
        여러 신호를 한번에 저장 (성능 최적화)

        Args:
            signals: 저장할 신호 리스트

        Returns:
            저장된 신호 리스트
        """
        try:
            self.session.add_all(signals)
            self.session.flush()
            return signals
        except Exception as e:
            self.session.rollback()
            raise Exception(f"신호 일괄 저장 실패: {e}")

    # =================================================================
    # READ 작업 (신호 조회)
    # =================================================================

    def find_by_id(self, signal_id: int) -> Optional[TechnicalSignal]:
        """
        ID로 신호 조회

        Args:
            signal_id: 신호 ID

        Returns:
            신호 엔티티 또는 None
        """
        return (
            self.session.query(TechnicalSignal)
            .filter(TechnicalSignal.id == signal_id)
            .first()
        )

    def find_by_symbol(
        self, symbol: str, limit: int = 100, offset: int = 0
    ) -> List[TechnicalSignal]:
        """
        심볼별 신호 조회 (최신순)

        Args:
            symbol: 심볼 (예: NQ=F, ^IXIC)
            limit: 조회할 최대 개수
            offset: 건너뛸 개수 (페이징용)

        Returns:
            신호 리스트 (최신순)
        """
        return (
            self.session.query(TechnicalSignal)
            .filter(TechnicalSignal.symbol == symbol)
            .order_by(desc(TechnicalSignal.triggered_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

    def find_by_signal_type(
        self,
        signal_type: str,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        limit: int = 100,
    ) -> List[TechnicalSignal]:
        """
        신호 타입별 조회

        Args:
            signal_type: 신호 타입 (예: MA200_breakout_up)
            symbol: 심볼 필터 (선택사항)
            timeframe: 시간대 필터 (선택사항)
            limit: 조회할 최대 개수

        Returns:
            해당 타입의 신호 리스트
        """
        query = self.session.query(TechnicalSignal).filter(
            TechnicalSignal.signal_type == signal_type
        )

        # 선택적 필터 적용
        if symbol:
            query = query.filter(TechnicalSignal.symbol == symbol)
        if timeframe:
            query = query.filter(TechnicalSignal.timeframe == timeframe)

        return query.order_by(desc(TechnicalSignal.triggered_at)).limit(limit).all()

    def find_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        symbol: Optional[str] = None,
        signal_type: Optional[str] = None,
    ) -> List[TechnicalSignal]:
        """
        날짜 범위로 신호 조회 (백테스팅용)

        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            symbol: 심볼 필터 (선택사항)
            signal_type: 신호 타입 필터 (선택사항)

        Returns:
            해당 기간의 신호 리스트
        """
        query = self.session.query(TechnicalSignal).filter(
            and_(
                TechnicalSignal.triggered_at >= start_date,
                TechnicalSignal.triggered_at <= end_date,
            )
        )

        # 선택적 필터 적용
        if symbol:
            query = query.filter(TechnicalSignal.symbol == symbol)
        if signal_type:
            query = query.filter(TechnicalSignal.signal_type == signal_type)

        return query.order_by(asc(TechnicalSignal.triggered_at)).all()

    def find_recent_signals(
        self, hours: int = 24, symbol: Optional[str] = None
    ) -> List[TechnicalSignal]:
        """
        최근 N시간 내 발생한 신호 조회

        Args:
            hours: 조회할 시간 범위 (시간)
            symbol: 심볼 필터 (선택사항)

        Returns:
            최근 신호 리스트
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        query = self.session.query(TechnicalSignal).filter(
            TechnicalSignal.triggered_at >= cutoff_time
        )

        if symbol:
            query = query.filter(TechnicalSignal.symbol == symbol)

        return query.order_by(desc(TechnicalSignal.triggered_at)).all()

    # =================================================================
    # UPDATE 작업 (신호 수정)
    # =================================================================

    def update_alert_status(self, signal_id: int, alert_sent: bool) -> bool:
        """
        알림 발송 상태 업데이트

        Args:
            signal_id: 신호 ID
            alert_sent: 알림 발송 여부

        Returns:
            업데이트 성공 여부
        """
        try:
            updated_rows = (
                self.session.query(TechnicalSignal)
                .filter(TechnicalSignal.id == signal_id)
                .update(
                    {
                        TechnicalSignal.alert_sent: alert_sent,
                        TechnicalSignal.alert_sent_at: (
                            datetime.utcnow() if alert_sent else None
                        ),
                        TechnicalSignal.updated_at: datetime.utcnow(),
                    }
                )
            )

            return updated_rows > 0
        except Exception as e:
            self.session.rollback()
            raise Exception(f"알림 상태 업데이트 실패: {e}")

    # =================================================================
    # 통계 및 집계 쿼리 (백테스팅용)
    # =================================================================

    def get_signal_count_by_type(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        신호 타입별 발생 횟수 통계

        Args:
            start_date: 시작 날짜 (선택사항)
            end_date: 종료 날짜 (선택사항)

        Returns:
            신호 타입별 통계 리스트
            [{'signal_type': 'MA200_breakout_up', 'count': 15}, ...]
        """
        query = self.session.query(
            TechnicalSignal.signal_type, func.count(TechnicalSignal.id).label("count")
        )

        # 날짜 필터 적용
        if start_date:
            query = query.filter(TechnicalSignal.triggered_at >= start_date)
        if end_date:
            query = query.filter(TechnicalSignal.triggered_at <= end_date)

        results = query.group_by(TechnicalSignal.signal_type).all()

        return [
            {"signal_type": result.signal_type, "count": result.count}
            for result in results
        ]

    def get_daily_signal_count(
        self, symbol: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        일별 신호 발생 횟수 (차트용)

        Args:
            symbol: 심볼
            days: 조회할 일수

        Returns:
            일별 신호 횟수 리스트
            [{'date': '2025-01-16', 'count': 5}, ...]
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        results = (
            self.session.query(
                func.date(TechnicalSignal.triggered_at).label("date"),
                func.count(TechnicalSignal.id).label("count"),
            )
            .filter(
                and_(
                    TechnicalSignal.symbol == symbol,
                    TechnicalSignal.triggered_at >= start_date,
                )
            )
            .group_by(func.date(TechnicalSignal.triggered_at))
            .order_by(asc(func.date(TechnicalSignal.triggered_at)))
            .all()
        )

        return [
            {"date": result.date.strftime("%Y-%m-%d"), "count": result.count}
            for result in results
        ]

    def get_signal_strength_stats(
        self, signal_type: str, symbol: Optional[str] = None
    ) -> Dict[str, float]:
        """
        신호 강도 통계 (평균, 최대, 최소)

        Args:
            signal_type: 신호 타입
            symbol: 심볼 (선택사항)

        Returns:
            통계 딕셔너리
            {'avg': 2.5, 'max': 5.2, 'min': 0.1, 'count': 100}
        """
        query = self.session.query(
            func.avg(TechnicalSignal.signal_strength).label("avg"),
            func.max(TechnicalSignal.signal_strength).label("max"),
            func.min(TechnicalSignal.signal_strength).label("min"),
            func.count(TechnicalSignal.id).label("count"),
        ).filter(
            and_(
                TechnicalSignal.signal_type == signal_type,
                TechnicalSignal.signal_strength.isnot(None),
            )
        )

        if symbol:
            query = query.filter(TechnicalSignal.symbol == symbol)

        result = query.first()

        return {
            "avg": float(result.avg) if result.avg else 0.0,
            "max": float(result.max) if result.max else 0.0,
            "min": float(result.min) if result.min else 0.0,
            "count": result.count,
        }

    # =================================================================
    # 중복 체크 (알림 스팸 방지용)
    # =================================================================

    def exists_recent_signal(
        self, symbol: str, signal_type: str, minutes: int = 60
    ) -> bool:
        """
        최근 N분 내에 동일한 신호가 발생했는지 확인
        (중복 알림 방지용)

        Args:
            symbol: 심볼
            signal_type: 신호 타입
            minutes: 확인할 시간 범위 (분)

        Returns:
            중복 신호 존재 여부
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

        count = (
            self.session.query(TechnicalSignal)
            .filter(
                and_(
                    TechnicalSignal.symbol == symbol,
                    TechnicalSignal.signal_type == signal_type,
                    TechnicalSignal.triggered_at >= cutoff_time,
                )
            )
            .count()
        )

        return count > 0
