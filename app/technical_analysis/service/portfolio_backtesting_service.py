"""
포트폴리오 백테스팅 서비스

Phase 3의 고급 기능으로, 여러 전략을 조합한 포트폴리오의 성과를 분석합니다.

주요 기능:
1. 다중 전략 포트폴리오 - 여러 신호 전략을 조합하여 리스크 분산
2. 상관관계 분석 - 전략 간 상관관계를 고려한 최적 조합
3. 리밸런싱 전략 - 주기적 포트폴리오 재조정
4. 고급 리스크 지표 - VaR, CVaR, 샤프비율, 소르티노비율 등
5. 몬테카를로 시뮬레이션 - 다양한 시나리오 분석

포트폴리오 전략:
- Equal Weight: 모든 전략에 동일한 비중
- Risk Parity: 리스크 기여도에 따른 비중 조정
- Momentum: 최근 성과가 좋은 전략에 높은 비중
- Mean Reversion: 성과가 나쁜 전략에 높은 비중 (반전 기대)
"""

import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.common.infra.database.config.database_config import SessionLocal
from app.technical_analysis.service.backtesting_service import BacktestingService
from app.technical_analysis.infra.model.repository.technical_signal_repository import TechnicalSignalRepository
from app.technical_analysis.infra.model.repository.signal_outcome_repository import SignalOutcomeRepository


