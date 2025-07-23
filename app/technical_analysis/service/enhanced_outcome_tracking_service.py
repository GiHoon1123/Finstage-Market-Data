"""
향상된 신호 결과 추적 서비스

이 파일은 기술적 신호가 발생한 후의 결과를 추적하는 서비스입니다.
초등학생도 이해할 수 있도록 매우 자세한 주석을 달았습니다.

🎯 이 서비스가 하는 일:
1. 기술적 신호가 발생하면 → 결과 추적을 시작합니다
2. 시간이 지나면서 → 주가가 어떻게 변했는지 확인합니다
3. 수익률을 계산해서 → 그 신호가 좋았는지 나빴는지 판단합니다
4. 데이터를 저장해서 → 나중에 분석할 수 있게 합니다

🔍 예시로 설명하면:
- 나스닥이 20일선을 돌파했다는 신호가 발생
- 1시간 후, 4시간 후, 1일 후... 가격을 계속 확인
- 가격이 올랐으면 "좋은 신호", 떨어졌으면 "나쁜 신호"로 기록
- 이런 데이터가 쌓이면 어떤 신호가 믿을만한지 알 수 있음
"""

# 필요한 라이브러리들을 가져옵니다 (import)
from typing import List, Optional, Dict, Any, Tuple  # 타입 힌트용
from datetime import datetime, timedelta  # 날짜와 시간 계산용
from sqlalchemy.orm import Session  # 데이터베이스 연결용
from app.common.infra.database.config.database_config import (
    SessionLocal,
)  # 데이터베이스 세션
from app.common.infra.client.yahoo_price_client import (
    YahooPriceClient,
)  # 주가 데이터 가져오기용
from app.technical_analysis.infra.model.repository.signal_outcome_repository import (
    SignalOutcomeRepository,
)  # 결과 데이터 저장/조회용
from app.technical_analysis.infra.model.repository.technical_signal_repository import (
    TechnicalSignalRepository,
)  # 신호 데이터 조회용
from app.technical_analysis.infra.model.entity.signal_outcomes import (
    SignalOutcome,
)  # 결과 데이터 구조
from app.technical_analysis.infra.model.entity.technical_signals import (
    TechnicalSignal,
)  # 신호 데이터 구조


