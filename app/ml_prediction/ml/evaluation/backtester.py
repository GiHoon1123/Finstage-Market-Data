"""
백테스팅 시스템

이 파일은 ML 모델의 과거 데이터를 사용한 백테스팅을 수행하는 클래스를 구현합니다.
실제 거래 시뮬레이션을 통해 모델의 실전 성능을 평가합니다.

주요 기능:
- 과거 데이터 기반 예측 시뮬레이션
- 거래 전략 백테스팅
- 수익률 및 리스크 분석
- 성능 지표 계산
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime, timedelta
import numpy as np
import pandas as pd
from dataclasses import dataclass

from app.ml_prediction.ml.model.lstm_model import MultiOutputLSTMPredictor
from app.ml_prediction.ml.data.preprocessor import MLDataPreprocessor
from app.ml_prediction.infra.model.repository.ml_model_repository import (
    MLModelRepository,
)
from app.technical_analysis.infra.model.repository.daily_price_repository import (
    DailyPriceRepository,
)
from app.common.infra.database.config.database_config import SessionLocal
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class BacktestConfig:
    """백테스트 설정"""

    initial_capital: float = 100000.0  # 초기 자본
    position_size: float = 0.1  # 포지션 크기 (자본의 10%)
    transaction_cost: float = 0.001  # 거래 비용 (0.1%)
    confidence_threshold: float = 0.6  # 거래 실행 최소 신뢰도
    stop_loss: float = 0.05  # 손절매 (5%)
    take_profit: float = 0.10  # 익절 (10%)
    max_holding_days: int = 30  # 최대 보유 일수


@dataclass
class Trade:
    """거래 정보"""

    entry_date: date
    exit_date: Optional[date]
    entry_price: float
    exit_price: Optional[float]
    position_size: float
    direction: str  # 'long' or 'short'
    predicted_price: float
    confidence_score: float
    timeframe: str
    is_closed: bool = False
    pnl: Optional[float] = None
    return_pct: Optional[float] = None


class Backtester:
    """
    백테스팅 시스템

    과거 데이터를 사용하여 ML 모델의 실전 성능을 시뮬레이션합니다.
    """

    def __init__(self, config: Optional[BacktestConfig] = None):
        """
        백테스터 초기화

        Args:
            config: 백테스트 설정
        """
        self.config = config or BacktestConfig()
        self.preprocessor = MLDataPreprocessor()

        # 백테스트 결과 저장
        self.backtest_results = {}

        logger.info(
            "backtester_initialized",
            initial_capital=self.config.initial_capital,
            position_size=self.config.position_size,
            confidence_threshold=self.config.confidence_threshold,
        )

    def run_backtest(
        self,
        symbol: str,
        model_version: str,
        start_date: date,
        end_date: date,
        strategy: str = "direction_based",
    ) -> Dict[str, Any]:
        """
        백테스트 실행

        Args:
            symbol: 심볼
            model_version: 모델 버전
            start_date: 백테스트 시작 날짜
            end_date: 백테스트 종료 날짜
            strategy: 거래 전략

        Returns:
            백테스트 결과
        """
        logger.info(
            "backtest_started",
            symbol=symbol,
            model_version=model_version,
            start_date=start_date,
            end_date=end_date,
            strategy=strategy,
        )

        try:
            # 1. 모델 로드
            model_predictor, model_entity = self._load_model(symbol, model_version)

            # 2. 백테스트 데이터 준비
            price_data = self._prepare_backtest_data(symbol, start_date, end_date)

            # 3. 예측 시뮬레이션
            predictions = self._simulate_predictions(
                model_predictor, symbol, price_data, start_date, end_date
            )

            # 4. 거래 시뮬레이션
            trades = self._simulate_trades(predictions, price_data, strategy)

            # 5. 성과 분석
            performance_metrics = self._calculate_performance_metrics(
                trades, price_data
            )

            # 6. 리스크 분석
            risk_metrics = self._calculate_risk_metrics(trades, price_data)

            # 7. 벤치마크 비교
            benchmark_comparison = self._compare_with_benchmark(
                trades, price_data, start_date, end_date
            )

            # 8. 결과 구성
            backtest_result = {
                "symbol": symbol,
                "model_version": model_version,
                "strategy": strategy,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "trading_days": len(price_data),
                },
                "config": {
                    "initial_capital": self.config.initial_capital,
                    "position_size": self.config.position_size,
                    "transaction_cost": self.config.transaction_cost,
                    "confidence_threshold": self.config.confidence_threshold,
                },
                "trades": {
                    "total_trades": len(trades),
                    "winning_trades": len([t for t in trades if t.pnl and t.pnl > 0]),
                    "losing_trades": len([t for t in trades if t.pnl and t.pnl < 0]),
                    "trade_details": [self._trade_to_dict(trade) for trade in trades],
                },
                "performance_metrics": performance_metrics,
                "risk_metrics": risk_metrics,
                "benchmark_comparison": benchmark_comparison,
                "backtest_timestamp": datetime.now().isoformat(),
            }

            # 캐시에 저장
            cache_key = f"{symbol}_{model_version}_{start_date}_{end_date}_{strategy}"
            self.backtest_results[cache_key] = backtest_result

            logger.info(
                "backtest_completed",
                symbol=symbol,
                model_version=model_version,
                total_trades=len(trades),
                total_return=performance_metrics.get("total_return_pct", 0),
                sharpe_ratio=risk_metrics.get("sharpe_ratio", 0),
            )

            return backtest_result

        except Exception as e:
            logger.error(
                "backtest_failed",
                symbol=symbol,
                model_version=model_version,
                error=str(e),
            )
            raise

    def _load_model(
        self, symbol: str, model_version: str
    ) -> Tuple[MultiOutputLSTMPredictor, Any]:
        """모델 로드"""
        session = SessionLocal()
        model_repo = MLModelRepository(session)

        try:
            model_name = f"{symbol.replace('^', '')}_lstm"
            model_entity = model_repo.find_by_name_and_version(
                model_name, model_version
            )

            if not model_entity:
                raise ValueError(
                    f"Model {model_name} version {model_version} not found"
                )

            # 모델 로드
            model_predictor = MultiOutputLSTMPredictor(
                input_shape=(60, 0),  # 실제 크기는 로드 시 결정
                model_name=model_entity.model_name,
            )

            model_predictor.load_model(model_entity.model_path)

            # 스케일러 로드
            import os

            scaler_dir = os.path.join(
                os.path.dirname(model_entity.model_path), "scalers"
            )
            if os.path.exists(scaler_dir):
                self.preprocessor.feature_engineer.load_scalers(scaler_dir)

            return model_predictor, model_entity

        finally:
            session.close()

    def _prepare_backtest_data(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """백테스트 데이터 준비"""
        session = SessionLocal()
        price_repo = DailyPriceRepository(session)

        try:
            # 모델 윈도우 크기만큼 추가로 과거 데이터 필요
            extended_start = start_date - timedelta(days=90)  # 여유분 포함

            daily_prices = price_repo.find_by_symbol_and_date_range(
                symbol=symbol,
                start_date=extended_start,
                end_date=end_date,
                order_desc=False,
            )

            if not daily_prices:
                raise ValueError(f"No price data found for {symbol}")

            # DataFrame 변환
            data_list = []
            for price in daily_prices:
                data_list.append(
                    {
                        "date": price.date,
                        "open": float(price.open_price),
                        "high": float(price.high_price),
                        "low": float(price.low_price),
                        "close": float(price.close_price),
                        "volume": price.volume or 0,
                    }
                )

            df = pd.DataFrame(data_list)
            df.set_index("date", inplace=True)
            df.sort_index(inplace=True)

            return df

        finally:
            session.close()

    def _simulate_predictions(
        self,
        model_predictor: MultiOutputLSTMPredictor,
        symbol: str,
        price_data: pd.DataFrame,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        """예측 시뮬레이션"""
        predictions = []

        # 백테스트 기간의 각 날짜에 대해 예측 수행
        current_date = start_date

        while current_date <= end_date:
            try:
                # 해당 날짜까지의 데이터로 예측 수행
                if current_date in price_data.index:
                    # 예측용 데이터 준비
                    X_pred, data_metadata = self.preprocessor.prepare_prediction_data(
                        symbol=symbol, end_date=current_date
                    )

                    # 예측 실행
                    raw_predictions = model_predictor.predict(X_pred)

                    # 역정규화
                    denormalized_predictions = (
                        self.preprocessor.feature_engineer.denormalize_predictions(
                            raw_predictions
                        )
                    )

                    # 각 타임프레임별 예측 저장
                    current_price = float(price_data.loc[current_date, "close"])

                    for timeframe, predicted_price in denormalized_predictions.items():
                        days = int(timeframe.replace("d", ""))
                        target_date = current_date + timedelta(days=days)

                        # 가격 변화율 계산
                        price_change_pct = (
                            (predicted_price[0] - current_price) / current_price
                        ) * 100

                        # 예측 방향
                        if price_change_pct > 0.5:
                            direction = "up"
                        elif price_change_pct < -0.5:
                            direction = "down"
                        else:
                            direction = "neutral"

                        predictions.append(
                            {
                                "prediction_date": current_date,
                                "target_date": target_date,
                                "timeframe": timeframe,
                                "current_price": current_price,
                                "predicted_price": float(predicted_price[0]),
                                "predicted_direction": direction,
                                "price_change_pct": price_change_pct,
                                "confidence_score": 0.7,  # 간단화된 신뢰도
                            }
                        )

                current_date += timedelta(days=1)

            except Exception as e:
                logger.debug(
                    "prediction_simulation_error", date=current_date, error=str(e)
                )
                current_date += timedelta(days=1)
                continue

        logger.info(
            "prediction_simulation_completed",
            symbol=symbol,
            predictions_generated=len(predictions),
        )

        return predictions

    def _simulate_trades(
        self, predictions: List[Dict[str, Any]], price_data: pd.DataFrame, strategy: str
    ) -> List[Trade]:
        """거래 시뮬레이션"""
        trades = []
        open_positions = []

        for pred in predictions:
            prediction_date = pred["prediction_date"]

            # 신뢰도 필터링
            if pred["confidence_score"] < self.config.confidence_threshold:
                continue

            # 전략에 따른 거래 결정
            if strategy == "direction_based":
                trade_signal = self._direction_based_strategy(pred)
            else:
                continue

            if trade_signal:
                # 새로운 거래 생성
                trade = Trade(
                    entry_date=prediction_date,
                    exit_date=None,
                    entry_price=pred["current_price"],
                    exit_price=None,
                    position_size=self.config.initial_capital
                    * self.config.position_size,
                    direction=trade_signal,
                    predicted_price=pred["predicted_price"],
                    confidence_score=pred["confidence_score"],
                    timeframe=pred["timeframe"],
                )

                open_positions.append(trade)
                trades.append(trade)

            # 기존 포지션 관리
            self._manage_open_positions(open_positions, prediction_date, price_data)

        # 남은 포지션 정리
        final_date = price_data.index[-1]
        for position in open_positions:
            if not position.is_closed:
                self._close_position(position, final_date, price_data)

        return trades

    def _direction_based_strategy(self, prediction: Dict[str, Any]) -> Optional[str]:
        """방향 기반 거래 전략"""
        direction = prediction["predicted_direction"]
        price_change_pct = abs(prediction["price_change_pct"])

        # 최소 변화율 필터 (1% 이상)
        if price_change_pct < 1.0:
            return None

        if direction == "up":
            return "long"
        elif direction == "down":
            return "short"
        else:
            return None

    def _manage_open_positions(
        self, open_positions: List[Trade], current_date: date, price_data: pd.DataFrame
    ) -> None:
        """열린 포지션 관리"""
        if current_date not in price_data.index:
            return

        current_price = float(price_data.loc[current_date, "close"])

        positions_to_close = []

        for position in open_positions:
            if position.is_closed:
                continue

            # 보유 기간 확인
            holding_days = (current_date - position.entry_date).days
            if holding_days >= self.config.max_holding_days:
                positions_to_close.append(position)
                continue

            # 손절매/익절 확인
            if position.direction == "long":
                return_pct = (
                    current_price - position.entry_price
                ) / position.entry_price
            else:  # short
                return_pct = (
                    position.entry_price - current_price
                ) / position.entry_price

            if (
                return_pct <= -self.config.stop_loss
                or return_pct >= self.config.take_profit
            ):
                positions_to_close.append(position)

        # 포지션 정리
        for position in positions_to_close:
            self._close_position(position, current_date, price_data)
            open_positions.remove(position)

    def _close_position(
        self, position: Trade, exit_date: date, price_data: pd.DataFrame
    ) -> None:
        """포지션 정리"""
        if exit_date not in price_data.index:
            # 가장 가까운 거래일 찾기
            available_dates = [d for d in price_data.index if d <= exit_date]
            if available_dates:
                exit_date = max(available_dates)
            else:
                return

        exit_price = float(price_data.loc[exit_date, "close"])

        position.exit_date = exit_date
        position.exit_price = exit_price
        position.is_closed = True

        # 수익률 계산
        if position.direction == "long":
            return_pct = (exit_price - position.entry_price) / position.entry_price
        else:  # short
            return_pct = (position.entry_price - exit_price) / position.entry_price

        # 거래 비용 차감
        return_pct -= self.config.transaction_cost * 2  # 매수/매도

        position.return_pct = return_pct
        position.pnl = position.position_size * return_pct

    def _calculate_performance_metrics(
        self, trades: List[Trade], price_data: pd.DataFrame
    ) -> Dict[str, float]:
        """성과 지표 계산"""
        if not trades:
            return {}

        closed_trades = [t for t in trades if t.is_closed and t.pnl is not None]

        if not closed_trades:
            return {"total_trades": len(trades), "closed_trades": 0}

        # 기본 통계
        total_pnl = sum(t.pnl for t in closed_trades)
        total_return_pct = (total_pnl / self.config.initial_capital) * 100

        winning_trades = [t for t in closed_trades if t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl < 0]

        win_rate = len(winning_trades) / len(closed_trades) if closed_trades else 0

        # 평균 수익/손실
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0

        # 수익 팩터
        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))
        profit_factor = total_wins / total_losses if total_losses > 0 else float("inf")

        return {
            "total_trades": len(trades),
            "closed_trades": len(closed_trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "total_return_pct": total_return_pct,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "avg_return_per_trade": (
                total_pnl / len(closed_trades) if closed_trades else 0
            ),
        }

    def _calculate_risk_metrics(
        self, trades: List[Trade], price_data: pd.DataFrame
    ) -> Dict[str, float]:
        """리스크 지표 계산"""
        closed_trades = [t for t in trades if t.is_closed and t.return_pct is not None]

        if not closed_trades:
            return {}

        returns = [t.return_pct for t in closed_trades]

        # 기본 통계
        avg_return = np.mean(returns)
        std_return = np.std(returns)

        # 샤프 비율 (무위험 수익률 0으로 가정)
        sharpe_ratio = avg_return / std_return if std_return > 0 else 0

        # 최대 낙폭 계산
        cumulative_returns = np.cumprod([1 + r for r in returns])
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = np.min(drawdowns)

        # VaR (95% 신뢰구간)
        var_95 = np.percentile(returns, 5)

        return {
            "avg_return": avg_return,
            "volatility": std_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "var_95": var_95,
            "calmar_ratio": avg_return / abs(max_drawdown) if max_drawdown < 0 else 0,
        }

    def _compare_with_benchmark(
        self,
        trades: List[Trade],
        price_data: pd.DataFrame,
        start_date: date,
        end_date: date,
    ) -> Dict[str, float]:
        """벤치마크 비교"""
        # 단순 매수 후 보유 전략과 비교
        start_price = float(price_data.loc[start_date, "close"])
        end_price = float(price_data.loc[end_date, "close"])

        benchmark_return = (end_price - start_price) / start_price

        closed_trades = [t for t in trades if t.is_closed and t.pnl is not None]
        strategy_return = (
            sum(t.return_pct for t in closed_trades) / len(closed_trades)
            if closed_trades
            else 0
        )

        excess_return = strategy_return - benchmark_return

        return {
            "benchmark_return": benchmark_return,
            "strategy_return": strategy_return,
            "excess_return": excess_return,
            "outperformed": excess_return > 0,
        }

    def _trade_to_dict(self, trade: Trade) -> Dict[str, Any]:
        """거래를 딕셔너리로 변환"""
        return {
            "entry_date": trade.entry_date.isoformat(),
            "exit_date": trade.exit_date.isoformat() if trade.exit_date else None,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "direction": trade.direction,
            "timeframe": trade.timeframe,
            "predicted_price": trade.predicted_price,
            "confidence_score": trade.confidence_score,
            "is_closed": trade.is_closed,
            "pnl": trade.pnl,
            "return_pct": trade.return_pct,
        }

    def get_backtest_results(self, cache_key: Optional[str] = None) -> Dict[str, Any]:
        """백테스트 결과 반환"""
        if cache_key:
            return self.backtest_results.get(cache_key, {})
        else:
            return self.backtest_results

    def clear_backtest_cache(self) -> None:
        """백테스트 캐시 초기화"""
        self.backtest_results.clear()
        logger.info("backtest_cache_cleared")