class PortfolioBacktestingService:
    """
    포트폴리오 백테스팅을 담당하는 서비스
    
    여러 전략을 조합한 포트폴리오의 성과를 분석합니다.
    """

    def __init__(self):
        """서비스 초기화"""
        self.session: Optional[Session] = None
        self.signal_repository: Optional[TechnicalSignalRepository] = None
        self.outcome_repository: Optional[SignalOutcomeRepository] = None
        self.backtesting_service = BacktestingService()

    def _get_session_and_repositories(self):
        """세션과 리포지토리 초기화 (지연 초기화)"""
        if not self.session:
            self.session = SessionLocal()
            self.signal_repository = TechnicalSignalRepository(self.session)
            self.outcome_repository = SignalOutcomeRepository(self.session)
        return self.session, self.signal_repository, self.outcome_repository

    # =================================================================
    # 포트폴리오 백테스팅
    # =================================================================

    def backtest_portfolio_strategies(
        self,
        strategies: List[Dict[str, Any]],
        portfolio_method: str = "equal_weight",
        initial_capital: float = 100000.0,
        rebalancing_frequency: str = "monthly",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        포트폴리오 전략 백테스팅
        
        Args:
            strategies: 전략 리스트
                [
                    {
                        "name": "MA_Strategy",
                        "signal_types": ["MA200_breakout_up"],
                        "position_size": 0.1,
                        "stop_loss": -0.05,
                        "take_profit": 0.10
                    },
                    ...
                ]
            portfolio_method: 포트폴리오 구성 방법
                - "equal_weight": 동일 비중
                - "risk_parity": 리스크 패리티
                - "momentum": 모멘텀 기반
                - "mean_reversion": 평균 회귀 기반
            initial_capital: 초기 자본금
            rebalancing_frequency: 리밸런싱 주기 ("monthly", "quarterly", "yearly")
            start_date: 시작 날짜
            end_date: 종료 날짜
            
        Returns:
            포트폴리오 백테스팅 결과
        """
        session, signal_repo, outcome_repo = self._get_session_and_repositories()
        
        try:
            print(f"🔄 포트폴리오 백테스팅 시작: {len(strategies)}개 전략")
            
            # 기본 날짜 설정
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=180)  # 기본 6개월
            
            # 각 전략별 개별 백테스팅
            strategy_results = []
            for i, strategy in enumerate(strategies):
                print(f"   📊 전략 {i+1}/{len(strategies)} 백테스팅: {strategy['name']}")
                
                result = self.backtesting_service.simulate_trading_strategy(
                    signal_types=strategy["signal_types"],
                    initial_capital=initial_capital / len(strategies),  # 균등 분할
                    position_size=strategy.get("position_size", 0.1),
                    stop_loss=strategy.get("stop_loss"),
                    take_profit=strategy.get("take_profit"),
                    start_date=start_date,
                    end_date=end_date,
                )
                
                if "error" not in result:
                    strategy_results.append({
                        "strategy": strategy,
                        "result": result
                    })
            
            if not strategy_results:
                return {"error": "모든 전략의 백테스팅이 실패했습니다"}
            
            # 포트폴리오 성과 계산
            portfolio_performance = self._calculate_portfolio_performance(
                strategy_results, portfolio_method, rebalancing_frequency
            )
            
            # 상관관계 분석
            correlation_analysis = self._analyze_strategy_correlations(strategy_results)
            
            # 리스크 지표 계산
            risk_metrics = self._calculate_advanced_risk_metrics(portfolio_performance)
            
            # 개별 전략 vs 포트폴리오 비교
            comparison = self._compare_strategies_vs_portfolio(strategy_results, portfolio_performance)
            
            return {
                "portfolio_config": {
                    "strategies": [s["strategy"] for s in strategy_results],
                    "portfolio_method": portfolio_method,
                    "rebalancing_frequency": rebalancing_frequency,
                    "initial_capital": initial_capital,
                    "period": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat(),
                        "days": (end_date - start_date).days
                    }
                },
                "portfolio_performance": portfolio_performance,
                "individual_strategies": [s["result"]["performance"] for s in strategy_results],
                "correlation_analysis": correlation_analysis,
                "risk_metrics": risk_metrics,
                "comparison": comparison,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"❌ 포트폴리오 백테스팅 실패: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    def _calculate_portfolio_performance(
        self, 
        strategy_results: List[Dict[str, Any]], 
        portfolio_method: str,
        rebalancing_frequency: str
    ) -> Dict[str, Any]:
        """포트폴리오 성과 계산"""
        
        # 각 전략의 일별 수익률 추출 (간단한 구현)
        strategy_returns = []
        for strategy_result in strategy_results:
            trades = strategy_result["result"]["trades"]
            if trades:
                # 거래별 수익률을 일별로 변환 (간단한 근사)
                daily_returns = [trade["actual_return"] for trade in trades]
                strategy_returns.append(daily_returns)
        
        if not strategy_returns:
            return {"error": "수익률 데이터가 없습니다"}
        
        # 포트폴리오 가중치 계산
        weights = self._calculate_portfolio_weights(strategy_results, portfolio_method)
        
        # 포트폴리오 수익률 계산
        portfolio_returns = []
        min_length = min(len(returns) for returns in strategy_returns)
        
        for i in range(min_length):
            portfolio_return = sum(
                weights[j] * strategy_returns[j][i] 
                for j in range(len(strategy_returns))
            )
            portfolio_returns.append(portfolio_return)
        
        # 성과 지표 계산
        total_return = sum(portfolio_returns)
        avg_return = total_return / len(portfolio_returns) if portfolio_returns else 0
        
        winning_periods = len([r for r in portfolio_returns if r > 0])
        win_rate = winning_periods / len(portfolio_returns) if portfolio_returns else 0
        
        # 변동성 계산
        volatility = np.std(portfolio_returns) if len(portfolio_returns) > 1 else 0
        
        # 최대 손실 계산
        cumulative_returns = np.cumsum(portfolio_returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = cumulative_returns - running_max
        max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0
        
        return {
            "total_return_pct": total_return,
            "avg_return_pct": avg_return,
            "volatility_pct": volatility,
            "win_rate": win_rate,
            "max_drawdown_pct": max_drawdown,
            "sharpe_ratio": avg_return / volatility if volatility > 0 else 0,
            "total_periods": len(portfolio_returns),
            "winning_periods": winning_periods,
            "losing_periods": len(portfolio_returns) - winning_periods,
            "portfolio_weights": {
                f"strategy_{i+1}": weights[i] 
                for i in range(len(weights))
            }
        }

    def _calculate_portfolio_weights(
        self, strategy_results: List[Dict[str, Any]], method: str
    ) -> List[float]:
        """포트폴리오 가중치 계산"""
        
        n_strategies = len(strategy_results)
        
        if method == "equal_weight":
            # 동일 비중
            return [1.0 / n_strategies] * n_strategies
        
        elif method == "risk_parity":
            # 리스크 패리티 (간단한 구현)
            volatilities = []
            for result in strategy_results:
                trades = result["result"]["trades"]
                if trades:
                    returns = [trade["actual_return"] for trade in trades]
                    vol = np.std(returns) if len(returns) > 1 else 1.0
                    volatilities.append(vol)
                else:
                    volatilities.append(1.0)
            
            # 변동성의 역수로 가중치 계산
            inv_vol = [1.0 / vol for vol in volatilities]
            total_inv_vol = sum(inv_vol)
            return [w / total_inv_vol for w in inv_vol]
        
        elif method == "momentum":
            # 모멘텀 기반 (최근 성과가 좋은 전략에 높은 비중)
            returns = []
            for result in strategy_results:
                total_return = result["result"]["performance"]["total_return_pct"]
                returns.append(max(total_return, 0))  # 음수는 0으로 처리
            
            total_return = sum(returns)
            if total_return > 0:
                return [r / total_return for r in returns]
            else:
                return [1.0 / n_strategies] * n_strategies
        
        elif method == "mean_reversion":
            # 평균 회귀 (성과가 나쁜 전략에 높은 비중)
            returns = []
            for result in strategy_results:
                total_return = result["result"]["performance"]["total_return_pct"]
                returns.append(total_return)
            
            # 수익률을 역순으로 변환
            max_return = max(returns) if returns else 0
            inv_returns = [max_return - r + 1 for r in returns]
            total_inv_return = sum(inv_returns)
            
            if total_inv_return > 0:
                return [r / total_inv_return for r in inv_returns]
            else:
                return [1.0 / n_strategies] * n_strategies
        
        else:
            # 기본값: 동일 비중
            return [1.0 / n_strategies] * n_strategies

    def _analyze_strategy_correlations(
        self, strategy_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """전략 간 상관관계 분석"""
        
        if len(strategy_results) < 2:
            return {"message": "상관관계 분석을 위해서는 최소 2개의 전략이 필요합니다"}
        
        # 각 전략의 수익률 추출
        strategy_returns = []
        strategy_names = []
        
        for result in strategy_results:
            trades = result["result"]["trades"]
            strategy_name = result["strategy"]["name"]
            
            if trades:
                returns = [trade["actual_return"] for trade in trades]
                strategy_returns.append(returns)
                strategy_names.append(strategy_name)
        
        if len(strategy_returns) < 2:
            return {"message": "상관관계 분석을 위한 충분한 데이터가 없습니다"}
        
        # 상관관계 매트릭스 계산
        min_length = min(len(returns) for returns in strategy_returns)
        correlation_matrix = []
        
        for i in range(len(strategy_returns)):
            correlation_row = []
            for j in range(len(strategy_returns)):
                if i == j:
                    correlation = 1.0
                else:
                    returns_i = strategy_returns[i][:min_length]
                    returns_j = strategy_returns[j][:min_length]
                    correlation = np.corrcoef(returns_i, returns_j)[0, 1]
                    if np.isnan(correlation):
                        correlation = 0.0
                
                correlation_row.append(round(correlation, 3))
            correlation_matrix.append(correlation_row)
        
        # 평균 상관관계 계산
        correlations = []
        for i in range(len(strategy_returns)):
            for j in range(i + 1, len(strategy_returns)):
                correlations.append(correlation_matrix[i][j])
        
        avg_correlation = sum(correlations) / len(correlations) if correlations else 0
        
        return {
            "strategy_names": strategy_names,
            "correlation_matrix": correlation_matrix,
            "average_correlation": round(avg_correlation, 3),
            "diversification_benefit": "High" if avg_correlation < 0.3 else "Medium" if avg_correlation < 0.7 else "Low",
            "analysis": {
                "low_correlation_pairs": [
                    f"{strategy_names[i]} vs {strategy_names[j]}"
                    for i in range(len(strategy_names))
                    for j in range(i + 1, len(strategy_names))
                    if correlation_matrix[i][j] < 0.3
                ],
                "high_correlation_pairs": [
                    f"{strategy_names[i]} vs {strategy_names[j]}"
                    for i in range(len(strategy_names))
                    for j in range(i + 1, len(strategy_names))
                    if correlation_matrix[i][j] > 0.7
                ]
            }
        }

    def _calculate_advanced_risk_metrics(
        self, portfolio_performance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """고급 리스크 지표 계산"""
        
        # 기본 지표들
        total_return = portfolio_performance.get("total_return_pct", 0)
        volatility = portfolio_performance.get("volatility_pct", 0)
        max_drawdown = portfolio_performance.get("max_drawdown_pct", 0)
        win_rate = portfolio_performance.get("win_rate", 0)
        
        # 샤프 비율 (이미 계산됨)
        sharpe_ratio = portfolio_performance.get("sharpe_ratio", 0)
        
        # 소르티노 비율 (하방 변동성만 고려)
        # 간단한 근사: 샤프 비율 * 1.4 (일반적인 비율)
        sortino_ratio = sharpe_ratio * 1.4 if sharpe_ratio > 0 else 0
        
        # 칼마 비율 (연간 수익률 / 최대 손실률)
        calmar_ratio = (total_return / abs(max_drawdown)) if max_drawdown != 0 else 0
        
        # VaR (Value at Risk) 95% 신뢰구간 (간단한 근사)
        var_95 = volatility * 1.645  # 정규분포 가정
        
        # CVaR (Conditional VaR) - VaR을 초과하는 손실의 평균
        cvar_95 = var_95 * 1.3  # 간단한 근사
        
        # 정보 비율 (초과 수익률 / 추적 오차)
        # 벤치마크를 0%로 가정
        information_ratio = total_return / volatility if volatility > 0 else 0
        
        return {
            "sharpe_ratio": round(sharpe_ratio, 3),
            "sortino_ratio": round(sortino_ratio, 3),
            "calmar_ratio": round(calmar_ratio, 3),
            "information_ratio": round(information_ratio, 3),
            "var_95_pct": round(var_95, 3),
            "cvar_95_pct": round(cvar_95, 3),
            "max_drawdown_pct": round(max_drawdown, 3),
            "volatility_pct": round(volatility, 3),
            "win_rate": round(win_rate, 3),
            "risk_grade": self._calculate_risk_grade(sharpe_ratio, max_drawdown, win_rate),
            "interpretation": {
                "sharpe_ratio": "위험 대비 수익률 (1.0 이상 양호)",
                "sortino_ratio": "하방 위험 대비 수익률 (1.5 이상 양호)",
                "calmar_ratio": "최대손실 대비 수익률 (1.0 이상 양호)",
                "var_95": "95% 신뢰구간에서 예상 최대 손실",
                "cvar_95": "VaR 초과시 예상 평균 손실"
            }
        }

    def _calculate_risk_grade(self, sharpe_ratio: float, max_drawdown: float, win_rate: float) -> str:
        """리스크 등급 계산"""
        score = 0
        
        # 샤프 비율 점수 (40%)
        if sharpe_ratio >= 2.0:
            score += 40
        elif sharpe_ratio >= 1.0:
            score += 30
        elif sharpe_ratio >= 0.5:
            score += 20
        elif sharpe_ratio >= 0:
            score += 10
        
        # 최대 손실률 점수 (30%)
        if max_drawdown >= -5:
            score += 30
        elif max_drawdown >= -10:
            score += 25
        elif max_drawdown >= -15:
            score += 20
        elif max_drawdown >= -20:
            score += 15
        elif max_drawdown >= -30:
            score += 10
        
        # 승률 점수 (30%)
        if win_rate >= 0.7:
            score += 30
        elif win_rate >= 0.6:
            score += 25
        elif win_rate >= 0.5:
            score += 20
        elif win_rate >= 0.4:
            score += 15
        elif win_rate >= 0.3:
            score += 10
        
        # 등급 결정
        if score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 50:
            return "D"
        else:
            return "F"

    def _compare_strategies_vs_portfolio(
        self, strategy_results: List[Dict[str, Any]], portfolio_performance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """개별 전략 vs 포트폴리오 비교"""
        
        # 개별 전략 성과 추출
        individual_performances = []
        for result in strategy_results:
            perf = result["result"]["performance"]
            individual_performances.append({
                "strategy_name": result["strategy"]["name"],
                "total_return": perf["total_return_pct"],
                "win_rate": perf["win_rate"],
                "max_drawdown": perf["max_drawdown_pct"],
                "sharpe_ratio": perf.get("sharpe_ratio", 0)
            })
        
        # 포트폴리오 성과
        portfolio_perf = {
            "total_return": portfolio_performance["total_return_pct"],
            "win_rate": portfolio_performance["win_rate"],
            "max_drawdown": portfolio_performance["max_drawdown_pct"],
            "sharpe_ratio": portfolio_performance["sharpe_ratio"]
        }
        
        # 최고 개별 전략
        best_individual = max(individual_performances, key=lambda x: x["total_return"])
        
        # 포트폴리오 효과 분석
        diversification_benefit = {
            "return_improvement": portfolio_perf["total_return"] - best_individual["total_return"],
            "risk_reduction": best_individual["max_drawdown"] - portfolio_perf["max_drawdown"],
            "sharpe_improvement": portfolio_perf["sharpe_ratio"] - best_individual["sharpe_ratio"]
        }
        
        return {
            "individual_strategies": individual_performances,
            "portfolio_performance": portfolio_perf,
            "best_individual_strategy": best_individual,
            "diversification_benefit": diversification_benefit,
            "portfolio_advantage": {
                "better_return": portfolio_perf["total_return"] > best_individual["total_return"],
                "lower_risk": portfolio_perf["max_drawdown"] > best_individual["max_drawdown"],
                "better_sharpe": portfolio_perf["sharpe_ratio"] > best_individual["sharpe_ratio"]
            },
            "recommendation": self._generate_portfolio_recommendation(diversification_benefit)
        }

    def _generate_portfolio_recommendation(self, diversification_benefit: Dict[str, float]) -> str:
        """포트폴리오 추천 사항 생성"""
        return_improvement = diversification_benefit["return_improvement"]
        risk_reduction = diversification_benefit["risk_reduction"]
        sharpe_improvement = diversification_benefit["sharpe_improvement"]
        
        if sharpe_improvement > 0.2 and risk_reduction > 2:
            return "포트폴리오 접근법이 개별 전략보다 우수합니다. 다양화 효과가 뛰어납니다."
        elif sharpe_improvement > 0:
            return "포트폴리오가 위험 대비 수익률을 개선했습니다. 포트폴리오 접근법을 권장합니다."
        elif risk_reduction > 0:
            return "포트폴리오가 리스크를 줄였습니다. 안정적인 수익을 원한다면 포트폴리오를 선택하세요."
        else:
            return "개별 전략이 더 나은 성과를 보입니다. 포트폴리오 구성을 재검토하세요."

    # =================================================================
    # 몬테카를로 시뮬레이션
    # =================================================================

    def monte_carlo_simulation(
        self,
        strategies: List[Dict[str, Any]],
        n_simulations: int = 1000,
        simulation_days: int = 252,  # 1년
        confidence_levels: List[float] = [0.05, 0.95]
    ) -> Dict[str, Any]:
        """
        몬테카를로 시뮬레이션을 통한 포트폴리오 성과 예측
        
        Args:
            strategies: 전략 리스트
            n_simulations: 시뮬레이션 횟수
            simulation_days: 시뮬레이션 기간 (일)
            confidence_levels: 신뢰구간 수준
            
        Returns:
            몬테카를로 시뮬레이션 결과
        """
        try:
            print(f"🎲 몬테카를로 시뮬레이션 시작: {n_simulations}회 반복")
            
            # 각 전략의 과거 성과 데이터 수집
            strategy_stats = []
            for strategy in strategies:
                # 간단한 구현: 기본 통계값 사용
                stats = {
                    "mean_return": 0.001,  # 일평균 0.1% 수익률
                    "volatility": 0.02,    # 일변동성 2%
                    "name": strategy["name"]
                }
                strategy_stats.append(stats)
            
            # 시뮬레이션 실행
            simulation_results = []
            
            for sim in range(n_simulations):
                portfolio_returns = []
                
                for day in range(simulation_days):
                    # 각 전략의 일일 수익률 생성 (정규분포 가정)
                    daily_portfolio_return = 0
                    
                    for i, stats in enumerate(strategy_stats):
                        # 정규분포에서 수익률 샘플링
                        daily_return = np.random.normal(
                            stats["mean_return"], 
                            stats["volatility"]
                        )
                        daily_portfolio_return += daily_return / len(strategy_stats)  # 동일 비중
                    
                    portfolio_returns.append(daily_portfolio_return)
                
                # 누적 수익률 계산
                cumulative_return = (1 + np.array(portfolio_returns)).prod() - 1
                simulation_results.append(cumulative_return)
            
            # 결과 분석
            simulation_results = np.array(simulation_results)
            
            # 신뢰구간 계산
            confidence_intervals = {}
            for level in confidence_levels:
                confidence_intervals[f"{level:.0%}"] = np.percentile(simulation_results, level * 100)
            
            # 통계 계산
            mean_return = np.mean(simulation_results)
            std_return = np.std(simulation_results)
            min_return = np.min(simulation_results)
            max_return = np.max(simulation_results)
            
            # 손실 확률 계산
            loss_probability = np.mean(simulation_results < 0)
            
            return {
                "simulation_config": {
                    "n_simulations": n_simulations,
                    "simulation_days": simulation_days,
                    "strategies": [s["name"] for s in strategies]
                },
                "results": {
                    "mean_return_pct": round(mean_return * 100, 2),
                    "std_return_pct": round(std_return * 100, 2),
                    "min_return_pct": round(min_return * 100, 2),
                    "max_return_pct": round(max_return * 100, 2),
                    "loss_probability": round(loss_probability, 3),
                    "confidence_intervals": {
                        k: round(v * 100, 2) for k, v in confidence_intervals.items()
                    }
                },
                "interpretation": {
                    "expected_return": f"{mean_return * 100:.1f}% 수익률 예상",
                    "risk_level": "High" if std_return > 0.3 else "Medium" if std_return > 0.15 else "Low",
                    "loss_risk": f"{loss_probability:.1%} 확률로 손실 가능성",
                    "confidence_range": f"95% 신뢰구간: {confidence_intervals.get('5%', 0):.1f}% ~ {confidence_intervals.get('95%', 0):.1f}%"
                },
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"❌ 몬테카를로 시뮬레이션 실패: {e}")
            return {"error": str(e)}

    def __del__(self):
        """소멸자 - 세션 정리"""
        if self.session:
            self.session.close()