"""
신호 결과 리포지토리

이 리포지토리는 기술적 신호 발생 후의 결과 데이터를 관리합니다.
신호가 발생한 후 시간이 지나면서 실제 가격이 어떻게 변했는지,
수익률은 얼마나 되는지 등을 추적하고 저장하는 역할을 합니다.

주요 기능:
1. 결과 레코드 생성 - 신호 발생시 빈 결과 레코드 생성
2. 가격 업데이트 - 시간대별 가격 정보 업데이트 (1시간, 4시간, 1일, 1주, 1개월 후)
3. 수익률 계산 - 각 시간대별 수익률 자동 계산
4. 성과 통계 - 신호 타입별, 심볼별 성과 통계 제공
5. 백테스팅 지원 - 과거 신호들의 실제 성과 데이터 제공

데이터 흐름:
1. 신호 발생 → 빈 결과 레코드 생성 (모든 가격 필드 NULL)
2. 1시간 후 → price_1h_after 업데이트 → return_1h 계산
3. 4시간 후 → price_4h_after 업데이트 → return_4h 계산
4. 1일 후 → price_1d_after 업데이트 → return_1d 계산 → is_successful_1d 판정
5. 1주 후 → price_1w_after 업데이트 → return_1w 계산 → is_successful_1w 판정
6. 1개월 후 → price_1m_after 업데이트 → return_1m 계산 → is_complete = True

이렇게 수집된 데이터는 백테스팅과 신호 품질 평가에 사용됩니다.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from app.technical_analysis.infra.model.entity.signal_outcomes import SignalOutcome
from app.technical_analysis.infra.model.entity.technical_signals import TechnicalSignal


class SignalOutcomeRepository:
    """
    신호 결과 데이터 접근을 담당하는 리포지토리

    기술적 신호 발생 후의 실제 성과를 추적하고 관리합니다.
    """

    def __init__(self, session: Session):
        """
        리포지토리 초기화

        Args:
            session: SQLAlchemy 세션 객체
        """
        self.session = session

    # =================================================================
    # 기본 CRUD 작업
    # =================================================================

    def create_outcome_record(self, signal_id: int) -> SignalOutcome:
        """
        신호에 대한 빈 결과 레코드 생성

        신호가 발생하면 즉시 호출하여 결과 추적을 위한 빈 레코드를 만듭니다.
        모든 가격 필드는 NULL로 시작하고, 시간이 지나면서 점진적으로 채워집니다.

        Args:
            signal_id: 추적할 신호의 ID

        Returns:
            생성된 결과 레코드

        Raises:
            Exception: 신호가 존재하지 않거나 이미 결과 레코드가 있는 경우
        """
        # 1. 신호 존재 여부 확인
        signal = (
            self.session.query(TechnicalSignal)
            .filter(TechnicalSignal.id == signal_id)
            .first()
        )

        if not signal:
            raise Exception(f"신호를 찾을 수 없습니다: ID {signal_id}")

        # 2. 이미 결과 레코드가 있는지 확인
        existing_outcome = (
            self.session.query(SignalOutcome)
            .filter(SignalOutcome.signal_id == signal_id)
            .first()
        )

        if existing_outcome:
            raise Exception(f"이미 결과 레코드가 존재합니다: 신호 ID {signal_id}")

        # 3. 새 결과 레코드 생성
        outcome = SignalOutcome(
            signal_id=signal_id,
            # 모든 가격 필드는 NULL로 시작 (시간이 지나면서 채워짐)
            price_1h_after=None,
            price_4h_after=None,
            price_1d_after=None,
            price_1w_after=None,
            price_1m_after=None,
            # 모든 수익률 필드도 NULL로 시작
            return_1h=None,
            return_4h=None,
            return_1d=None,
            return_1w=None,
            return_1m=None,
            # 성공 여부도 NULL로 시작
            is_successful_1d=None,
            is_successful_1w=None,
            is_successful_1m=None,
            # 최대/최소 수익률도 NULL로 시작
            max_return=None,
            min_return=None,
            # 추적 상태
            is_complete=False,
            created_at=datetime.utcnow(),
            last_updated_at=datetime.utcnow(),
        )

        self.session.add(outcome)
        self.session.flush()  # ID 생성을 위해 flush

        return outcome

    def find_by_id(self, outcome_id: int) -> Optional[SignalOutcome]:
        """
        ID로 결과 레코드 조회

        Args:
            outcome_id: 결과 레코드 ID

        Returns:
            결과 레코드 또는 None
        """
        return (
            self.session.query(SignalOutcome)
            .filter(SignalOutcome.id == outcome_id)
            .first()
        )

    def find_by_signal_id(self, signal_id: int) -> Optional[SignalOutcome]:
        """
        신호 ID로 결과 레코드 조회

        Args:
            signal_id: 신호 ID

        Returns:
            해당 신호의 결과 레코드 또는 None
        """
        return (
            self.session.query(SignalOutcome)
            .filter(SignalOutcome.signal_id == signal_id)
            .first()
        )

    def find_incomplete_outcomes(self, hours_old: int = 1) -> List[SignalOutcome]:
        """
        미완료 결과 레코드들 조회

        아직 모든 시간대의 가격이 수집되지 않은 결과들을 조회합니다.
        스케줄러에서 주기적으로 호출하여 업데이트할 대상을 찾습니다.

        Args:
            hours_old: 몇 시간 이상 된 것만 조회 (너무 최근 것은 제외)

        Returns:
            미완료 결과 레코드 리스트
        """
        # 기준 시간 계산 (현재 시간 - hours_old)
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_old)

        # 미완료 조건:
        # 1. is_complete = False
        # 2. 생성된 지 hours_old 시간 이상 경과
        # 3. 아직 채워지지 않은 가격 필드가 있음
        return (
            self.session.query(SignalOutcome)
            .join(TechnicalSignal)
            .filter(
                and_(
                    SignalOutcome.is_complete == False,
                    TechnicalSignal.triggered_at <= cutoff_time,
                    or_(
                        SignalOutcome.price_1h_after.is_(None),
                        SignalOutcome.price_4h_after.is_(None),
                        SignalOutcome.price_1d_after.is_(None),
                        SignalOutcome.price_1w_after.is_(None),
                        SignalOutcome.price_1m_after.is_(None),
                    ),
                )
            )
            .order_by(asc(SignalOutcome.created_at))
            .all()
        )

    # =================================================================
    # 가격 및 수익률 업데이트
    # =================================================================

    def update_outcome_prices(
        self,
        outcome_id: int,
        price_1h: Optional[float] = None,
        price_4h: Optional[float] = None,
        price_1d: Optional[float] = None,
        price_1w: Optional[float] = None,
        price_1m: Optional[float] = None,
    ) -> bool:
        """
        결과 레코드의 가격 정보 업데이트

        시간대별로 가격을 업데이트합니다. None이 아닌 값만 업데이트됩니다.

        Args:
            outcome_id: 업데이트할 결과 레코드 ID
            price_1h: 1시간 후 가격
            price_4h: 4시간 후 가격
            price_1d: 1일 후 가격
            price_1w: 1주 후 가격
            price_1m: 1개월 후 가격

        Returns:
            업데이트 성공 여부
        """
        try:
            # 업데이트할 필드들 준비
            update_fields = {SignalOutcome.last_updated_at: datetime.utcnow()}

            if price_1h is not None:
                update_fields[SignalOutcome.price_1h_after] = price_1h
            if price_4h is not None:
                update_fields[SignalOutcome.price_4h_after] = price_4h
            if price_1d is not None:
                update_fields[SignalOutcome.price_1d_after] = price_1d
            if price_1w is not None:
                update_fields[SignalOutcome.price_1w_after] = price_1w
            if price_1m is not None:
                update_fields[SignalOutcome.price_1m_after] = price_1m

            # 업데이트 실행
            rows_updated = (
                self.session.query(SignalOutcome)
                .filter(SignalOutcome.id == outcome_id)
                .update(update_fields)
            )

            return rows_updated > 0

        except Exception as e:
            print(f"❌ 가격 업데이트 실패: {e}")
            return False

    def calculate_and_update_returns(self, outcome_id: int) -> bool:
        """
        수익률 계산 및 업데이트

        원본 신호의 가격과 각 시간대별 가격을 비교하여 수익률을 계산합니다.
        또한 신호의 방향(상승/하락)에 따라 성공 여부도 판정합니다.

        Args:
            outcome_id: 계산할 결과 레코드 ID

        Returns:
            계산 및 업데이트 성공 여부
        """
        try:
            # 1. 결과 레코드와 원본 신호 조회
            outcome = (
                self.session.query(SignalOutcome)
                .join(TechnicalSignal)
                .filter(SignalOutcome.id == outcome_id)
                .first()
            )

            if not outcome or not outcome.signal:
                return False

            original_price = float(outcome.signal.current_price)
            signal_type = outcome.signal.signal_type.lower()

            # 2. 신호 방향 판정 (상승 신호인지 하락 신호인지)
            is_bullish_signal = any(
                keyword in signal_type
                for keyword in [
                    "breakout_up",
                    "golden_cross",
                    "oversold",
                    "bullish",
                    "touch_lower",
                ]
            )

            # 3. 업데이트할 필드들 준비
            update_fields = {SignalOutcome.last_updated_at: datetime.utcnow()}

            returns = []  # 최대/최소 수익률 계산용

            # 4. 각 시간대별 수익률 계산
            if outcome.price_1h_after is not None:
                return_1h = (
                    (float(outcome.price_1h_after) - original_price) / original_price
                ) * 100
                update_fields[SignalOutcome.return_1h] = return_1h
                returns.append(return_1h)

            if outcome.price_4h_after is not None:
                return_4h = (
                    (float(outcome.price_4h_after) - original_price) / original_price
                ) * 100
                update_fields[SignalOutcome.return_4h] = return_4h
                returns.append(return_4h)

            if outcome.price_1d_after is not None:
                return_1d = (
                    (float(outcome.price_1d_after) - original_price) / original_price
                ) * 100
                update_fields[SignalOutcome.return_1d] = return_1d
                returns.append(return_1d)

                # 1일 후 성공 여부 판정
                if is_bullish_signal:
                    update_fields[SignalOutcome.is_successful_1d] = return_1d > 0
                else:
                    update_fields[SignalOutcome.is_successful_1d] = return_1d < 0

            if outcome.price_1w_after is not None:
                return_1w = (
                    (float(outcome.price_1w_after) - original_price) / original_price
                ) * 100
                update_fields[SignalOutcome.return_1w] = return_1w
                returns.append(return_1w)

                # 1주 후 성공 여부 판정
                if is_bullish_signal:
                    update_fields[SignalOutcome.is_successful_1w] = return_1w > 0
                else:
                    update_fields[SignalOutcome.is_successful_1w] = return_1w < 0

            if outcome.price_1m_after is not None:
                return_1m = (
                    (float(outcome.price_1m_after) - original_price) / original_price
                ) * 100
                update_fields[SignalOutcome.return_1m] = return_1m
                returns.append(return_1m)

                # 1개월 후 성공 여부 판정
                if is_bullish_signal:
                    update_fields[SignalOutcome.is_successful_1m] = return_1m > 0
                else:
                    update_fields[SignalOutcome.is_successful_1m] = return_1m < 0

                # 1개월까지 완료되면 추적 완료 표시
                update_fields[SignalOutcome.is_complete] = True

            # 5. 최대/최소 수익률 계산
            if returns:
                update_fields[SignalOutcome.max_return] = max(returns)
                update_fields[SignalOutcome.min_return] = min(returns)

            # 6. 업데이트 실행
            rows_updated = (
                self.session.query(SignalOutcome)
                .filter(SignalOutcome.id == outcome_id)
                .update(update_fields)
            )

            return rows_updated > 0

        except Exception as e:
            print(f"❌ 수익률 계산 실패: {e}")
            return False

    # =================================================================
    # 성과 통계 및 분석 쿼리
    # =================================================================

    def get_success_rate_by_signal_type(
        self, timeframe_eval: str = "1d", min_samples: int = 10
    ) -> List[Dict[str, Any]]:
        """
        신호 타입별 성공률 통계

        각 신호 타입이 얼마나 자주 성공하는지 통계를 제공합니다.
        백테스팅과 신호 품질 평가에 사용됩니다.

        Args:
            timeframe_eval: 평가 기간 ('1d', '1w', '1m')
            min_samples: 최소 샘플 수 (이보다 적으면 제외)

        Returns:
            신호 타입별 성공률 리스트
            [
                {
                    'signal_type': 'MA200_breakout_up',
                    'total_count': 50,
                    'success_count': 35,
                    'success_rate': 0.70
                },
                ...
            ]
        """
        # 평가 기간에 따른 성공 필드 선택
        success_field_map = {
            "1d": SignalOutcome.is_successful_1d,
            "1w": SignalOutcome.is_successful_1w,
            "1m": SignalOutcome.is_successful_1m,
        }

        success_field = success_field_map.get(
            timeframe_eval, SignalOutcome.is_successful_1d
        )

        # 쿼리 실행
        results = (
            self.session.query(
                TechnicalSignal.signal_type,
                func.count(SignalOutcome.id).label("total_count"),
                func.sum(func.cast(success_field, func.INTEGER)).label("success_count"),
            )
            .join(SignalOutcome)
            .filter(success_field.is_not(None))  # 평가가 완료된 것만
            .group_by(TechnicalSignal.signal_type)
            .having(func.count(SignalOutcome.id) >= min_samples)
            .all()
        )

        # 결과 포맷팅
        return [
            {
                "signal_type": result.signal_type,
                "total_count": result.total_count,
                "success_count": result.success_count or 0,
                "success_rate": (
                    (result.success_count or 0) / result.total_count
                    if result.total_count > 0
                    else 0.0
                ),
            }
            for result in results
        ]

    def get_average_returns_by_signal_type(
        self, timeframe_eval: str = "1d", min_samples: int = 10
    ) -> List[Dict[str, Any]]:
        """
        신호 타입별 평균 수익률 통계

        Args:
            timeframe_eval: 평가 기간 ('1h', '4h', '1d', '1w', '1m')
            min_samples: 최소 샘플 수

        Returns:
            신호 타입별 평균 수익률 리스트
        """
        # 평가 기간에 따른 수익률 필드 선택
        return_field_map = {
            "1h": SignalOutcome.return_1h,
            "4h": SignalOutcome.return_4h,
            "1d": SignalOutcome.return_1d,
            "1w": SignalOutcome.return_1w,
            "1m": SignalOutcome.return_1m,
        }

        return_field = return_field_map.get(timeframe_eval, SignalOutcome.return_1d)

        # 쿼리 실행
        results = (
            self.session.query(
                TechnicalSignal.signal_type,
                func.count(SignalOutcome.id).label("total_count"),
                func.avg(return_field).label("avg_return"),
                func.max(return_field).label("max_return"),
                func.min(return_field).label("min_return"),
            )
            .join(SignalOutcome)
            .filter(return_field.is_not(None))  # 수익률이 계산된 것만
            .group_by(TechnicalSignal.signal_type)
            .having(func.count(SignalOutcome.id) >= min_samples)
            .all()
        )

        # 결과 포맷팅
        return [
            {
                "signal_type": result.signal_type,
                "total_count": result.total_count,
                "avg_return": float(result.avg_return) if result.avg_return else 0.0,
                "max_return": float(result.max_return) if result.max_return else 0.0,
                "min_return": float(result.min_return) if result.min_return else 0.0,
            }
            for result in results
        ]

    def get_best_performing_signals(
        self, timeframe_eval: str = "1d", min_samples: int = 10, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        가장 좋은 성과를 보인 신호들 조회

        Args:
            timeframe_eval: 평가 기간
            min_samples: 최소 샘플 수
            limit: 조회할 개수

        Returns:
            최고 성과 신호 리스트
        """
        return_field_map = {
            "1h": SignalOutcome.return_1h,
            "4h": SignalOutcome.return_4h,
            "1d": SignalOutcome.return_1d,
            "1w": SignalOutcome.return_1w,
            "1m": SignalOutcome.return_1m,
        }

        return_field = return_field_map.get(timeframe_eval, SignalOutcome.return_1d)

        # 쿼리 실행
        results = (
            self.session.query(
                TechnicalSignal.signal_type,
                TechnicalSignal.symbol,
                TechnicalSignal.timeframe,
                func.count(SignalOutcome.id).label("total_count"),
                func.avg(return_field).label("avg_return"),
            )
            .join(SignalOutcome)
            .filter(return_field.is_not(None))
            .group_by(
                TechnicalSignal.signal_type,
                TechnicalSignal.symbol,
                TechnicalSignal.timeframe,
            )
            .having(func.count(SignalOutcome.id) >= min_samples)
            .order_by(desc(func.avg(return_field)))
            .limit(limit)
            .all()
        )

        # 결과 포맷팅
        return [
            {
                "signal_type": result.signal_type,
                "symbol": result.symbol,
                "timeframe": result.timeframe,
                "total_count": result.total_count,
                "avg_return": float(result.avg_return) if result.avg_return else 0.0,
            }
            for result in results
        ]

    def get_performance_by_timeframe(
        self, signal_type: str, symbol: Optional[str] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        특정 신호의 시간대별 성과 분석

        Args:
            signal_type: 신호 타입
            symbol: 심볼 필터 (선택사항)

        Returns:
            시간대별 성과 딕셔너리
            {
                '1h': {'avg_return': 0.5, 'success_rate': 0.6, 'count': 20},
                '4h': {'avg_return': 1.2, 'success_rate': 0.65, 'count': 20},
                ...
            }
        """
        base_query = (
            self.session.query(SignalOutcome)
            .join(TechnicalSignal)
            .filter(TechnicalSignal.signal_type == signal_type)
        )

        if symbol:
            base_query = base_query.filter(TechnicalSignal.symbol == symbol)

        outcomes = base_query.all()

        result = {}

        # 각 시간대별 성과 계산
        timeframes = [
            ("1h", "return_1h", None),
            ("4h", "return_4h", None),
            ("1d", "return_1d", "is_successful_1d"),
            ("1w", "return_1w", "is_successful_1w"),
            ("1m", "return_1m", "is_successful_1m"),
        ]

        for tf_name, return_attr, success_attr in timeframes:
            returns = []
            successes = []

            for outcome in outcomes:
                return_val = getattr(outcome, return_attr)
                if return_val is not None:
                    returns.append(float(return_val))

                    if success_attr:
                        success_val = getattr(outcome, success_attr)
                        if success_val is not None:
                            successes.append(success_val)

            if returns:
                result[tf_name] = {
                    "avg_return": sum(returns) / len(returns),
                    "max_return": max(returns),
                    "min_return": min(returns),
                    "count": len(returns),
                    "success_rate": (
                        sum(successes) / len(successes) if successes else None
                    ),
                }

        return result

    def get_risk_metrics(
        self, signal_type: str, timeframe_eval: str = "1d", symbol: Optional[str] = None
    ) -> Dict[str, float]:
        """
        리스크 지표 계산

        Args:
            signal_type: 신호 타입
            timeframe_eval: 평가 기간
            symbol: 심볼 필터

        Returns:
            리스크 지표 딕셔너리
        """
        return_field_map = {
            "1h": SignalOutcome.return_1h,
            "4h": SignalOutcome.return_4h,
            "1d": SignalOutcome.return_1d,
            "1w": SignalOutcome.return_1w,
            "1m": SignalOutcome.return_1m,
        }

        return_field = return_field_map.get(timeframe_eval, SignalOutcome.return_1d)

        query = (
            self.session.query(return_field)
            .join(TechnicalSignal)
            .filter(
                and_(
                    TechnicalSignal.signal_type == signal_type,
                    return_field.is_not(None),
                )
            )
        )

        if symbol:
            query = query.filter(TechnicalSignal.symbol == symbol)

        returns = [float(r[0]) for r in query.all()]

        if not returns:
            return {}

        # 기본 통계
        avg_return = sum(returns) / len(returns)
        max_return = max(returns)
        min_return = min(returns)

        # 변동성 (표준편차)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        volatility = variance**0.5

        # 최대 손실률 (가장 큰 음수 수익률)
        max_drawdown = min(returns) if returns else 0

        # 샤프 비율 (위험 대비 수익률)
        sharpe_ratio = avg_return / volatility if volatility > 0 else 0

        # 승률
        win_rate = len([r for r in returns if r > 0]) / len(returns)

        # 수익 팩터 (총 수익 / 총 손실)
        total_gains = sum(r for r in returns if r > 0)
        total_losses = abs(sum(r for r in returns if r < 0))
        profit_factor = total_gains / total_losses if total_losses > 0 else float("inf")

        return {
            "total_trades": len(returns),
            "avg_return": avg_return,
            "max_return": max_return,
            "min_return": min_return,
            "max_drawdown": max_drawdown,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
        }

    def find_outcomes_by_signal_type(
        self, signal_type: str, symbol: Optional[str] = None, limit: int = 100
    ) -> List[SignalOutcome]:
        """
        신호 타입별 결과 레코드 조회

        Args:
            signal_type: 신호 타입
            symbol: 심볼 필터
            limit: 최대 조회 개수

        Returns:
            결과 레코드 리스트
        """
        query = (
            self.session.query(SignalOutcome)
            .join(TechnicalSignal)
            .filter(TechnicalSignal.signal_type == signal_type)
        )

        if symbol:
            query = query.filter(TechnicalSignal.symbol == symbol)

        return query.order_by(desc(SignalOutcome.created_at)).limit(limit).all()
