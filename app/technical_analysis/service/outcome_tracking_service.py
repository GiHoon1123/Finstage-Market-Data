"""
신호 결과 추적 서비스

이 서비스는 기술적 신호가 발생한 후의 결과를 추적하여 성과를 측정합니다.
신호 발생 후 1시간, 4시간, 1일, 1주일, 1개월 후의 가격을 수집하고
수익률을 계산하여 신호의 품질을 평가합니다.

결과 추적의 목적:
1. 신호 품질 평가: 어떤 신호가 실제로 효과적인지 판단
2. 백테스팅 데이터 수집: 과거 신호들의 성과 분석
3. 알림 최적화: 성과가 좋은 신호만 알림 발송
4. 매매 전략 개발: 효과적인 신호 조합 발견

작동 방식:
1. 신호 발생시 빈 결과 레코드 생성
2. 스케줄러가 주기적으로 실행되어 미완료 결과들 조회
3. 각 시간대별로 현재 가격 수집 및 수익률 계산
4. 1개월 후까지 모든 데이터 수집 완료되면 추적 완료 표시

수집 데이터:
- 시간대별 가격: 1시간, 4시간, 1일, 1주일, 1개월 후
- 수익률: 각 시간대별 수익률 (%)
- 최대/최소: 최대 수익률, 최대 손실률
- 성공 여부: 신호 방향에 따른 성공/실패 판정

데이터 활용:
- 백테스팅: 과거 신호들의 실제 성과 분석
- 신호 필터링: 성과가 좋지 않은 신호 제외
- 전략 최적화: 시간대별 최적 매매 타이밍 발견
- 리스크 관리: 최대 손실률 기반 손절매 설정
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.common.infra.database.config.database_config import SessionLocal
from app.common.infra.client.yahoo_price_client import YahooPriceClient
from app.technical_analysis.infra.model.repository.signal_outcome_repository import (
    SignalOutcomeRepository,
)
from app.technical_analysis.infra.model.repository.technical_signal_repository import (
    TechnicalSignalRepository,
)
from app.technical_analysis.infra.model.entity.signal_outcomes import SignalOutcome
from app.technical_analysis.infra.model.entity.technical_signals import TechnicalSignal


class OutcomeTrackingService:
    """
    신호 결과 추적을 담당하는 서비스

    기술적 신호가 발생한 후의 결과를 추적하여 성과를 측정합니다.
    """

    def __init__(self):
        """서비스 초기화"""
        self.session: Optional[Session] = None
        self.outcome_repository: Optional[SignalOutcomeRepository] = None
        self.signal_repository: Optional[TechnicalSignalRepository] = None
        self.yahoo_client = YahooPriceClient()

    def _get_session_and_repositories(self):
        """세션과 리포지토리 초기화 (지연 초기화)"""
        if not self.session:
            self.session = SessionLocal()
            self.outcome_repository = SignalOutcomeRepository(self.session)
            self.signal_repository = TechnicalSignalRepository(self.session)
        return self.session, self.outcome_repository, self.signal_repository

    # =================================================================
    # 결과 추적 초기화
    # =================================================================

    def initialize_outcome_tracking(self, signal_id: int) -> Optional[SignalOutcome]:
        """
        신호에 대한 결과 추적 초기화

        신호가 발생하면 즉시 호출하여 빈 결과 레코드를 생성합니다.
        모든 가격 필드는 NULL로 시작하고, 시간이 지나면서 점진적으로 채워집니다.

        Args:
            signal_id: 추적할 신호의 ID

        Returns:
            생성된 결과 추적 레코드 또는 None

        Note:
            신호가 발생하면 즉시 호출하여 빈 결과 레코드를 생성합니다.
            실제 가격 수집은 스케줄러에서 주기적으로 수행됩니다.
        """
        session, outcome_repo, signal_repo = self._get_session_and_repositories()

        try:
            # 1. 신호 존재 확인
            signal = signal_repo.find_by_id(signal_id)
            if not signal:
                print(f"❌ 신호를 찾을 수 없음: ID {signal_id}")
                return None

            # 2. 이미 결과 레코드가 있는지 확인
            existing_outcome = outcome_repo.find_by_signal_id(signal_id)
            if existing_outcome:
                print(f"⚠️ 이미 결과 추적 중: 신호 ID {signal_id}")
                return existing_outcome

            # 3. 새 결과 레코드 생성
            outcome = outcome_repo.create_outcome_record(signal_id)
            session.commit()

            print(f"✅ 결과 추적 초기화 완료: 신호 ID {signal_id}")
            print(f"   - 신호 타입: {signal.signal_type}")
            print(f"   - 심볼: {signal.symbol}")
            print(f"   - 발생 시간: {signal.triggered_at}")
            print(f"   - 원본 가격: ${signal.current_price}")

            return outcome

        except Exception as e:
            session.rollback()
            print(f"❌ 결과 추적 초기화 실패: {e}")
            return None
        finally:
            session.close()

    # =================================================================
    # 결과 추적 업데이트
    # =================================================================

    def update_outcomes(self, hours_old: int = 1) -> Dict[str, Any]:
        """
        미완료 결과들의 가격 및 수익률 업데이트

        스케줄러에서 주기적으로 호출하여 결과를 업데이트합니다.
        각 신호의 발생 시간을 기준으로 경과 시간을 계산하고,
        해당 시간대에 맞는 가격을 수집하여 수익률을 계산합니다.

        Args:
            hours_old: 몇 시간 이상 된 것만 업데이트 (기본: 1시간)

        Returns:
            업데이트 결과 통계
            {
                'updated': 업데이트된 결과 개수,
                'errors': 오류 발생 개수,
                'completed': 완료된 결과 개수,
                'total_processed': 처리된 총 개수
            }

        Note:
            스케줄러에서 주기적으로 호출하여 결과를 업데이트합니다.
            - 1시간마다 실행 권장
            - 너무 최근 신호는 제외 (가격 변화 시간 확보)
        """
        session, outcome_repo, signal_repo = self._get_session_and_repositories()

        try:
            # 1. 미완료 결과들 조회
            incomplete_outcomes = outcome_repo.find_incomplete_outcomes(hours_old)
            if not incomplete_outcomes:
                print("ℹ️ 업데이트할 미완료 결과 없음")
                return {"updated": 0, "errors": 0, "completed": 0, "total_processed": 0}

            print(f"🔄 {len(incomplete_outcomes)}개의 미완료 결과 업데이트 시작")

            updated_count = 0
            error_count = 0
            completed_count = 0

            # 2. 각 결과 업데이트
            for outcome in incomplete_outcomes:
                try:
                    # 원본 신호 조회
                    signal = signal_repo.find_by_id(outcome.signal_id)
                    if not signal:
                        print(f"⚠️ 원본 신호를 찾을 수 없음: ID {outcome.signal_id}")
                        error_count += 1
                        continue

                    # 현재 시간과 신호 발생 시간의 차이 계산
                    now = datetime.utcnow()
                    elapsed_hours = (now - signal.triggered_at).total_seconds() / 3600

                    print(
                        f"   📊 신호 ID {outcome.signal_id} 처리 중 (경과: {elapsed_hours:.1f}시간)"
                    )

                    # 3. 너무 오래된 신호는 강제 완료 처리 (60일 = 2개월)
                    if elapsed_hours >= 60 * 24:  # 2개월 이상
                        outcome_repo.mark_as_complete(outcome.id)
                        completed_count += 1
                        print(
                            f"   ⏰ 오래된 신호 강제 완료: 신호 ID {outcome.signal_id} (경과: {elapsed_hours:.1f}시간)"
                        )
                        continue  # 더 이상 처리하지 않음

                    # 4. 시간대별 가격 업데이트
                    updated = self._update_outcome_prices(
                        outcome, signal, elapsed_hours
                    )
                    if updated:
                        updated_count += 1
                        print(f"   ✅ 가격 업데이트 완료: {signal.signal_type}")

                    # 5. 수익률 계산
                    outcome_repo.calculate_and_update_returns(outcome.id)

                    # 6. 추적 완료 여부 확인 (정상 완료)
                    if elapsed_hours >= 30 * 24:  # 1개월 (30일)
                        completed_count += 1
                        print(f"   🎯 정상 추적 완료: 신호 ID {outcome.signal_id}")

                except Exception as e:
                    print(f"❌ 결과 업데이트 실패: 결과 ID {outcome.id} - {e}")
                    error_count += 1

            session.commit()

            print(f"✅ 결과 업데이트 완료:")
            print(f"   - 업데이트: {updated_count}개")
            print(f"   - 완료: {completed_count}개")
            print(f"   - 오류: {error_count}개")
            print(f"   - 총 처리: {len(incomplete_outcomes)}개")

            return {
                "updated": updated_count,
                "errors": error_count,
                "completed": completed_count,
                "total_processed": len(incomplete_outcomes),
            }

        except Exception as e:
            session.rollback()
            print(f"❌ 결과 업데이트 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    def _update_outcome_prices(
        self, outcome: SignalOutcome, signal: TechnicalSignal, elapsed_hours: float
    ) -> bool:
        """
        결과의 시간대별 가격 업데이트

        경과 시간에 따라 해당하는 시간대의 가격을 업데이트합니다.
        예를 들어, 1시간이 경과했으면 price_1h_after를 업데이트하고,
        4시간이 경과했으면 price_4h_after를 업데이트합니다.

        Args:
            outcome: 결과 레코드
            signal: 원본 신호
            elapsed_hours: 경과 시간 (시간)

        Returns:
            업데이트 성공 여부

        Note:
            각 시간대별로 한 번만 업데이트됩니다.
            이미 업데이트된 시간대는 건너뜁니다.
        """
        # 현재 가격 조회 (캐시 무시하여 정확한 현재 가격 획득)
        current_price = self.yahoo_client.get_latest_minute_price(
            signal.symbol, ignore_cache=True
        )
        if current_price is None:
            print(f"⚠️ 현재 가격 조회 실패: {signal.symbol}")
            return False

        # 시간대별 가격 업데이트 (아직 업데이트되지 않은 것만)
        price_updates = {}

        # 1시간 후 가격 (1시간 경과 && 아직 업데이트 안됨)
        if elapsed_hours >= 1 and outcome.price_1h_after is None:
            price_updates["price_1h"] = current_price
            print(f"   📈 1시간 후 가격 업데이트: ${current_price:.2f}")

        # 4시간 후 가격 (4시간 경과 && 아직 업데이트 안됨)
        if elapsed_hours >= 4 and outcome.price_4h_after is None:
            price_updates["price_4h"] = current_price
            print(f"   📈 4시간 후 가격 업데이트: ${current_price:.2f}")

        # 1일 후 가격 (24시간 경과 && 아직 업데이트 안됨)
        if elapsed_hours >= 24 and outcome.price_1d_after is None:
            price_updates["price_1d"] = current_price
            print(f"   📈 1일 후 가격 업데이트: ${current_price:.2f}")

        # 1주일 후 가격 (7일 경과 && 아직 업데이트 안됨)
        if elapsed_hours >= 7 * 24 and outcome.price_1w_after is None:
            price_updates["price_1w"] = current_price
            print(f"   📈 1주일 후 가격 업데이트: ${current_price:.2f}")

        # 1개월 후 가격 (30일 경과 && 아직 업데이트 안됨)
        if elapsed_hours >= 30 * 24 and outcome.price_1m_after is None:
            price_updates["price_1m"] = current_price
            print(f"   📈 1개월 후 가격 업데이트: ${current_price:.2f}")

        # 가격 업데이트 실행
        if price_updates:
            success = self.outcome_repository.update_outcome_prices(
                outcome_id=outcome.id,
                price_1h=price_updates.get("price_1h"),
                price_4h=price_updates.get("price_4h"),
                price_1d=price_updates.get("price_1d"),
                price_1w=price_updates.get("price_1w"),
                price_1m=price_updates.get("price_1m"),
            )
            return success

        return False

    # =================================================================
    # 결과 조회 및 분석
    # =================================================================

    def get_signal_outcome(self, signal_id: int) -> Dict[str, Any]:
        """
        특정 신호의 결과 조회

        신호 발생 후 현재까지 수집된 모든 결과 데이터를 조회합니다.
        시간대별 가격, 수익률, 성공 여부 등을 포함합니다.

        Args:
            signal_id: 신호 ID

        Returns:
            신호 결과 데이터
            {
                'signal': 원본 신호 정보,
                'outcome': 결과 데이터 (가격, 수익률 등),
                'analysis': 추가 분석 정보,
                'tracking_status': 추적 상태
            }
        """
        session, outcome_repo, signal_repo = self._get_session_and_repositories()

        try:
            # 1. 신호 조회
            signal = signal_repo.find_by_id(signal_id)
            if not signal:
                return {"error": f"신호를 찾을 수 없음: ID {signal_id}"}

            # 2. 결과 조회
            outcome = outcome_repo.find_by_signal_id(signal_id)
            if not outcome:
                return {
                    "signal": signal.to_dict(),
                    "outcome": None,
                    "message": "아직 결과 추적이 시작되지 않았습니다.",
                    "tracking_status": "미시작",
                }

            # 3. 결과 데이터 구성
            outcome_data = outcome.to_dict()

            # 4. 추가 분석 정보
            analysis = self._analyze_outcome(outcome, signal)

            # 5. 추적 상태 판정
            tracking_status = self._determine_tracking_status(outcome, signal)

            return {
                "signal": signal.to_dict(),
                "outcome": outcome_data,
                "analysis": analysis,
                "tracking_status": tracking_status,
            }

        except Exception as e:
            print(f"❌ 신호 결과 조회 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    def _analyze_outcome(
        self, outcome: SignalOutcome, signal: TechnicalSignal
    ) -> Dict[str, Any]:
        """
        결과 분석 정보 생성

        수집된 결과 데이터를 바탕으로 추가적인 분석 정보를 생성합니다.
        성공 여부, 수익률 요약, 경과 시간 등을 포함합니다.

        Args:
            outcome: 결과 레코드
            signal: 원본 신호

        Returns:
            분석 정보
        """
        analysis = {
            "success_summary": {},
            "return_summary": {},
            "elapsed_time": {},
            "signal_direction": {},
            "performance_grade": None,
        }

        # 1. 성공 여부 요약
        for timeframe in ["1d", "1w", "1m"]:
            success_attr = f"is_successful_{timeframe}"
            if (
                hasattr(outcome, success_attr)
                and getattr(outcome, success_attr) is not None
            ):
                analysis["success_summary"][timeframe] = getattr(outcome, success_attr)

        # 2. 수익률 요약
        for timeframe in ["1h", "4h", "1d", "1w", "1m"]:
            return_attr = f"return_{timeframe}"
            if (
                hasattr(outcome, return_attr)
                and getattr(outcome, return_attr) is not None
            ):
                analysis["return_summary"][timeframe] = float(
                    getattr(outcome, return_attr)
                )

        # 3. 경과 시간 계산
        now = datetime.utcnow()
        elapsed_seconds = (now - signal.triggered_at).total_seconds()

        analysis["elapsed_time"] = {
            "hours": elapsed_seconds / 3600,
            "days": elapsed_seconds / (3600 * 24),
            "signal_time": signal.triggered_at.isoformat(),
            "current_time": now.isoformat(),
            "is_complete": outcome.is_complete,
        }

        # 4. 신호 방향 분석
        signal_type = signal.signal_type.lower()
        is_bullish = any(
            keyword in signal_type
            for keyword in [
                "breakout_up",
                "golden_cross",
                "oversold",
                "bullish",
                "touch_lower",
            ]
        )

        analysis["signal_direction"] = {
            "is_bullish": is_bullish,
            "expected_direction": "상승" if is_bullish else "하락",
            "signal_type": signal.signal_type,
        }

        # 5. 성과 등급 계산 (1일 기준)
        if outcome.return_1d is not None:
            return_1d = float(outcome.return_1d)
            if return_1d > 5:
                grade = "A"
            elif return_1d > 2:
                grade = "B"
            elif return_1d > 0:
                grade = "C"
            elif return_1d > -2:
                grade = "D"
            else:
                grade = "F"

            analysis["performance_grade"] = {
                "grade": grade,
                "return_1d": return_1d,
                "description": self._get_grade_description(grade, return_1d),
            }

        return analysis

    def _determine_tracking_status(
        self, outcome: SignalOutcome, signal: TechnicalSignal
    ) -> str:
        """
        추적 상태 판정

        Args:
            outcome: 결과 레코드
            signal: 원본 신호

        Returns:
            추적 상태 문자열
        """
        if outcome.is_complete:
            return "완료"

        now = datetime.utcnow()
        elapsed_hours = (now - signal.triggered_at).total_seconds() / 3600

        if elapsed_hours < 1:
            return "대기 중 (1시간 미만)"
        elif elapsed_hours < 24:
            return "진행 중 (1일 미만)"
        elif elapsed_hours < 7 * 24:
            return "진행 중 (1주 미만)"
        elif elapsed_hours < 30 * 24:
            return "진행 중 (1개월 미만)"
        else:
            return "완료 예정"

    def _get_grade_description(self, grade: str, return_pct: float) -> str:
        """성과 등급 설명 생성"""
        descriptions = {
            "A": f"우수한 성과 (+{return_pct:.1f}%)",
            "B": f"좋은 성과 (+{return_pct:.1f}%)",
            "C": f"보통 성과 (+{return_pct:.1f}%)",
            "D": f"약간 손실 ({return_pct:.1f}%)",
            "F": f"큰 손실 ({return_pct:.1f}%)",
        }
        return descriptions.get(grade, f"성과: {return_pct:.1f}%")

    # =================================================================
    # 테스트 및 디버깅 메서드
    # =================================================================

    def test_outcome_tracking(self, signal_id: int) -> Dict[str, Any]:
        """
        결과 추적 테스트 (개발용)

        실제 시간 경과를 기다리지 않고 가상의 가격 데이터를 생성하여
        결과 추적 시스템이 정상 동작하는지 확인합니다.

        Args:
            signal_id: 테스트할 신호 ID

        Returns:
            테스트 결과
        """
        session, outcome_repo, signal_repo = self._get_session_and_repositories()

        try:
            # 1. 신호 조회
            signal = signal_repo.find_by_id(signal_id)
            if not signal:
                return {"error": f"신호를 찾을 수 없음: ID {signal_id}"}

            print(f"🧪 신호 ID {signal_id} 결과 추적 테스트 시작")
            print(f"   - 신호 타입: {signal.signal_type}")
            print(f"   - 심볼: {signal.symbol}")
            print(f"   - 원본 가격: ${signal.current_price}")

            # 2. 기존 결과 삭제 (있으면)
            existing_outcome = outcome_repo.find_by_signal_id(signal_id)
            if existing_outcome:
                print(f"🗑️ 기존 결과 삭제: ID {existing_outcome.id}")
                session.delete(existing_outcome)
                session.commit()

            # 3. 새 결과 초기화
            outcome = self.initialize_outcome_tracking(signal_id)
            if not outcome:
                return {"error": "결과 추적 초기화 실패"}

            # 4. 가격 데이터 생성 (테스트용 가짜 데이터)
            original_price = float(signal.current_price)

            # 신호 타입에 따라 다른 가격 변화 시뮬레이션
            is_bullish = any(
                keyword in signal.signal_type.lower()
                for keyword in ["breakout_up", "golden_cross", "oversold", "bullish"]
            )

            if is_bullish:
                # 상승 신호는 점진적으로 상승하는 가격
                price_1h = original_price * 1.005  # +0.5%
                price_4h = original_price * 1.01  # +1.0%
                price_1d = original_price * 1.02  # +2.0%
                price_1w = original_price * 1.05  # +5.0%
                price_1m = original_price * 1.10  # +10.0%
                print(f"   📈 상승 신호 시뮬레이션 (예상 상승)")
            else:
                # 하락 신호는 점진적으로 하락하는 가격
                price_1h = original_price * 0.995  # -0.5%
                price_4h = original_price * 0.99  # -1.0%
                price_1d = original_price * 0.98  # -2.0%
                price_1w = original_price * 0.95  # -5.0%
                price_1m = original_price * 0.90  # -10.0%
                print(f"   📉 하락 신호 시뮬레이션 (예상 하락)")

            # 5. 가격 업데이트
            print(f"   💾 가격 데이터 업데이트 중...")
            outcome_repo.update_outcome_prices(
                outcome_id=outcome.id,
                price_1h=price_1h,
                price_4h=price_4h,
                price_1d=price_1d,
                price_1w=price_1w,
                price_1m=price_1m,
            )

            # 6. 수익률 계산
            print(f"   🧮 수익률 계산 중...")
            outcome_repo.calculate_and_update_returns(outcome.id)

            # 7. 완료 표시
            session.query(SignalOutcome).filter(SignalOutcome.id == outcome.id).update(
                {
                    SignalOutcome.is_complete: True,
                    SignalOutcome.last_updated_at: datetime.utcnow(),
                }
            )

            session.commit()

            # 8. 결과 조회
            updated_outcome = outcome_repo.find_by_signal_id(signal_id)

            print(f"✅ 테스트 결과 추적 완료: 신호 ID {signal_id}")
            print(
                f"   - 1시간 후: ${price_1h:.2f} ({((price_1h-original_price)/original_price*100):+.1f}%)"
            )
            print(
                f"   - 4시간 후: ${price_4h:.2f} ({((price_4h-original_price)/original_price*100):+.1f}%)"
            )
            print(
                f"   - 1일 후: ${price_1d:.2f} ({((price_1d-original_price)/original_price*100):+.1f}%)"
            )
            print(
                f"   - 1주 후: ${price_1w:.2f} ({((price_1w-original_price)/original_price*100):+.1f}%)"
            )
            print(
                f"   - 1개월 후: ${price_1m:.2f} ({((price_1m-original_price)/original_price*100):+.1f}%)"
            )

            return {
                "signal": signal.to_dict(),
                "outcome": updated_outcome.to_dict() if updated_outcome else None,
                "test_data": {
                    "original_price": original_price,
                    "price_1h": price_1h,
                    "price_4h": price_4h,
                    "price_1d": price_1d,
                    "price_1w": price_1w,
                    "price_1m": price_1m,
                    "is_bullish": is_bullish,
                    "expected_direction": "상승" if is_bullish else "하락",
                },
                "analysis": (
                    self._analyze_outcome(updated_outcome, signal)
                    if updated_outcome
                    else None
                ),
            }

        except Exception as e:
            session.rollback()
            print(f"❌ 테스트 결과 추적 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    def get_tracking_statistics(self) -> Dict[str, Any]:
        """
        결과 추적 통계 조회

        현재 추적 중인 신호들의 상태를 요약하여 제공합니다.

        Returns:
            추적 통계 정보
        """
        session, outcome_repo, signal_repo = self._get_session_and_repositories()

        try:
            # 전체 결과 레코드 수
            total_outcomes = session.query(SignalOutcome).count()

            # 완료된 결과 수
            completed_outcomes = (
                session.query(SignalOutcome)
                .filter(SignalOutcome.is_complete == True)
                .count()
            )

            # 진행 중인 결과 수
            in_progress_outcomes = total_outcomes - completed_outcomes

            # 최근 24시간 내 생성된 결과 수
            yesterday = datetime.utcnow() - timedelta(hours=24)
            recent_outcomes = (
                session.query(SignalOutcome)
                .filter(SignalOutcome.created_at >= yesterday)
                .count()
            )

            return {
                "total_tracking": total_outcomes,
                "completed": completed_outcomes,
                "in_progress": in_progress_outcomes,
                "recent_24h": recent_outcomes,
                "completion_rate": (
                    completed_outcomes / total_outcomes if total_outcomes > 0 else 0
                ),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            print(f"❌ 추적 통계 조회 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    def __del__(self):
        """소멸자 - 세션 정리"""
        if self.session:
            self.session.close()
