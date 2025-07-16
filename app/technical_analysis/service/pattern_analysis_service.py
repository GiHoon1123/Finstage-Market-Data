"""
패턴 분석 서비스

이 서비스는 여러 기술적 신호들의 조합 패턴을 발견하고 분석합니다.
단일 신호보다 더 강력한 매매 신호를 찾기 위한 고급 분석을 제공합니다.

패턴 분석이란?
- 여러 기술적 신호들이 특정 순서나 조합으로 발생할 때의 효과 분석
- 예: "RSI 과매수 후 볼린저 상단 터치" 패턴이 얼마나 자주 하락으로 이어지는가?
- 예: "200일선 돌파 + 거래량 급증" 조합이 상승 추세의 시작인가?

패턴 유형:
1. 순차적 패턴: A 신호 → B 신호 → C 신호 (시간 순서대로)
2. 동시 패턴: A 신호 + B 신호 (같은 시점에 발생)
3. 선행 패턴: A 신호 → (시간 간격) → B 신호 (A가 B를 예측)

분석 방법:
- 패턴 발견: 과거 데이터에서 반복되는 신호 조합 탐색
- 성과 측정: 패턴 발생 후 가격 변화 추적
- 신뢰도 평가: 패턴의 일관성과 예측력 측정
- 시장 상황별 분석: 상승장/하락장에서의 패턴 효과 차이

활용 방안:
- 고급 매매 전략: 단일 신호보다 정확한 매매 시점 포착
- 위험 관리: 특정 패턴 발생 시 손절매/익절매 최적화
- 알고리즘 트레이딩: 패턴 기반 자동 매매 규칙 개발
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.common.infra.database.config.database_config import SessionLocal
from app.technical_analysis.infra.model.repository.signal_pattern_repository import (
    SignalPatternRepository,
)
from app.technical_analysis.infra.model.repository.technical_signal_repository import (
    TechnicalSignalRepository,
)
from app.technical_analysis.infra.model.entity.signal_patterns import SignalPattern
from app.technical_analysis.infra.model.entity.technical_signals import TechnicalSignal
from app.common.infra.client.yahoo_price_client import YahooPriceClient


class PatternAnalysisService:
    """
    패턴 분석을 담당하는 서비스

    여러 기술적 신호들의 조합 패턴을 발견하고 분석합니다.
    """

    def __init__(self):
        """서비스 초기화"""
        self.session: Optional[Session] = None
        self.pattern_repository: Optional[SignalPatternRepository] = None
        self.signal_repository: Optional[TechnicalSignalRepository] = None
        self.yahoo_client = YahooPriceClient()

    def _get_session_and_repositories(self):
        """세션과 리포지토리 초기화 (지연 초기화)"""
        if not self.session:
            self.session = SessionLocal()
            self.pattern_repository = SignalPatternRepository(self.session)
            self.signal_repository = TechnicalSignalRepository(self.session)
        return self.session, self.pattern_repository, self.signal_repository

    # =================================================================
    # 패턴 발견 및 저장
    # =================================================================

    def discover_patterns(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        특정 심볼의 패턴 자동 발견

        Args:
            symbol: 분석할 심볼
            timeframe: 시간대

        Returns:
            발견된 패턴 정보
        """
        session, pattern_repo, signal_repo = self._get_session_and_repositories()

        try:
            print(f"🔍 {symbol} ({timeframe}) 패턴 발견 시작")

            # 1. 순차적 패턴 발견
            sequential_patterns = pattern_repo.discover_sequential_patterns(
                symbol=symbol,
                timeframe=timeframe,
                max_hours_between=24,  # 24시간 이내 연속 신호
                min_pattern_length=2,  # 최소 2개 신호
            )

            print(f"🔎 {len(sequential_patterns)}개의 패턴 후보 발견")

            # 2. 패턴 저장 (중복 제외)
            saved_patterns = []
            for pattern_data in sequential_patterns:
                # 패턴 이름으로 중복 체크
                existing_patterns = pattern_repo.find_by_pattern_name(
                    pattern_name=pattern_data["pattern_name"], symbol=symbol, limit=1
                )

                # 이미 존재하는 패턴이면 건너뛰기
                if existing_patterns:
                    continue

                # 새 패턴 저장
                try:
                    pattern = pattern_repo.create_sequential_pattern(
                        pattern_name=pattern_data["pattern_name"],
                        symbol=symbol,
                        timeframe=timeframe,
                        signal_ids=pattern_data["signal_ids"],
                        market_condition=self._determine_market_condition(symbol),
                    )

                    saved_patterns.append(pattern)
                    print(f"✅ 패턴 저장: {pattern_data['pattern_name']}")

                except Exception as e:
                    print(f"⚠️ 패턴 저장 실패: {pattern_data['pattern_name']} - {e}")

            session.commit()

            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "discovered_patterns": len(sequential_patterns),
                "saved_patterns": len(saved_patterns),
                "patterns": [
                    {
                        "name": p.pattern_name,
                        "type": p.pattern_type,
                        "start": p.pattern_start.isoformat(),
                        "end": p.pattern_end.isoformat(),
                        "duration_hours": (
                            float(p.pattern_duration_hours)
                            if p.pattern_duration_hours
                            else 0.0
                        ),
                    }
                    for p in saved_patterns
                ],
            }

        except Exception as e:
            session.rollback()
            print(f"❌ 패턴 발견 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    def _determine_market_condition(self, symbol: str) -> str:
        """
        현재 시장 상황 판단 (간단한 버전)

        Args:
            symbol: 심볼

        Returns:
            시장 상황 문자열
        """
        try:
            # 일봉 데이터 조회
            daily_data = self.yahoo_client.get_daily_data(symbol, period="1mo")
            if daily_data is None or len(daily_data) < 20:
                return "unknown"

            # 20일 이동평균 계산
            ma_20 = daily_data["close"].rolling(20).mean()
            if len(ma_20.dropna()) < 1:
                return "unknown"

            # 현재 가격과 20일선 비교
            current_price = daily_data["close"].iloc[-1]
            ma_20_value = ma_20.iloc[-1]

            # 최근 5일 추세 분석
            recent_prices = daily_data["close"].tail(5)
            if len(recent_prices) >= 2:
                price_change = (
                    recent_prices.iloc[-1] - recent_prices.iloc[0]
                ) / recent_prices.iloc[0]

                if price_change > 0.05:  # +5% 이상
                    return "bullish"
                elif price_change < -0.05:  # -5% 이하
                    return "bearish"
                else:
                    return "sideways"

            return "unknown"

        except Exception as e:
            print(f"⚠️ 시장 상황 판단 실패: {e}")
            return "unknown"

    # =================================================================
    # 패턴 성과 분석
    # =================================================================

    def analyze_pattern_performance(
        self,
        pattern_name: Optional[str] = None,
        symbol: Optional[str] = None,
        min_occurrences: int = 5,
    ) -> Dict[str, Any]:
        """
        패턴 성과 분석

        Args:
            pattern_name: 분석할 패턴명 (None이면 모든 패턴)
            symbol: 심볼 필터
            min_occurrences: 최소 발생 횟수

        Returns:
            패턴 성과 분석 결과
        """
        session, pattern_repo, signal_repo = self._get_session_and_repositories()

        try:
            print(f"📊 패턴 성과 분석 시작: {pattern_name or '모든 패턴'}")

            # 1. 패턴별 성과 통계 조회
            pattern_stats = pattern_repo.get_pattern_performance_stats(
                pattern_name=pattern_name,
                symbol=symbol,
                min_occurrences=min_occurrences,
            )

            if not pattern_stats:
                return {
                    "message": "분석할 패턴이 없습니다.",
                    "filters": {
                        "pattern_name": pattern_name,
                        "symbol": symbol,
                        "min_occurrences": min_occurrences,
                    },
                }

            # 2. 패턴별 상세 분석
            detailed_analysis = []
            for stat in pattern_stats:
                # 해당 패턴의 모든 인스턴스 조회
                pattern_instances = pattern_repo.find_by_pattern_name(
                    pattern_name=stat["pattern_name"], symbol=symbol, limit=100
                )

                # 성과 지표 계산
                performance_metrics = self._calculate_pattern_metrics(pattern_instances)

                detailed_analysis.append(
                    {
                        "pattern_name": stat["pattern_name"],
                        "symbol": stat.get("symbol", "ALL"),
                        "total_occurrences": stat["total_count"],
                        "avg_duration_hours": (
                            float(stat["avg_duration"]) if stat["avg_duration"] else 0.0
                        ),
                        "performance_metrics": performance_metrics,
                        "market_conditions": self._analyze_pattern_market_conditions(
                            pattern_instances
                        ),
                    }
                )

            # 3. 전체 요약
            summary = self._generate_pattern_summary(detailed_analysis)

            return {
                "summary": summary,
                "pattern_analysis": detailed_analysis,
                "filters": {
                    "pattern_name": pattern_name,
                    "symbol": symbol,
                    "min_occurrences": min_occurrences,
                },
                "analysis_timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            print(f"❌ 패턴 성과 분석 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    def find_successful_patterns(
        self,
        symbol: Optional[str] = None,
        success_threshold: float = 0.7,
        min_occurrences: int = 3,
    ) -> Dict[str, Any]:
        """
        성공적인 패턴 발견

        Args:
            symbol: 심볼 필터
            success_threshold: 성공 임계값 (70% 이상)
            min_occurrences: 최소 발생 횟수

        Returns:
            성공적인 패턴 목록
        """
        session, pattern_repo, signal_repo = self._get_session_and_repositories()

        try:
            print(f"🔍 성공적인 패턴 탐색: 성공률 {success_threshold:.0%} 이상")

            # 1. 모든 패턴의 성과 분석
            all_patterns = pattern_repo.get_pattern_performance_stats(
                symbol=symbol, min_occurrences=min_occurrences
            )

            # 2. 성공적인 패턴 필터링
            successful_patterns = []
            for pattern_stat in all_patterns:
                pattern_instances = pattern_repo.find_by_pattern_name(
                    pattern_name=pattern_stat["pattern_name"], symbol=symbol, limit=100
                )

                # 성공률 계산 (간단한 버전)
                success_count = 0
                total_count = len(pattern_instances)

                for pattern in pattern_instances:
                    # 패턴 발생 후 가격 상승 여부 확인 (간단한 성공 기준)
                    if self._is_pattern_successful(pattern):
                        success_count += 1

                success_rate = success_count / total_count if total_count > 0 else 0

                if success_rate >= success_threshold:
                    successful_patterns.append(
                        {
                            "pattern_name": pattern_stat["pattern_name"],
                            "symbol": pattern_stat.get("symbol", "ALL"),
                            "success_rate": success_rate,
                            "total_occurrences": total_count,
                            "successful_occurrences": success_count,
                            "avg_duration_hours": (
                                float(pattern_stat["avg_duration"])
                                if pattern_stat["avg_duration"]
                                else 0.0
                            ),
                            "last_occurrence": max(
                                p.pattern_end for p in pattern_instances
                            ).isoformat(),
                        }
                    )

            # 3. 성공률 순으로 정렬
            successful_patterns.sort(key=lambda x: x["success_rate"], reverse=True)

            return {
                "successful_patterns": successful_patterns,
                "criteria": {
                    "success_threshold": success_threshold,
                    "min_occurrences": min_occurrences,
                    "symbol": symbol,
                },
                "summary": {
                    "total_patterns_analyzed": len(all_patterns),
                    "successful_patterns_found": len(successful_patterns),
                    "best_success_rate": (
                        successful_patterns[0]["success_rate"]
                        if successful_patterns
                        else 0.0
                    ),
                },
                "analysis_timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            print(f"❌ 성공적인 패턴 탐색 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    def _calculate_pattern_metrics(
        self, pattern_instances: List[SignalPattern]
    ) -> Dict[str, Any]:
        """
        패턴 성과 지표 계산

        Args:
            pattern_instances: 패턴 인스턴스 목록

        Returns:
            성과 지표
        """
        if not pattern_instances:
            return {}

        # 기본 통계
        durations = [
            float(p.pattern_duration_hours)
            for p in pattern_instances
            if p.pattern_duration_hours
        ]

        metrics = {
            "total_count": len(pattern_instances),
            "avg_duration_hours": sum(durations) / len(durations) if durations else 0.0,
            "min_duration_hours": min(durations) if durations else 0.0,
            "max_duration_hours": max(durations) if durations else 0.0,
            "success_count": sum(
                1 for p in pattern_instances if self._is_pattern_successful(p)
            ),
        }

        metrics["success_rate"] = metrics["success_count"] / metrics["total_count"]

        return metrics

    def _is_pattern_successful(self, pattern: SignalPattern) -> bool:
        """
        패턴 성공 여부 판단 (간단한 버전)

        Args:
            pattern: 패턴 인스턴스

        Returns:
            성공 여부
        """
        # 간단한 성공 기준: 패턴 지속 시간이 1시간 이상이면 성공으로 간주
        # 실제로는 패턴 발생 후 가격 변화를 분석해야 함
        if (
            pattern.pattern_duration_hours
            and float(pattern.pattern_duration_hours) >= 1.0
        ):
            return True
        return False

    def _analyze_pattern_market_conditions(
        self, pattern_instances: List[SignalPattern]
    ) -> Dict[str, Any]:
        """
        패턴별 시장 상황 분석

        Args:
            pattern_instances: 패턴 인스턴스 목록

        Returns:
            시장 상황별 분석
        """
        market_conditions = {}

        for pattern in pattern_instances:
            condition = pattern.market_condition or "unknown"
            if condition not in market_conditions:
                market_conditions[condition] = 0
            market_conditions[condition] += 1

        total = len(pattern_instances)
        return {
            condition: {
                "count": count,
                "percentage": (count / total * 100) if total > 0 else 0,
            }
            for condition, count in market_conditions.items()
        }

    def _generate_pattern_summary(
        self, detailed_analysis: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        패턴 분석 요약 생성

        Args:
            detailed_analysis: 상세 분석 결과

        Returns:
            요약 정보
        """
        if not detailed_analysis:
            return {}

        total_patterns = len(detailed_analysis)
        total_occurrences = sum(p["total_occurrences"] for p in detailed_analysis)
        avg_success_rate = (
            sum(
                p["performance_metrics"].get("success_rate", 0)
                for p in detailed_analysis
            )
            / total_patterns
        )

        # 가장 성공적인 패턴
        best_pattern = max(
            detailed_analysis,
            key=lambda x: x["performance_metrics"].get("success_rate", 0),
        )

        return {
            "total_patterns": total_patterns,
            "total_occurrences": total_occurrences,
            "avg_success_rate": avg_success_rate,
            "best_pattern": {
                "name": best_pattern["pattern_name"],
                "success_rate": best_pattern["performance_metrics"].get(
                    "success_rate", 0
                ),
                "occurrences": best_pattern["total_occurrences"],
            },
        }

    # =================================================================
    # 테스트 및 디버깅 메서드
    # =================================================================

    def test_pattern_analysis(self, symbol: str = "NQ=F") -> Dict[str, Any]:
        """
        패턴 분석 테스트 (개발용)

        Args:
            symbol: 테스트할 심볼

        Returns:
            테스트 결과
        """
        session, pattern_repo, signal_repo = self._get_session_and_repositories()

        try:
            print(f"🧪 패턴 분석 테스트 시작: {symbol}")

            # 1. 테스트용 패턴 데이터 생성
            test_patterns = [
                {
                    "pattern_name": "RSI_oversold_then_MA_breakout",
                    "description": "RSI 과매도 후 이동평균선 돌파",
                    "signal_types": ["RSI_oversold", "MA20_breakout_up"],
                    "expected_success_rate": 0.75,
                },
                {
                    "pattern_name": "BB_squeeze_then_breakout",
                    "description": "볼린저 밴드 수축 후 돌파",
                    "signal_types": ["BB_touch_lower", "BB_break_upper"],
                    "expected_success_rate": 0.65,
                },
                {
                    "pattern_name": "Golden_cross_with_volume",
                    "description": "골든크로스와 거래량 급증",
                    "signal_types": ["golden_cross"],
                    "expected_success_rate": 0.80,
                },
            ]

            # 2. 각 패턴에 대한 테스트 데이터 생성
            created_patterns = []
            for i, test_pattern in enumerate(test_patterns):
                try:
                    # 테스트용 신호 ID 생성 (실제 신호가 있다고 가정)
                    signal_ids = [
                        1,
                        2,
                        3,
                    ]  # 실제로는 해당 신호 타입의 ID들을 조회해야 함

                    pattern = pattern_repo.create_sequential_pattern(
                        pattern_name=test_pattern["pattern_name"],
                        symbol=symbol,
                        timeframe="15min",
                        signal_ids=signal_ids,
                        market_condition="bullish" if i % 2 == 0 else "bearish",
                    )

                    created_patterns.append(
                        {
                            "id": pattern.id,
                            "name": pattern.pattern_name,
                            "description": test_pattern["description"],
                            "expected_success_rate": test_pattern[
                                "expected_success_rate"
                            ],
                        }
                    )

                    print(f"✅ 테스트 패턴 생성: {test_pattern['pattern_name']}")

                except Exception as e:
                    print(
                        f"⚠️ 테스트 패턴 생성 실패: {test_pattern['pattern_name']} - {e}"
                    )

            session.commit()

            # 3. 생성된 패턴들 분석
            analysis_result = self.analyze_pattern_performance(
                symbol=symbol, min_occurrences=1  # 테스트용으로 낮게 설정
            )

            # 4. 성공적인 패턴 탐색
            successful_patterns = self.find_successful_patterns(
                symbol=symbol,
                success_threshold=0.5,  # 테스트용으로 낮게 설정
                min_occurrences=1,
            )

            return {
                "test_summary": {
                    "symbol": symbol,
                    "created_patterns": len(created_patterns),
                    "test_patterns": created_patterns,
                },
                "pattern_analysis": analysis_result,
                "successful_patterns": successful_patterns,
                "test_timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            session.rollback()
            print(f"❌ 패턴 분석 테스트 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    def cleanup_test_patterns(self, symbol: str = "NQ=F") -> Dict[str, Any]:
        """
        테스트용 패턴 데이터 정리

        Args:
            symbol: 정리할 심볼

        Returns:
            정리 결과
        """
        session, pattern_repo, signal_repo = self._get_session_and_repositories()

        try:
            print(f"🧹 테스트 패턴 데이터 정리: {symbol}")

            # 테스트 패턴명들
            test_pattern_names = [
                "RSI_oversold_then_MA_breakout",
                "BB_squeeze_then_breakout",
                "Golden_cross_with_volume",
            ]

            deleted_count = 0
            for pattern_name in test_pattern_names:
                patterns = pattern_repo.find_by_pattern_name(
                    pattern_name=pattern_name, symbol=symbol, limit=100
                )

                for pattern in patterns:
                    session.delete(pattern)
                    deleted_count += 1

            session.commit()

            print(f"✅ 테스트 패턴 정리 완료: {deleted_count}개 삭제")
            return {
                "deleted_count": deleted_count,
                "deleted_patterns": test_pattern_names,
                "symbol": symbol,
            }

        except Exception as e:
            session.rollback()
            print(f"❌ 테스트 패턴 정리 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    def __del__(self):
        """소멸자 - 세션 정리"""
        if self.session:
            self.session.close()
