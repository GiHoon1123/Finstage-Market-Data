"""
신호 패턴 리포지토리

이 파일은 신호 패턴 분석 데이터의 데이터베이스 접근을 담당합니다.
여러 신호들의 조합 패턴을 발견하고 분석하기 위한 고급 쿼리를 제공합니다.

주요 기능:
1. 패턴 저장/조회 - 발견된 신호 패턴 저장 및 관리
2. 패턴 발견 - 유사한 신호 조합 자동 탐지
3. 패턴 성과 분석 - 패턴별 성공률 및 수익률 분석
4. 시장 상황별 패턴 효과 - 상승장/하락장에서의 패턴 차이
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc, text
from app.technical_analysis.infra.model.entity.signal_patterns import SignalPattern
from app.technical_analysis.infra.model.entity.technical_signals import TechnicalSignal


class SignalPatternRepository:
    """
    신호 패턴 데이터 접근 객체

    복잡한 신호 패턴의 저장, 조회, 분석을 담당합니다.
    """

    def __init__(self, session: Session):
        """
        리포지토리 초기화

        Args:
            session: SQLAlchemy 세션 객체
        """
        self.session = session

    # =================================================================
    # CREATE 작업 (패턴 저장)
    # =================================================================

    def save_pattern(self, pattern: SignalPattern) -> SignalPattern:
        """
        신호 패턴을 데이터베이스에 저장

        Args:
            pattern: 저장할 패턴 엔티티

        Returns:
            저장된 패턴 엔티티
        """
        try:
            self.session.add(pattern)
            self.session.flush()
            return pattern
        except Exception as e:
            self.session.rollback()
            raise Exception(f"패턴 저장 실패: {e}")

    def create_sequential_pattern(
        self,
        pattern_name: str,
        symbol: str,
        timeframe: str,
        signal_ids: List[int],
        market_condition: Optional[str] = None,
    ) -> SignalPattern:
        """
        순차적 패턴 생성 (A → B → C 형태)

        Args:
            pattern_name: 패턴 이름
            symbol: 심볼
            timeframe: 시간대
            signal_ids: 신호 ID 리스트 (순서대로)
            market_condition: 시장 상황

        Returns:
            생성된 패턴 엔티티
        """
        if len(signal_ids) < 2:
            raise ValueError("순차적 패턴은 최소 2개의 신호가 필요합니다")

        # 첫 번째와 마지막 신호의 시간 조회
        first_signal = (
            self.session.query(TechnicalSignal)
            .filter(TechnicalSignal.id == signal_ids[0])
            .first()
        )
        last_signal = (
            self.session.query(TechnicalSignal)
            .filter(TechnicalSignal.id == signal_ids[-1])
            .first()
        )

        if not first_signal or not last_signal:
            raise ValueError("유효하지 않은 신호 ID가 포함되어 있습니다")

        # 패턴 지속 시간 계산
        duration = (
            last_signal.triggered_at - first_signal.triggered_at
        ).total_seconds() / 3600

        pattern = SignalPattern(
            pattern_name=pattern_name,
            pattern_type="sequential",
            symbol=symbol,
            timeframe=timeframe,
            first_signal_id=signal_ids[0] if len(signal_ids) > 0 else None,
            second_signal_id=signal_ids[1] if len(signal_ids) > 1 else None,
            third_signal_id=signal_ids[2] if len(signal_ids) > 2 else None,
            fourth_signal_id=signal_ids[3] if len(signal_ids) > 3 else None,
            fifth_signal_id=signal_ids[4] if len(signal_ids) > 4 else None,
            pattern_start=first_signal.triggered_at,
            pattern_end=last_signal.triggered_at,
            pattern_duration_hours=duration,
            market_condition=market_condition,
        )

        return self.save_pattern(pattern)

    # =================================================================
    # READ 작업 (패턴 조회)
    # =================================================================

    def find_by_pattern_name(
        self, pattern_name: str, symbol: Optional[str] = None, limit: int = 50
    ) -> List[SignalPattern]:
        """
        패턴 이름으로 조회

        Args:
            pattern_name: 패턴 이름
            symbol: 심볼 필터 (선택사항)
            limit: 최대 조회 개수

        Returns:
            해당 패턴 리스트
        """
        query = self.session.query(SignalPattern).filter(
            SignalPattern.pattern_name == pattern_name
        )

        if symbol:
            query = query.filter(SignalPattern.symbol == symbol)

        return query.order_by(desc(SignalPattern.pattern_start)).limit(limit).all()

    def find_patterns_by_signal(self, signal_id: int) -> List[SignalPattern]:
        """
        특정 신호가 포함된 모든 패턴 조회

        Args:
            signal_id: 신호 ID

        Returns:
            해당 신호가 포함된 패턴 리스트
        """
        return (
            self.session.query(SignalPattern)
            .filter(
                or_(
                    SignalPattern.first_signal_id == signal_id,
                    SignalPattern.second_signal_id == signal_id,
                    SignalPattern.third_signal_id == signal_id,
                    SignalPattern.fourth_signal_id == signal_id,
                    SignalPattern.fifth_signal_id == signal_id,
                )
            )
            .all()
        )

    def find_recent_patterns(
        self, days: int = 30, pattern_type: Optional[str] = None
    ) -> List[SignalPattern]:
        """
        최근 발생한 패턴들 조회

        Args:
            days: 조회할 일수
            pattern_type: 패턴 타입 필터 (선택사항)

        Returns:
            최근 패턴 리스트
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = self.session.query(SignalPattern).filter(
            SignalPattern.pattern_start >= cutoff_date
        )

        if pattern_type:
            query = query.filter(SignalPattern.pattern_type == pattern_type)

        return query.order_by(desc(SignalPattern.pattern_start)).all()

    # =================================================================
    # 패턴 발견 및 분석
    # =================================================================

    def discover_sequential_patterns(
        self,
        symbol: str,
        timeframe: str,
        max_hours_between: int = 24,
        min_pattern_length: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        순차적 패턴 자동 발견

        Args:
            symbol: 분석할 심볼
            timeframe: 시간대
            max_hours_between: 신호 간 최대 시간 간격 (시간)
            min_pattern_length: 최소 패턴 길이

        Returns:
            발견된 패턴 후보 리스트
        """
        # 최근 신호들 조회 (시간순 정렬)
        recent_signals = (
            self.session.query(TechnicalSignal)
            .filter(
                and_(
                    TechnicalSignal.symbol == symbol,
                    TechnicalSignal.timeframe == timeframe,
                    TechnicalSignal.triggered_at
                    >= datetime.utcnow() - timedelta(days=30),
                )
            )
            .order_by(asc(TechnicalSignal.triggered_at))
            .all()
        )

        patterns = []

        # 슬라이딩 윈도우로 패턴 탐지
        for i in range(len(recent_signals) - min_pattern_length + 1):
            for j in range(i + min_pattern_length, min(i + 6, len(recent_signals) + 1)):
                # 연속된 신호들 추출
                signal_sequence = recent_signals[i:j]

                # 시간 간격 체크
                valid_sequence = True
                for k in range(1, len(signal_sequence)):
                    time_diff = (
                        signal_sequence[k].triggered_at
                        - signal_sequence[k - 1].triggered_at
                    ).total_seconds() / 3600
                    if time_diff > max_hours_between:
                        valid_sequence = False
                        break

                if valid_sequence:
                    # 패턴 이름 생성
                    signal_types = [s.signal_type for s in signal_sequence]
                    pattern_name = "_then_".join(signal_types[:3])  # 최대 3개까지만

                    patterns.append(
                        {
                            "pattern_name": pattern_name,
                            "signal_ids": [s.id for s in signal_sequence],
                            "signal_types": signal_types,
                            "start_time": signal_sequence[0].triggered_at,
                            "end_time": signal_sequence[-1].triggered_at,
                            "duration_hours": (
                                signal_sequence[-1].triggered_at
                                - signal_sequence[0].triggered_at
                            ).total_seconds()
                            / 3600,
                        }
                    )

        return patterns

    def find_similar_patterns(
        self, reference_pattern_id: int, similarity_threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """
        유사한 패턴 찾기

        Args:
            reference_pattern_id: 기준 패턴 ID
            similarity_threshold: 유사도 임계값 (0~1)

        Returns:
            유사한 패턴 리스트 (유사도 포함)
        """
        reference = (
            self.session.query(SignalPattern)
            .filter(SignalPattern.id == reference_pattern_id)
            .first()
        )

        if not reference:
            return []

        # 같은 패턴 이름을 가진 패턴들 조회
        similar_patterns = (
            self.session.query(SignalPattern)
            .filter(
                and_(
                    SignalPattern.pattern_name == reference.pattern_name,
                    SignalPattern.id != reference_pattern_id,
                )
            )
            .all()
        )

        results = []
        for pattern in similar_patterns:
            # 유사도 계산 (간단한 버전)
            similarity = self._calculate_pattern_similarity(reference, pattern)

            if similarity >= similarity_threshold:
                results.append({"pattern": pattern, "similarity": similarity})

        # 유사도 순으로 정렬
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results

    def _calculate_pattern_similarity(
        self, pattern1: SignalPattern, pattern2: SignalPattern
    ) -> float:
        """
        두 패턴 간의 유사도 계산

        Args:
            pattern1: 첫 번째 패턴
            pattern2: 두 번째 패턴

        Returns:
            유사도 (0~1)
        """
        similarity = 0.0

        # 기본 속성 비교 (가중치 30%)
        if pattern1.symbol == pattern2.symbol:
            similarity += 0.1
        if pattern1.timeframe == pattern2.timeframe:
            similarity += 0.1
        if pattern1.pattern_type == pattern2.pattern_type:
            similarity += 0.1

        # 시장 상황 비교 (가중치 20%)
        if pattern1.market_condition == pattern2.market_condition:
            similarity += 0.2

        # 패턴 지속 시간 비교 (가중치 20%)
        if pattern1.pattern_duration_hours and pattern2.pattern_duration_hours:
            duration_diff = abs(
                float(pattern1.pattern_duration_hours)
                - float(pattern2.pattern_duration_hours)
            )
            max_duration = max(
                float(pattern1.pattern_duration_hours),
                float(pattern2.pattern_duration_hours),
            )
            duration_similarity = 1.0 - (duration_diff / max_duration)
            similarity += duration_similarity * 0.2

        # 결과 비교 (가중치 30%)
        outcome_similarity = 0.0
        for timeframe in ["1h", "1d", "1w"]:
            outcome1 = getattr(pattern1, f"pattern_outcome_{timeframe}")
            outcome2 = getattr(pattern2, f"pattern_outcome_{timeframe}")

            if outcome1 is not None and outcome2 is not None:
                # 같은 방향(양수/음수)이면 유사도 증가
                if (outcome1 > 0 and outcome2 > 0) or (outcome1 < 0 and outcome2 < 0):
                    outcome_similarity += 0.1

        similarity += outcome_similarity

        return min(similarity, 1.0)

    # =================================================================
    # 패턴 성과 분석
    # =================================================================

    def get_pattern_performance_stats(
        self, pattern_name: Optional[str] = None, symbol: Optional[str] = None, min_occurrences: int = 5
    ) -> List[Dict[str, Any]]:
        """
        패턴 성과 통계 조회

        Args:
            pattern_name: 특정 패턴명 (None이면 모든 패턴)
            symbol: 심볼 필터 (선택사항)
            min_occurrences: 최소 발생 횟수

        Returns:
            패턴 성과 통계 리스트
        """
        # 기본 쿼리 구성
        query = self.session.query(
            SignalPattern.pattern_name,
            SignalPattern.symbol,
            func.count(SignalPattern.id).label("total_count"),
            func.avg(SignalPattern.pattern_duration_hours).label("avg_duration"),
        )

        # 필터 적용
        if pattern_name:
            query = query.filter(SignalPattern.pattern_name == pattern_name)
        if symbol:
            query = query.filter(SignalPattern.symbol == symbol)

        # 그룹화 및 필터링
        if pattern_name and symbol:
            # 특정 패턴 + 특정 심볼
            query = query.group_by(SignalPattern.pattern_name, SignalPattern.symbol)
        elif pattern_name:
            # 특정 패턴, 모든 심볼
            query = query.group_by(SignalPattern.pattern_name, SignalPattern.symbol)
        elif symbol:
            # 특정 심볼, 모든 패턴
            query = query.group_by(SignalPattern.pattern_name, SignalPattern.symbol)
        else:
            # 모든 패턴, 모든 심볼
            query = query.group_by(SignalPattern.pattern_name, SignalPattern.symbol)

        # 최소 발생 횟수 필터
        query = query.having(func.count(SignalPattern.id) >= min_occurrences)

        # 결과 조회
        results = query.all()

        # 결과 포맷팅
        return [
            {
                "pattern_name": result.pattern_name,
                "symbol": result.symbol,
                "total_count": result.total_count,
                "avg_duration": float(result.avg_duration) if result.avg_duration else 0.0,
            }
            for result in results
        ]

    def get_best_patterns(
        self, timeframe_eval: str = "1d", min_occurrences: int = 5, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        가장 성과가 좋은 패턴들 조회

        Args:
            timeframe_eval: 평가 기간
            min_occurrences: 최소 발생 횟수
            limit: 조회할 개수

        Returns:
            성과 순으로 정렬된 패턴 리스트
        """
        outcome_column = getattr(SignalPattern, f"pattern_outcome_{timeframe_eval}")
        success_column = getattr(SignalPattern, f"is_successful_{timeframe_eval}")

        results = (
            self.session.query(
                SignalPattern.pattern_name,
                func.count(SignalPattern.id).label("total_count"),
                func.avg(outcome_column).label("avg_return"),
                func.sum(success_column.cast("integer")).label("success_count"),
                (
                    func.sum(success_column.cast("integer"))
                    * 100.0
                    / func.count(SignalPattern.id)
                ).label("success_rate"),
            )
            .filter(outcome_column.isnot(None))
            .group_by(SignalPattern.pattern_name)
            .having(func.count(SignalPattern.id) >= min_occurrences)
            .order_by(desc("avg_return"))
            .limit(limit)
            .all()
        )

        return [
            {
                "pattern_name": result.pattern_name,
                "total_count": result.total_count,
                "avg_return": float(result.avg_return) if result.avg_return else 0.0,
                "success_count": result.success_count or 0,
                "success_rate": (
                    float(result.success_rate) / 100.0 if result.success_rate else 0.0
                ),
            }
            for result in results
        ]

    def get_market_condition_analysis(
        self, pattern_name: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        시장 상황별 패턴 성과 분석

        Args:
            pattern_name: 패턴 이름

        Returns:
            시장 상황별 성과 딕셔너리
        """
        patterns = (
            self.session.query(SignalPattern)
            .filter(SignalPattern.pattern_name == pattern_name)
            .all()
        )

        # 시장 상황별로 그룹화
        market_groups = {}
        for pattern in patterns:
            condition = pattern.market_condition or "unknown"
            if condition not in market_groups:
                market_groups[condition] = []
            market_groups[condition].append(pattern)

        # 각 시장 상황별 통계 계산
        result = {}
        for condition, pattern_list in market_groups.items():
            outcomes_1d = [
                float(p.pattern_outcome_1d)
                for p in pattern_list
                if p.pattern_outcome_1d is not None
            ]
            successes_1d = [
                p.is_successful_1d
                for p in pattern_list
                if p.is_successful_1d is not None
            ]

            result[condition] = {
                "count": len(pattern_list),
                "avg_return": (
                    sum(outcomes_1d) / len(outcomes_1d) if outcomes_1d else 0.0
                ),
                "success_rate": (
                    sum(successes_1d) / len(successes_1d) if successes_1d else 0.0
                ),
                "min_return": min(outcomes_1d) if outcomes_1d else 0.0,
                "max_return": max(outcomes_1d) if outcomes_1d else 0.0,
            }

        return result
