"""
백테스팅 서비스

이 서비스는 과거 기술적 신호들의 성과를 분석하여 신호의 품질을 평가합니다.
실제 매매 전략을 개발하고 검증하는데 사용됩니다.

백테스팅이란?
- 과거 데이터를 사용하여 매매 전략의 성과를 시뮬레이션하는 것
- "만약 이 신호대로 매매했다면 얼마나 수익을 냈을까?" 를 계산
- 신호의 신뢰도와 수익성을 객관적으로 평가

주요 분석 항목:
1. 수익률 분석: 평균 수익률, 최대 수익률, 최대 손실률
2. 승률 분석: 성공한 신호의 비율
3. 리스크 분석: 최대 손실폭, 변동성, 샤프 비율
4. 시장 상황별 분석: 상승장/하락장에서의 성과 차이
5. 시간대별 분석: 1시간/1일/1주일 후 성과 비교

활용 방안:
- 알림 최적화: 성과가 좋은 신호만 알림 발송
- 매매 전략 개발: 효과적인 신호 조합 발견
- 리스크 관리: 위험한 신호 패턴 식별
- 포트폴리오 구성: 다양한 신호의 조합으로 리스크 분산
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.common.infra.database.config.database_config import SessionLocal
from app.technical_analysis.infra.model.repository.signal_outcome_repository import (
    SignalOutcomeRepository,
)
from app.technical_analysis.infra.model.repository.technical_signal_repository import (
    TechnicalSignalRepository,
)
from app.technical_analysis.infra.model.entity.signal_outcomes import SignalOutcome
from app.technical_analysis.infra.model.entity.technical_signals import TechnicalSignal


class BacktestingService:
    """
    백테스팅 및 성과 분석을 담당하는 서비스

    과거 신호들의 실제 성과를 분석하여 신호의 품질을 평가하고
    매매 전략 개발에 필요한 통계를 제공합니다.
    """

    def __init__(self):
        """서비스 초기화"""
        self.session: Optional[Session] = None
        self.outcome_repository: Optional[SignalOutcomeRepository] = None
        self.signal_repository: Optional[TechnicalSignalRepository] = None

    def _get_session_and_repositories(self):
        """세션과 리포지토리 초기화 (지연 초기화)"""
        if not self.session:
            self.session = SessionLocal()
            self.outcome_repository = SignalOutcomeRepository(self.session)
            self.signal_repository = TechnicalSignalRepository(self.session)
        return self.session, self.outcome_repository, self.signal_repository

    # =================================================================
    # 전체 성과 분석
    # =================================================================

    def analyze_all_signals_performance(
        self, timeframe_eval: str = "1d", min_samples: int = 10
    ) -> Dict[str, Any]:
        """
        모든 신호 타입의 성과를 종합 분석

        Args:
            timeframe_eval: 평가 기간 ('1h', '1d', '1w', '1m')
            min_samples: 최소 샘플 수 (이보다 적으면 제외)

        Returns:
            전체 성과 분석 결과
            {
                'summary': {전체 요약 통계},
                'by_signal_type': [신호 타입별 성과],
                'best_performers': [가장 좋은 신호들],
                'worst_performers': [가장 나쁜 신호들],
                'recommendations': [추천 사항]
            }
        """
        session, outcome_repo, signal_repo = self._get_session_and_repositories()

        try:
            # 1. 신호 타입별 성공률 분석
            success_rates = outcome_repo.get_success_rate_by_signal_type(
                timeframe_eval=timeframe_eval, min_samples=min_samples
            )

            # 2. 신호 타입별 평균 수익률 분석
            avg_returns = outcome_repo.get_average_returns_by_signal_type(
                timeframe_eval=timeframe_eval, min_samples=min_samples
            )

            # 3. 최고 성과 신호들
            best_performers = outcome_repo.get_best_performing_signals(
                timeframe_eval=timeframe_eval, min_samples=min_samples, limit=5
            )

            # 4. 전체 요약 통계 계산
            all_success_rates = [s["success_rate"] for s in success_rates]
            all_avg_returns = [r["avg_return"] for r in avg_returns]

            summary = {
                "total_signal_types": len(success_rates),
                "overall_success_rate": (
                    sum(all_success_rates) / len(all_success_rates)
                    if all_success_rates
                    else 0.0
                ),
                "overall_avg_return": (
                    sum(all_avg_returns) / len(all_avg_returns)
                    if all_avg_returns
                    else 0.0
                ),
                "best_success_rate": (
                    max(all_success_rates) if all_success_rates else 0.0
                ),
                "worst_success_rate": (
                    min(all_success_rates) if all_success_rates else 0.0
                ),
                "best_avg_return": max(all_avg_returns) if all_avg_returns else 0.0,
                "worst_avg_return": min(all_avg_returns) if all_avg_returns else 0.0,
                "evaluation_period": timeframe_eval,
                "min_samples_required": min_samples,
            }

            # 5. 성과별로 분류
            excellent_signals = [
                s
                for s in success_rates
                if s["success_rate"] >= 0.7 and s["total_count"] >= min_samples
            ]
            poor_signals = [
                s
                for s in success_rates
                if s["success_rate"] <= 0.4 and s["total_count"] >= min_samples
            ]

            # 6. 추천 사항 생성
            recommendations = self._generate_recommendations(
                success_rates,
                avg_returns,
                best_performers,
                excellent_signals,
                poor_signals,
            )

            return {
                "summary": summary,
                "by_signal_type": {
                    "success_rates": success_rates,
                    "average_returns": avg_returns,
                },
                "best_performers": best_performers,
                "excellent_signals": excellent_signals,
                "poor_signals": poor_signals,
                "recommendations": recommendations,
                "analysis_timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            print(f"❌ 전체 성과 분석 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    def analyze_signal_type_performance(
        self, signal_type: str, symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        특정 신호 타입의 상세 성과 분석

        Args:
            signal_type: 분석할 신호 타입 (예: MA200_breakout_up)
            symbol: 심볼 필터 (선택사항)

        Returns:
            해당 신호의 상세 분석 결과
        """
        session, outcome_repo, signal_repo = self._get_session_and_repositories()

        try:
            # 1. 시간대별 성과 분석
            timeframe_performance = outcome_repo.get_performance_by_timeframe(
                signal_type=signal_type, symbol=symbol
            )

            # 2. 리스크 지표 계산
            risk_metrics = outcome_repo.get_risk_metrics(
                signal_type=signal_type, timeframe_eval="1d", symbol=symbol
            )

            # 3. 해당 신호의 모든 결과 조회
            outcomes = outcome_repo.find_outcomes_by_signal_type(
                signal_type=signal_type, limit=1000
            )

            # 4. 월별 성과 분석
            monthly_performance = self._analyze_monthly_performance(outcomes)

            # 5. 시장 상황별 성과 (간단한 분석)
            market_analysis = self._analyze_by_market_condition(outcomes)

            return {
                "signal_type": signal_type,
                "symbol": symbol,
                "total_signals": len(outcomes),
                "timeframe_performance": timeframe_performance,
                "risk_metrics": risk_metrics,
                "monthly_performance": monthly_performance,
                "market_condition_analysis": market_analysis,
                "signal_quality_score": self._calculate_signal_quality_score(
                    timeframe_performance, risk_metrics
                ),
                "analysis_timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            print(f"❌ 신호 타입 성과 분석 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    # =================================================================
    # 매매 전략 시뮬레이션
    # =================================================================

    def simulate_trading_strategy(
        self,
        signal_types: List[str],
        initial_capital: float = 10000.0,
        position_size: float = 0.1,  # 10% of capital per trade
        stop_loss: Optional[float] = None,  # -5% stop loss
        take_profit: Optional[float] = None,  # +10% take profit
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        매매 전략 시뮬레이션

        Args:
            signal_types: 사용할 신호 타입 리스트
            initial_capital: 초기 자본금
            position_size: 포지션 크기 (자본금 대비 비율)
            stop_loss: 손절매 비율 (예: -0.05 = -5%)
            take_profit: 익절매 비율 (예: 0.10 = +10%)
            start_date: 시뮬레이션 시작 날짜
            end_date: 시뮬레이션 종료 날짜

        Returns:
            시뮬레이션 결과
        """
        session, outcome_repo, signal_repo = self._get_session_and_repositories()

        try:
            # 1. 해당 기간의 신호들 조회
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=90)  # 기본 3개월
            if not end_date:
                end_date = datetime.utcnow()

            all_signals = []
            for signal_type in signal_types:
                signals = signal_repo.find_by_date_range(
                    start_date=start_date, end_date=end_date, signal_type=signal_type
                )
                all_signals.extend(signals)

            # 시간순 정렬
            all_signals.sort(key=lambda x: x.triggered_at)

            # 2. 매매 시뮬레이션 실행
            trades = []
            current_capital = initial_capital
            max_capital = initial_capital
            max_drawdown = 0.0

            for signal in all_signals:
                # 해당 신호의 결과 조회
                outcome = outcome_repo.find_by_signal_id(signal.id)
                if not outcome or outcome.return_1d is None:
                    continue

                # 포지션 크기 계산
                trade_amount = current_capital * position_size

                # 수익률 적용 (stop loss, take profit 고려)
                signal_return = float(outcome.return_1d) / 100.0  # % to decimal

                # Stop loss / Take profit 적용
                if stop_loss and signal_return < stop_loss:
                    actual_return = stop_loss
                elif take_profit and signal_return > take_profit:
                    actual_return = take_profit
                else:
                    actual_return = signal_return

                # 손익 계산
                profit_loss = trade_amount * actual_return
                current_capital += profit_loss

                # 최대 자본금 및 최대 손실 추적
                max_capital = max(max_capital, current_capital)
                drawdown = (max_capital - current_capital) / max_capital
                max_drawdown = max(max_drawdown, drawdown)

                # 거래 기록
                trades.append(
                    {
                        "date": signal.triggered_at.isoformat(),
                        "signal_type": signal.signal_type,
                        "symbol": signal.symbol,
                        "entry_price": float(signal.current_price),
                        "signal_return": signal_return,
                        "actual_return": actual_return,
                        "trade_amount": trade_amount,
                        "profit_loss": profit_loss,
                        "capital_after": current_capital,
                    }
                )

            # 3. 성과 지표 계산
            total_return = (current_capital - initial_capital) / initial_capital
            total_return_pct = total_return * 100

            winning_trades = [t for t in trades if t["profit_loss"] > 0]
            losing_trades = [t for t in trades if t["profit_loss"] < 0]

            win_rate = len(winning_trades) / len(trades) if trades else 0
            avg_win = (
                sum(t["profit_loss"] for t in winning_trades) / len(winning_trades)
                if winning_trades
                else 0
            )
            avg_loss = (
                sum(t["profit_loss"] for t in losing_trades) / len(losing_trades)
                if losing_trades
                else 0
            )

            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float("inf")

            return {
                "strategy_config": {
                    "signal_types": signal_types,
                    "initial_capital": initial_capital,
                    "position_size": position_size,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "period": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat(),
                    },
                },
                "performance": {
                    "total_trades": len(trades),
                    "initial_capital": initial_capital,
                    "final_capital": current_capital,
                    "total_return_pct": total_return_pct,
                    "max_drawdown_pct": max_drawdown * 100,
                    "win_rate": win_rate,
                    "avg_win": avg_win,
                    "avg_loss": avg_loss,
                    "profit_factor": profit_factor,
                    "winning_trades": len(winning_trades),
                    "losing_trades": len(losing_trades),
                },
                "trades": trades[-20:],  # 최근 20개 거래만 반환
                "analysis_timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            print(f"❌ 매매 전략 시뮬레이션 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    # =================================================================
    # 신호 품질 평가
    # =================================================================

    def evaluate_signal_quality(
        self, signal_type: str, symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        신호 품질 종합 평가

        Args:
            signal_type: 평가할 신호 타입
            symbol: 심볼 필터 (선택사항)

        Returns:
            신호 품질 평가 결과 (점수 및 등급 포함)
        """
        session, outcome_repo, signal_repo = self._get_session_and_repositories()

        try:
            # 1. 기본 성과 지표 수집
            timeframe_performance = outcome_repo.get_performance_by_timeframe(
                signal_type=signal_type, symbol=symbol
            )

            risk_metrics = outcome_repo.get_risk_metrics(
                signal_type=signal_type, symbol=symbol
            )

            # 2. 품질 점수 계산 (0~100점)
            quality_score = self._calculate_signal_quality_score(
                timeframe_performance, risk_metrics
            )

            # 3. 등급 결정
            if quality_score >= 80:
                grade = "A"
                recommendation = "매우 우수한 신호. 적극 활용 권장"
            elif quality_score >= 70:
                grade = "B"
                recommendation = "좋은 신호. 활용 권장"
            elif quality_score >= 60:
                grade = "C"
                recommendation = "보통 신호. 다른 지표와 함께 사용"
            elif quality_score >= 50:
                grade = "D"
                recommendation = "약한 신호. 신중한 사용 필요"
            else:
                grade = "F"
                recommendation = "품질이 낮은 신호. 사용 비권장"

            # 4. 상세 분석
            strengths = []
            weaknesses = []

            # 승률 분석
            win_rate_1d = timeframe_performance.get("1d", {}).get("success_rate", 0)
            if win_rate_1d > 0.7:
                strengths.append(f"높은 승률 ({win_rate_1d:.1%})")
            elif win_rate_1d < 0.4:
                weaknesses.append(f"낮은 승률 ({win_rate_1d:.1%})")

            # 수익률 분석
            avg_return_1d = timeframe_performance.get("1d", {}).get("avg_return", 0)
            if avg_return_1d > 2.0:
                strengths.append(f"높은 평균 수익률 ({avg_return_1d:.1f}%)")
            elif avg_return_1d < 0:
                weaknesses.append(f"음수 평균 수익률 ({avg_return_1d:.1f}%)")

            # 리스크 분석
            max_drawdown = risk_metrics.get("max_drawdown", 0)
            if max_drawdown > -10:
                strengths.append("낮은 최대 손실률")
            elif max_drawdown < -20:
                weaknesses.append(f"높은 최대 손실률 ({max_drawdown:.1f}%)")

            return {
                "signal_type": signal_type,
                "symbol": symbol,
                "quality_assessment": {
                    "overall_score": quality_score,
                    "grade": grade,
                    "recommendation": recommendation,
                },
                "detailed_analysis": {
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                    "sample_size": risk_metrics.get("total_trades", 0),
                },
                "performance_metrics": {
                    "timeframe_performance": timeframe_performance,
                    "risk_metrics": risk_metrics,
                },
                "analysis_timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            print(f"❌ 신호 품질 평가 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    # =================================================================
    # 헬퍼 메서드들
    # =================================================================

    def _calculate_signal_quality_score(
        self,
        timeframe_performance: Dict[str, Dict[str, float]],
        risk_metrics: Dict[str, float],
    ) -> float:
        """
        신호 품질 점수 계산 (0~100)

        Args:
            timeframe_performance: 시간대별 성과
            risk_metrics: 리스크 지표

        Returns:
            품질 점수 (0~100)
        """
        score = 0.0

        # 1일 기준 성과 (가중치 40%)
        perf_1d = timeframe_performance.get("1d", {})
        success_rate = perf_1d.get("success_rate", 0)
        avg_return = perf_1d.get("avg_return", 0)

        # 승률 점수 (20%)
        score += min(success_rate * 100, 20)

        # 평균 수익률 점수 (20%)
        return_score = min(max(avg_return * 2, 0), 20)  # 10% 수익률 = 20점
        score += return_score

        # 리스크 조정 (가중치 30%)
        max_drawdown = risk_metrics.get("max_drawdown", 0)
        profit_factor = risk_metrics.get("profit_factor", 0)

        # 최대 손실률 점수 (15%)
        drawdown_score = max(15 + max_drawdown * 0.75, 0)  # -20% = 0점, 0% = 15점
        score += drawdown_score

        # 수익 팩터 점수 (15%)
        pf_score = min(profit_factor * 7.5, 15)  # 2.0 = 15점
        score += pf_score

        # 샘플 크기 보정 (가중치 10%)
        sample_size = risk_metrics.get("total_trades", 0)
        sample_score = min(sample_size * 0.5, 10)  # 20개 = 10점
        score += sample_score

        return min(score, 100.0)

    def _generate_recommendations(
        self,
        success_rates: List[Dict],
        avg_returns: List[Dict],
        best_performers: List[Dict],
        excellent_signals: List[Dict],
        poor_signals: List[Dict],
    ) -> List[str]:
        """추천 사항 생성"""
        recommendations = []

        if excellent_signals:
            top_signal = excellent_signals[0]["signal_type"]
            recommendations.append(
                f"✅ '{top_signal}' 신호는 우수한 성과를 보입니다. 적극 활용하세요."
            )

        if poor_signals:
            worst_signal = poor_signals[0]["signal_type"]
            recommendations.append(
                f"⚠️ '{worst_signal}' 신호는 성과가 좋지 않습니다. 사용을 재검토하세요."
            )

        if best_performers:
            best = best_performers[0]
            recommendations.append(
                f"🏆 '{best['signal_type']}' ({best['symbol']}, {best['timeframe']})가 "
                f"가장 좋은 성과를 보입니다 (수익률: {best['avg_return']:.1f}%)."
            )

        # 전반적인 조언
        overall_success = (
            sum(s["success_rate"] for s in success_rates) / len(success_rates)
            if success_rates
            else 0
        )
        if overall_success > 0.6:
            recommendations.append("📈 전반적으로 신호 품질이 양호합니다.")
        elif overall_success < 0.4:
            recommendations.append(
                "📉 신호 품질 개선이 필요합니다. 필터링 조건을 강화하세요."
            )

        return recommendations

    def _analyze_monthly_performance(
        self, outcomes: List[SignalOutcome]
    ) -> Dict[str, Any]:
        """월별 성과 분석"""
        monthly_data = {}

        for outcome in outcomes:
            if not outcome.signal or not outcome.return_1d:
                continue

            month_key = outcome.signal.triggered_at.strftime("%Y-%m")
            if month_key not in monthly_data:
                monthly_data[month_key] = []
            monthly_data[month_key].append(float(outcome.return_1d))

        monthly_stats = {}
        for month, returns in monthly_data.items():
            monthly_stats[month] = {
                "count": len(returns),
                "avg_return": sum(returns) / len(returns),
                "win_rate": len([r for r in returns if r > 0]) / len(returns),
            }

        return monthly_stats

    def _analyze_by_market_condition(
        self, outcomes: List[SignalOutcome]
    ) -> Dict[str, Any]:
        """시장 상황별 성과 분석 (간단한 버전)"""
        # 수익률 기준으로 시장 상황 추정
        positive_outcomes = [
            o for o in outcomes if o.return_1d and float(o.return_1d) > 2
        ]
        negative_outcomes = [
            o for o in outcomes if o.return_1d and float(o.return_1d) < -2
        ]
        neutral_outcomes = [
            o for o in outcomes if o.return_1d and -2 <= float(o.return_1d) <= 2
        ]

        return {
            "strong_market": {
                "count": len(positive_outcomes),
                "description": "강한 시장 상황에서의 성과",
            },
            "weak_market": {
                "count": len(negative_outcomes),
                "description": "약한 시장 상황에서의 성과",
            },
            "neutral_market": {
                "count": len(neutral_outcomes),
                "description": "중립적 시장 상황에서의 성과",
            },
        }

    def __del__(self):
        """소멸자 - 세션 정리"""
        if self.session:
            self.session.close()
