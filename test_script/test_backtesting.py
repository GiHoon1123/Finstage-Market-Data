#!/usr/bin/env python3
"""
기술적 지표 백테스팅 스크립트

과거 데이터를 사용하여 기술적 지표 전략의 성과를 검증
- 다양한 전략 백테스트
- 수익률 계산 및 분석
- 리스크 지표 계산
- 성과 리포트 생성
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import pandas as pd
import numpy as np

# 상위 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.common.infra.client.yahoo_price_client import YahooPriceClient
from app.technical_analysis.service.technical_indicator_service import (
    TechnicalIndicatorService,
)


class TechnicalBacktester:
    """기술적 지표 백테스터"""

    def __init__(self):
        self.yahoo_client = YahooPriceClient()
        self.indicator_service = TechnicalIndicatorService()

    def backtest_rsi_strategy(self, symbol: str, period: str = "2y") -> Dict[str, Any]:
        """RSI 전략 백테스트"""
        print(f"📊 {symbol} RSI 전략 백테스트 시작")

        # 데이터 가져오기
        df = self.yahoo_client.get_daily_data(symbol, period=period)
        if df is None or len(df) < 100:
            print(f"❌ {symbol} 데이터 부족")
            return {}

        # 컬럼명을 소문자로 변환
        df.columns = df.columns.str.lower()
        df = df.copy()

        # RSI 계산
        rsi = self.indicator_service.calculate_rsi(df["close"])
        if rsi.empty:
            return {}

        # RSI를 DataFrame에 추가
        df = df.iloc[len(df) - len(rsi) :].copy()  # RSI 길이에 맞춰 조정
        df["rsi"] = rsi.values

        # 전략 신호 생성
        df["signal"] = 0
        df.loc[df["rsi"] <= 30, "signal"] = 1  # 매수 신호 (과매도)
        df.loc[df["rsi"] >= 70, "signal"] = -1  # 매도 신호 (과매수)

        # 포지션 계산
        df["position"] = df["signal"].shift(1).fillna(0)  # 다음날 실행

        # 수익률 계산
        df["returns"] = df["close"].pct_change()
        df["strategy_returns"] = df["position"] * df["returns"]

        # 누적 수익률
        df["cumulative_returns"] = (1 + df["returns"]).cumprod()
        df["cumulative_strategy_returns"] = (1 + df["strategy_returns"]).cumprod()

        # 성과 지표 계산
        total_return = df["cumulative_strategy_returns"].iloc[-1] - 1
        benchmark_return = df["cumulative_returns"].iloc[-1] - 1

        # 연간 수익률
        days = len(df)
        annual_return = (1 + total_return) ** (252 / days) - 1
        annual_benchmark = (1 + benchmark_return) ** (252 / days) - 1

        # 변동성 (연간)
        strategy_vol = df["strategy_returns"].std() * np.sqrt(252)
        benchmark_vol = df["returns"].std() * np.sqrt(252)

        # 샤프 비율 (무위험 수익률 0% 가정)
        sharpe_ratio = annual_return / strategy_vol if strategy_vol > 0 else 0

        # 최대 낙폭 (Maximum Drawdown)
        rolling_max = df["cumulative_strategy_returns"].expanding().max()
        drawdown = (df["cumulative_strategy_returns"] - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        # 거래 횟수
        trades = (df["position"].diff() != 0).sum()

        return {
            "strategy": "RSI",
            "symbol": symbol,
            "period": period,
            "total_return": total_return,
            "benchmark_return": benchmark_return,
            "annual_return": annual_return,
            "annual_benchmark": annual_benchmark,
            "volatility": strategy_vol,
            "benchmark_volatility": benchmark_vol,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "trades": trades,
            "win_rate": self.calculate_win_rate(df),
            "data": df,
        }

    def backtest_macd_strategy(self, symbol: str, period: str = "2y") -> Dict[str, Any]:
        """MACD 전략 백테스트"""
        print(f"📊 {symbol} MACD 전략 백테스트 시작")

        # 데이터 가져오기
        df = self.yahoo_client.get_daily_data(symbol, period=period)
        if df is None or len(df) < 100:
            print(f"❌ {symbol} 데이터 부족")
            return {}

        # 컬럼명을 소문자로 변환
        df.columns = df.columns.str.lower()
        df = df.copy()

        # MACD 계산
        macd_data = self.indicator_service.calculate_macd(df["close"])
        if not macd_data:
            return {}

        # MACD를 DataFrame에 추가
        macd_df = pd.DataFrame(macd_data)
        df = df.iloc[len(df) - len(macd_df) :].copy()  # MACD 길이에 맞춰 조정
        df["macd"] = macd_df["macd"].values
        df["signal_line"] = macd_df["signal"].values
        df["histogram"] = macd_df["histogram"].values

        # 전략 신호 생성 (MACD 라인이 시그널 라인을 상향/하향 돌파)
        df["signal"] = 0
        df.loc[
            (df["macd"] > df["signal_line"])
            & (df["macd"].shift(1) <= df["signal_line"].shift(1)),
            "signal",
        ] = 1  # 매수
        df.loc[
            (df["macd"] < df["signal_line"])
            & (df["macd"].shift(1) >= df["signal_line"].shift(1)),
            "signal",
        ] = -1  # 매도

        # 포지션 계산
        df["position"] = df["signal"].shift(1).fillna(0)

        # 수익률 계산
        df["returns"] = df["close"].pct_change()
        df["strategy_returns"] = df["position"] * df["returns"]

        # 누적 수익률
        df["cumulative_returns"] = (1 + df["returns"]).cumprod()
        df["cumulative_strategy_returns"] = (1 + df["strategy_returns"]).cumprod()

        # 성과 지표 계산
        total_return = df["cumulative_strategy_returns"].iloc[-1] - 1
        benchmark_return = df["cumulative_returns"].iloc[-1] - 1

        # 연간 수익률
        days = len(df)
        annual_return = (1 + total_return) ** (252 / days) - 1
        annual_benchmark = (1 + benchmark_return) ** (252 / days) - 1

        # 변동성 (연간)
        strategy_vol = df["strategy_returns"].std() * np.sqrt(252)
        benchmark_vol = df["returns"].std() * np.sqrt(252)

        # 샤프 비율
        sharpe_ratio = annual_return / strategy_vol if strategy_vol > 0 else 0

        # 최대 낙폭
        rolling_max = df["cumulative_strategy_returns"].expanding().max()
        drawdown = (df["cumulative_strategy_returns"] - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        # 거래 횟수
        trades = (df["position"].diff() != 0).sum()

        return {
            "strategy": "MACD",
            "symbol": symbol,
            "period": period,
            "total_return": total_return,
            "benchmark_return": benchmark_return,
            "annual_return": annual_return,
            "annual_benchmark": annual_benchmark,
            "volatility": strategy_vol,
            "benchmark_volatility": benchmark_vol,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "trades": trades,
            "win_rate": self.calculate_win_rate(df),
            "data": df,
        }

    def backtest_moving_average_strategy(
        self,
        symbol: str,
        short_period: int = 20,
        long_period: int = 50,
        period: str = "2y",
    ) -> Dict[str, Any]:
        """이동평균 교차 전략 백테스트"""
        print(
            f"📊 {symbol} 이동평균 교차 전략 백테스트 시작 (SMA{short_period} vs SMA{long_period})"
        )

        # 데이터 가져오기
        df = self.yahoo_client.get_daily_data(symbol, period=period)
        if df is None or len(df) < max(short_period, long_period) + 50:
            print(f"❌ {symbol} 데이터 부족")
            return {}

        # 컬럼명을 소문자로 변환
        df.columns = df.columns.str.lower()
        df = df.copy()

        # 이동평균 계산
        short_ma = self.indicator_service.calculate_moving_average(
            df["close"], short_period, "SMA"
        )
        long_ma = self.indicator_service.calculate_moving_average(
            df["close"], long_period, "SMA"
        )

        if short_ma.empty or long_ma.empty:
            return {}

        # 데이터 길이 맞추기
        min_length = min(len(short_ma), len(long_ma))
        df = df.iloc[-min_length:].copy()
        df["short_ma"] = short_ma.iloc[-min_length:].values
        df["long_ma"] = long_ma.iloc[-min_length:].values

        # 전략 신호 생성 (골든 크로스/데드 크로스)
        df["signal"] = 0
        df.loc[
            (df["short_ma"] > df["long_ma"])
            & (df["short_ma"].shift(1) <= df["long_ma"].shift(1)),
            "signal",
        ] = 1  # 골든 크로스 (매수)
        df.loc[
            (df["short_ma"] < df["long_ma"])
            & (df["short_ma"].shift(1) >= df["long_ma"].shift(1)),
            "signal",
        ] = -1  # 데드 크로스 (매도)

        # 포지션 계산
        df["position"] = df["signal"].shift(1).fillna(0)

        # 수익률 계산
        df["returns"] = df["close"].pct_change()
        df["strategy_returns"] = df["position"] * df["returns"]

        # 누적 수익률
        df["cumulative_returns"] = (1 + df["returns"]).cumprod()
        df["cumulative_strategy_returns"] = (1 + df["strategy_returns"]).cumprod()

        # 성과 지표 계산
        total_return = df["cumulative_strategy_returns"].iloc[-1] - 1
        benchmark_return = df["cumulative_returns"].iloc[-1] - 1

        # 연간 수익률
        days = len(df)
        annual_return = (1 + total_return) ** (252 / days) - 1
        annual_benchmark = (1 + benchmark_return) ** (252 / days) - 1

        # 변동성 (연간)
        strategy_vol = df["strategy_returns"].std() * np.sqrt(252)
        benchmark_vol = df["returns"].std() * np.sqrt(252)

        # 샤프 비율
        sharpe_ratio = annual_return / strategy_vol if strategy_vol > 0 else 0

        # 최대 낙폭
        rolling_max = df["cumulative_strategy_returns"].expanding().max()
        drawdown = (df["cumulative_strategy_returns"] - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        # 거래 횟수
        trades = (df["position"].diff() != 0).sum()

        return {
            "strategy": f"MA_Cross_{short_period}_{long_period}",
            "symbol": symbol,
            "period": period,
            "total_return": total_return,
            "benchmark_return": benchmark_return,
            "annual_return": annual_return,
            "annual_benchmark": annual_benchmark,
            "volatility": strategy_vol,
            "benchmark_volatility": benchmark_vol,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "trades": trades,
            "win_rate": self.calculate_win_rate(df),
            "data": df,
        }

    def calculate_win_rate(self, df: pd.DataFrame) -> float:
        """승률 계산"""
        try:
            # 포지션 변화가 있는 지점 찾기
            position_changes = df["position"].diff() != 0

            if not position_changes.any():
                return 0.0

            # 거래별 수익률 계산
            trade_returns = []
            current_position = 0
            entry_price = 0

            for i, row in df.iterrows():
                if row["position"] != current_position:
                    if current_position != 0:  # 포지션 청산
                        if current_position > 0:  # 롱 포지션
                            trade_return = (row["close"] - entry_price) / entry_price
                        else:  # 숏 포지션
                            trade_return = (entry_price - row["close"]) / entry_price
                        trade_returns.append(trade_return)

                    if row["position"] != 0:  # 새 포지션 진입
                        entry_price = row["close"]

                    current_position = row["position"]

            if not trade_returns:
                return 0.0

            # 승률 계산
            winning_trades = sum(1 for ret in trade_returns if ret > 0)
            total_trades = len(trade_returns)

            return winning_trades / total_trades if total_trades > 0 else 0.0

        except Exception as e:
            print(f"승률 계산 오류: {e}")
            return 0.0

    def print_backtest_results(self, results: Dict[str, Any]):
        """백테스트 결과 출력"""
        if not results:
            print("❌ 백테스트 결과 없음")
            return

        print(f"\n📊 {results['strategy']} 전략 백테스트 결과")
        print("=" * 50)
        print(f"📈 종목: {results['symbol']}")
        print(f"📅 기간: {results['period']}")
        print(f"🎯 거래 횟수: {results['trades']}회")
        print(f"🏆 승률: {results['win_rate']:.1%}")

        print(f"\n💰 수익률:")
        print(f"  전략 수익률: {results['total_return']:+8.2%}")
        print(f"  벤치마크:   {results['benchmark_return']:+8.2%}")
        print(
            f"  초과 수익률: {results['total_return'] - results['benchmark_return']:+8.2%}"
        )

        print(f"\n📈 연간 수익률:")
        print(f"  전략:       {results['annual_return']:+8.2%}")
        print(f"  벤치마크:   {results['annual_benchmark']:+8.2%}")

        print(f"\n📊 리스크 지표:")
        print(f"  변동성:     {results['volatility']:8.2%}")
        print(f"  샤프 비율:  {results['sharpe_ratio']:8.2f}")
        print(f"  최대 낙폭:  {results['max_drawdown']:8.2%}")

        # 성과 평가
        if results["total_return"] > results["benchmark_return"]:
            performance = "우수 📈"
        elif results["total_return"] > 0:
            performance = "양호 🔼"
        else:
            performance = "부진 📉"

        print(f"\n🎯 종합 평가: {performance}")

    def compare_strategies(self, symbol: str, period: str = "2y"):
        """여러 전략 비교"""
        print(f"\n🔍 {symbol} 전략 비교 분석")
        print("=" * 60)

        strategies = []

        # 1. RSI 전략
        rsi_result = self.backtest_rsi_strategy(symbol, period)
        if rsi_result:
            strategies.append(rsi_result)

        # 2. MACD 전략
        macd_result = self.backtest_macd_strategy(symbol, period)
        if macd_result:
            strategies.append(macd_result)

        # 3. 이동평균 교차 전략들
        ma_configs = [(10, 20), (20, 50), (50, 200)]
        for short, long in ma_configs:
            ma_result = self.backtest_moving_average_strategy(
                symbol, short, long, period
            )
            if ma_result:
                strategies.append(ma_result)

        if not strategies:
            print("❌ 분석할 전략이 없습니다")
            return

        # 결과 비교 테이블
        print(f"\n📊 전략별 성과 비교")
        print("-" * 80)
        print(
            f"{'전략':<15} {'수익률':<10} {'연간수익률':<12} {'샤프비율':<10} {'최대낙폭':<10} {'승률':<8}"
        )
        print("-" * 80)

        for strategy in strategies:
            print(
                f"{strategy['strategy']:<15} "
                f"{strategy['total_return']:>8.1%} "
                f"{strategy['annual_return']:>10.1%} "
                f"{strategy['sharpe_ratio']:>8.2f} "
                f"{strategy['max_drawdown']:>8.1%} "
                f"{strategy['win_rate']:>6.1%}"
            )

        # 최고 성과 전략 찾기
        best_strategy = max(strategies, key=lambda x: x["sharpe_ratio"])
        print(f"\n🏆 최고 성과 전략: {best_strategy['strategy']}")
        print(f"   샤프 비율: {best_strategy['sharpe_ratio']:.2f}")
        print(f"   연간 수익률: {best_strategy['annual_return']:+.1%}")


def main():
    """메인 함수"""
    print("🚀 기술적 지표 백테스팅 시스템")
    print("=" * 60)

    backtester = TechnicalBacktester()

    # 테스트할 심볼들
    symbols = ["^IXIC", "QQQ", "SPY"]

    try:
        for symbol in symbols:
            print(f"\n🔍 {symbol} 백테스트 시작")

            # 개별 전략 테스트
            print(f"\n1️⃣ RSI 전략 테스트")
            rsi_result = backtester.backtest_rsi_strategy(symbol, "2y")
            backtester.print_backtest_results(rsi_result)

            print(f"\n2️⃣ MACD 전략 테스트")
            macd_result = backtester.backtest_macd_strategy(symbol, "2y")
            backtester.print_backtest_results(macd_result)

            print(f"\n3️⃣ 이동평균 교차 전략 테스트")
            ma_result = backtester.backtest_moving_average_strategy(
                symbol, 20, 50, "2y"
            )
            backtester.print_backtest_results(ma_result)

            # 전략 비교
            backtester.compare_strategies(symbol, "2y")

            print("\n" + "=" * 60)

        print("\n✅ 모든 백테스트 완료!")

    except Exception as e:
        print(f"❌ 백테스트 실행 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