class EnhancedOutcomeTrackingService:
    """
    향상된 신호 결과 추적 서비스 클래스

    이 클래스는 기술적 신호의 결과를 추적하는 모든 기능을 담고 있습니다.
    마치 학생이 시험 점수를 기록하고 분석하는 것처럼,
    투자 신호의 성과를 기록하고 분석합니다.
    """

    def __init__(self):
        """
        서비스를 초기화합니다 (생성자)

        🏗️ 여기서 하는 일:
        - 데이터베이스 연결 준비 (아직 연결하지는 않음)
        - 주가 데이터를 가져올 클라이언트 준비
        - 필요한 도구들을 준비해둠

        💡 왜 None으로 초기화하나요?
        - 메모리를 절약하기 위해서입니다
        - 실제로 사용할 때만 데이터베이스에 연결합니다
        """
        # 데이터베이스 관련 변수들을 None으로 초기화
        self.session: Optional[Session] = None  # 데이터베이스 연결 (아직 없음)
        self.outcome_repository: Optional[SignalOutcomeRepository] = (
            None  # 결과 데이터 관리자 (아직 없음)
        )
        self.signal_repository: Optional[TechnicalSignalRepository] = (
            None  # 신호 데이터 관리자 (아직 없음)
        )

        # 주가 데이터를 가져오는 클라이언트는 바로 생성
        self.yahoo_client = YahooPriceClient()  # 야후 파이낸스에서 주가 데이터 가져오기

    def _get_session_and_repositories(self):
        """
        데이터베이스 연결과 리포지토리들을 준비합니다 (지연 초기화)

        🔧 이 함수가 하는 일:
        1. 데이터베이스에 연결합니다
        2. 데이터를 저장/조회할 도구들을 준비합니다
        3. 준비된 도구들을 반환합니다

        💡 왜 지연 초기화를 하나요?
        - 서비스를 만들 때마다 데이터베이스에 연결하면 비효율적
        - 실제로 사용할 때만 연결해서 자원을 절약

        Returns:
            tuple: (세션, 결과_리포지토리, 신호_리포지토리)
        """
        # 아직 데이터베이스에 연결하지 않았다면 연결합니다
        if not self.session:
            print("🔌 데이터베이스에 연결 중...")

            # 데이터베이스 세션 생성 (연결)
            self.session = SessionLocal()

            # 결과 데이터를 관리할 리포지토리 생성
            self.outcome_repository = SignalOutcomeRepository(self.session)

            # 신호 데이터를 관리할 리포지토리 생성
            self.signal_repository = TechnicalSignalRepository(self.session)

            print("✅ 데이터베이스 연결 완료!")

        # 준비된 도구들을 반환
        return self.session, self.outcome_repository, self.signal_repository

    def initialize_outcome_tracking(self, signal_id: int) -> Optional[SignalOutcome]:
        """
        신호에 대한 결과 추적을 시작합니다

        🎯 이 함수가 하는 일:
        1. 새로운 신호가 발생했을 때 호출됩니다
        2. 그 신호의 결과를 추적하기 위한 빈 레코드를 만듭니다
        3. 나중에 이 레코드에 실제 결과를 채워넣습니다

        📝 예시:
        - 나스닥이 50일선을 돌파했다는 신호 발생 (signal_id = 12345)
        - 이 함수를 호출: initialize_outcome_tracking(12345)
        - 빈 결과 레코드가 생성됨 (가격들은 모두 NULL)
        - 시간이 지나면서 실제 가격들이 채워짐

        Args:
            signal_id (int): 추적할 신호의 ID 번호

        Returns:
            SignalOutcome: 생성된 결과 추적 레코드 (실패시 None)
        """
        print(f"🎯 신호 ID {signal_id}의 결과 추적을 시작합니다...")

        # 데이터베이스 연결과 도구들을 준비
        session, outcome_repo, signal_repo = self._get_session_and_repositories()

        try:
            # 1단계: 해당 신호가 실제로 존재하는지 확인
            print(f"🔍 신호 ID {signal_id}가 존재하는지 확인 중...")
            signal = signal_repo.find_by_id(signal_id)

            if not signal:
                print(f"❌ 신호를 찾을 수 없습니다: ID {signal_id}")
                return None

            print(f"✅ 신호 발견: {signal.signal_type} ({signal.symbol})")

            # 2단계: 이미 결과 추적이 시작되었는지 확인
            print(f"🔍 이미 추적 중인지 확인 중...")
            existing_outcome = outcome_repo.find_by_signal_id(signal_id)

            if existing_outcome:
                print(f"⚠️ 이미 결과 추적 중입니다: 신호 ID {signal_id}")
                return existing_outcome

            # 3단계: 새로운 결과 추적 레코드 생성
            print(f"📝 새로운 결과 추적 레코드를 생성 중...")
            outcome = outcome_repo.create_outcome_record(signal_id)

            # 데이터베이스에 저장
            session.commit()
            print(f"💾 데이터베이스에 저장 완료!")

            # 성공 메시지 출력
            print(f"🎉 결과 추적 초기화 완료!")
            print(f"   📊 신호 타입: {signal.signal_type}")
            print(f"   📈 심볼: {signal.symbol}")
            print(f"   🕐 발생 시간: {signal.triggered_at}")
            print(f"   💰 원본 가격: ${signal.current_price}")

            return outcome

        except Exception as e:
            # 오류가 발생하면 변경사항을 취소
            session.rollback()
            print(f"❌ 결과 추적 초기화 실패: {e}")
            return None

        finally:
            # 함수가 끝나면 데이터베이스 연결을 닫습니다
            if session:
                session.close()
                print(f"🔌 데이터베이스 연결을 닫았습니다")

    def update_outcomes_with_detailed_logging(
        self, hours_old: int = 1
    ) -> Dict[str, Any]:
        """
        미완료 결과들의 가격 및 수익률을 업데이트합니다 (자세한 로깅 포함)

        🔄 이 함수가 하는 일:
        1. 아직 완료되지 않은 결과 추적들을 찾습니다
        2. 각각에 대해 현재 가격을 확인합니다
        3. 시간대별로 가격을 기록합니다 (1시간 후, 4시간 후, 1일 후...)
        4. 수익률을 계산합니다

        📚 예시로 설명:
        - 어제 오후 2시에 "나스닥 50일선 돌파" 신호 발생
        - 지금은 오늘 오후 3시 (25시간 경과)
        - 1시간 후, 4시간 후, 1일 후 가격을 모두 기록
        - 각 시점의 수익률을 계산해서 저장

        Args:
            hours_old (int): 몇 시간 이상 된 신호만 업데이트할지 (기본: 1시간)

        Returns:
            Dict[str, Any]: 업데이트 결과 통계
            {
                'updated': 업데이트된 결과 개수,
                'errors': 오류 발생 개수,
                'completed': 완료된 결과 개수,
                'total_processed': 처리된 총 개수
            }
        """
        print(f"🔄 결과 추적 업데이트를 시작합니다...")
        print(f"📅 {hours_old}시간 이상 된 신호들을 대상으로 합니다")

        # 데이터베이스 연결과 도구들을 준비
        session, outcome_repo, signal_repo = self._get_session_and_repositories()

        try:
            # 1단계: 업데이트가 필요한 미완료 결과들을 찾습니다
            print(f"🔍 미완료 결과들을 검색 중...")
            incomplete_outcomes = outcome_repo.find_incomplete_outcomes(hours_old)

            if not incomplete_outcomes:
                print("ℹ️ 업데이트할 미완료 결과가 없습니다")
                return {"updated": 0, "errors": 0, "completed": 0, "total_processed": 0}

            print(f"📊 총 {len(incomplete_outcomes)}개의 미완료 결과를 발견했습니다")

            # 결과 통계를 위한 변수들
            updated_count = 0  # 성공적으로 업데이트된 개수
            error_count = 0  # 오류가 발생한 개수
            completed_count = 0  # 완전히 완료된 개수

            # 2단계: 각 결과를 하나씩 업데이트합니다
            for i, outcome in enumerate(incomplete_outcomes, 1):
                print(
                    f"\n📋 [{i}/{len(incomplete_outcomes)}] 신호 ID {outcome.signal_id} 처리 중..."
                )

                try:
                    # 원본 신호 정보를 가져옵니다
                    signal = signal_repo.find_by_id(outcome.signal_id)
                    if not signal:
                        print(f"⚠️ 원본 신호를 찾을 수 없습니다: ID {outcome.signal_id}")
                        error_count += 1
                        continue

                    # 신호 발생 후 경과 시간을 계산합니다
                    now = datetime.utcnow()  # 현재 시간 (UTC)
                    elapsed_hours = (
                        now - signal.triggered_at
                    ).total_seconds() / 3600  # 경과 시간 (시간 단위)

                    print(f"   ⏰ 신호 발생: {signal.triggered_at}")
                    print(f"   ⏰ 현재 시간: {now}")
                    print(f"   ⏰ 경과 시간: {elapsed_hours:.1f}시간")
                    print(f"   📊 신호 타입: {signal.signal_type}")
                    print(f"   📈 심볼: {signal.symbol}")

                    # 3단계: 시간대별 가격을 업데이트합니다
                    updated = self._update_outcome_prices_with_logging(
                        outcome, signal, elapsed_hours
                    )

                    if updated:
                        updated_count += 1
                        print(f"   ✅ 가격 업데이트 완료!")
                    else:
                        print(f"   ⏭️ 업데이트할 가격이 없습니다")

                    # 4단계: 수익률을 계산합니다
                    print(f"   🧮 수익률 계산 중...")
                    outcome_repo.calculate_and_update_returns(outcome.id)
                    print(f"   ✅ 수익률 계산 완료!")

                    # 5단계: 추적이 완료되었는지 확인합니다
                    if elapsed_hours >= 30 * 24:  # 30일 = 720시간
                        completed_count += 1
                        print(f"   🏁 추적 완료! (30일 경과)")

                except Exception as e:
                    error_count += 1
                    print(f"   ❌ 처리 실패: {e}")
                    continue

            # 최종 결과를 출력합니다
            print(f"\n🎉 결과 추적 업데이트 완료!")
            print(f"   ✅ 성공: {updated_count}개")
            print(f"   ❌ 실패: {error_count}개")
            print(f"   🏁 완료: {completed_count}개")
            print(f"   📊 총 처리: {len(incomplete_outcomes)}개")

            return {
                "updated": updated_count,
                "errors": error_count,
                "completed": completed_count,
                "total_processed": len(incomplete_outcomes),
            }

        except Exception as e:
            print(f"❌ 전체 업데이트 과정에서 오류 발생: {e}")
            return {"error": str(e)}

        finally:
            # 함수가 끝나면 데이터베이스 연결을 닫습니다
            if session:
                session.close()
                print(f"🔌 데이터베이스 연결을 닫았습니다")

    def _update_outcome_prices_with_logging(
        self, outcome: SignalOutcome, signal: TechnicalSignal, elapsed_hours: float
    ) -> bool:
        """
        특정 결과의 가격들을 시간대별로 업데이트합니다 (자세한 로깅 포함)

        🎯 이 함수가 하는 일:
        1. 경과 시간을 확인해서 어떤 시간대를 업데이트할지 결정
        2. 해당 시간대의 현재 가격을 가져옴
        3. 데이터베이스에 저장

        ⏰ 시간대별 업데이트 기준:
        - 1시간 후: 1시간 이상 경과시
        - 4시간 후: 4시간 이상 경과시
        - 1일 후: 24시간 이상 경과시
        - 1주일 후: 168시간(7일) 이상 경과시
        - 1개월 후: 720시간(30일) 이상 경과시

        Args:
            outcome (SignalOutcome): 업데이트할 결과 레코드
            signal (TechnicalSignal): 원본 신호 정보
            elapsed_hours (float): 신호 발생 후 경과 시간 (시간 단위)

        Returns:
            bool: 업데이트가 수행되었으면 True, 아니면 False
        """
        print(f"      🔍 시간대별 가격 업데이트 확인 중...")

        updated = False  # 업데이트 여부를 추적하는 변수

        try:
            # 현재 가격을 가져옵니다 (최신 1분봉 가격 사용)
            print(f"      📡 {signal.symbol}의 현재 가격을 가져오는 중...")

            # 최대 3번 재시도 로직 추가
            retry_count = 0
            max_retries = 3
            current_price = None

            while retry_count < max_retries and current_price is None:
                if retry_count > 0:
                    print(f"      🔄 재시도 {retry_count}/{max_retries}...")
                    # 재시도 간 짧은 대기 시간 추가
                    import time

                    time.sleep(1)

                current_price = self.yahoo_client.get_latest_minute_price(signal.symbol)
                retry_count += 1

            if not current_price:
                print(
                    f"      ❌ 현재 가격을 가져올 수 없습니다 (최대 재시도 횟수 초과)"
                )
                # 가격을 가져올 수 없는 경우, 원본 신호의 가격을 대체값으로 사용
                if signal.current_price:
                    print(
                        f"      ⚠️ 원본 신호의 가격을 대체값으로 사용: ${signal.current_price:.2f}"
                    )
                    current_price = signal.current_price
                else:
                    print(f"      ❌ 대체 가격도 없음, 업데이트 건너뜀")
                    return False

            print(f"      💰 현재 가격: ${current_price:.2f}")

            # 1시간 후 가격 업데이트 (1시간 이상 경과 & 아직 기록되지 않음)
            if elapsed_hours >= 1.0 and outcome.price_1h_after is None:
                print(f"      ⏰ 1시간 후 가격 업데이트: ${current_price:.2f}")
                outcome.price_1h_after = current_price
                updated = True

            # 4시간 후 가격 업데이트 (4시간 이상 경과 & 아직 기록되지 않음)
            if elapsed_hours >= 4.0 and outcome.price_4h_after is None:
                print(f"      ⏰ 4시간 후 가격 업데이트: ${current_price:.2f}")
                outcome.price_4h_after = current_price
                updated = True

            # 1일 후 가격 업데이트 (24시간 이상 경과 & 아직 기록되지 않음)
            if elapsed_hours >= 24.0 and outcome.price_1d_after is None:
                print(f"      ⏰ 1일 후 가격 업데이트: ${current_price:.2f}")
                outcome.price_1d_after = current_price
                updated = True

            # 1주일 후 가격 업데이트 (168시간 이상 경과 & 아직 기록되지 않음)
            if elapsed_hours >= 168.0 and outcome.price_1w_after is None:
                print(f"      ⏰ 1주일 후 가격 업데이트: ${current_price:.2f}")
                outcome.price_1w_after = current_price
                updated = True

            # 1개월 후 가격 업데이트 (720시간 이상 경과 & 아직 기록되지 않음)
            if elapsed_hours >= 720.0 and outcome.price_1m_after is None:
                print(f"      ⏰ 1개월 후 가격 업데이트: ${current_price:.2f}")
                outcome.price_1m_after = current_price
                outcome.is_complete = True  # 추적 완료 표시
                updated = True
                print(f"      🏁 모든 시간대 추적 완료!")

            # 업데이트된 내용이 있으면 데이터베이스에 저장
            if updated:
                print(f"      💾 변경사항을 데이터베이스에 저장 중...")
                # 세션은 이미 _get_session_and_repositories()에서 가져온 것을 사용
                # commit은 상위 함수에서 처리
            else:
                print(f"      ℹ️ 업데이트할 시간대가 없습니다")

            return updated

        except Exception as e:
            print(f"      ❌ 가격 업데이트 실패: {e}")
            return False

    def get_tracking_summary(self) -> Dict[str, Any]:
        """
        현재 추적 상황의 요약 정보를 제공합니다

        📊 이 함수가 제공하는 정보:
        1. 전체 추적 중인 신호 개수
        2. 완료된 추적 개수
        3. 미완료 추적 개수
        4. 최근 업데이트 시간
        5. 각 시간대별 데이터 수집 현황

        Returns:
            Dict[str, Any]: 추적 상황 요약 정보
        """
        print(f"📊 추적 상황 요약 정보를 생성 중...")

        # 데이터베이스 연결과 도구들을 준비
        session, outcome_repo, signal_repo = self._get_session_and_repositories()

        try:
            # 전체 통계 수집
            total_outcomes = outcome_repo.count_all_outcomes()
            completed_outcomes = outcome_repo.count_completed_outcomes()
            incomplete_outcomes = len(outcome_repo.find_incomplete_outcomes(0))

            # 시간대별 데이터 수집 현황
            price_1h_count = outcome_repo.count_outcomes_with_price_1h()
            price_4h_count = outcome_repo.count_outcomes_with_price_4h()
            price_1d_count = outcome_repo.count_outcomes_with_price_1d()
            price_1w_count = outcome_repo.count_outcomes_with_price_1w()
            price_1m_count = outcome_repo.count_outcomes_with_price_1m()

            summary = {
                "총_추적_개수": total_outcomes,
                "완료된_추적": completed_outcomes,
                "미완료_추적": incomplete_outcomes,
                "완료율": (
                    round((completed_outcomes / total_outcomes * 100), 2)
                    if total_outcomes > 0
                    else 0
                ),
                "시간대별_데이터_수집현황": {
                    "1시간_후": price_1h_count,
                    "4시간_후": price_4h_count,
                    "1일_후": price_1d_count,
                    "1주일_후": price_1w_count,
                    "1개월_후": price_1m_count,
                },
                "생성_시간": datetime.utcnow().isoformat(),
            }

            print(f"✅ 추적 상황 요약 완료!")
            print(f"   📊 총 추적: {total_outcomes}개")
            print(f"   ✅ 완료: {completed_outcomes}개")
            print(f"   🔄 진행중: {incomplete_outcomes}개")
            print(f"   📈 완료율: {summary['완료율']}%")

            return summary

        except Exception as e:
            print(f"❌ 추적 상황 요약 생성 실패: {e}")
            return {"error": str(e)}

        finally:
            # 함수가 끝나면 데이터베이스 연결을 닫습니다
            if session:
                session.close()

    def __del__(self):
        """
        서비스가 삭제될 때 호출되는 소멸자

        🧹 정리 작업:
        - 데이터베이스 연결이 열려있으면 닫습니다
        - 메모리 누수를 방지합니다
        """
        if self.session:
            print(f"🧹 서비스 종료: 데이터베이스 연결을 정리합니다")
            self.session.close()
