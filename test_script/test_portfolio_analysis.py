#!/usr/bin/env python3
"""
포트폴리오 기술적 분석 스크립트

여러 종목을 동시에 분석하여 포트폴리오 관점에서 투자 기회 발굴
- 섹터별 분석
- 상관관계 분석
- 포트폴리오 최적화
- 리스크 분산 분석
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
from app.technical_analysis.service.technical_monitor_service import (
    TechnicalMonitorService,
)


class PortfolioAnalyzer:
    """포트폴리오 분석기"""

    def __init__(self):
        self.yahoo_client = YahooPriceClient()
        self.indicator_service = TechnicalIndicatorService()
        self.monitor_service = TechnicalMonitorService()

        # 분석 대상 포트폴리오 정의
        self.portfolios = {
            "tech_giants": {
                "name": "빅테크 포트폴리오",
                "symbols": {
                    "AAPL": "Apple",
                    "MSFT": "Microsoft",
                    "GOOGL": "Alphabet",
                    "AMZN": "Amazon",
                    "TSLA": "Tesla",
                },
            },
            "etf_portfolio": {
                "name": "ETF 포트폴리오",
                "symbols": {
                    "QQQ": "나스닥 ETF",
                    "SPY": "S&P 500 ETF",
                    "IWM": "러셀 2000 ETF",
                    "VTI": "전체 시장 ETF",
                    "ARKK": "혁신 기술 ETF",
                },
            },
            "market_indices": {
                "name": "주요 지수",
                "symbols": {
                    "^IXIC": "나스닥 종합",
                    "^GSPC": "S&P 500",
                    "^DJI": "다우존스",
                    "^RUT": "러셀 2000",
                    "^VIX": "변동성 지수",
                },
            },
        }

    def analyze_portfolio_signals(self, portfolio_key: str) -> Dict[str, Any]:
        """포트폴리오 신호 분석"""
        if portfolio_key not in self.portfolios:
            print(f"❌ 포트폴리오 '{portfolio_key}' 없음")
            return {}

        portfolio = self.portfolios[portfolio_key]
        portfolio_name = portfolio["name"]
        symbols = portfolio["symbols"]

        print(f"📊 {portfolio_name} 신호 분석 시작")
        print(f"🎯 분석 종목: {len(symbols)}개")

        results = {}
        signal_summary = {"bullish": [], "bearish": [], "neutral": []}

        for symbol, name in symbols.items():
            print(f"\n🔍 {symbol} ({name}) 분석 중...")

            try:
                # 종합 신호 분석
                comprehensive_result = (
                    self.monitor_service.monitor_comprehensive_signals(symbol)
                )

                if comprehensive_result:
                    current_price = comprehensive_result["current_price"]
                    price_change_pct = comprehensive_result["price_change_pct"]
                    signals = comprehensive_result.get("signals", {})

                    # 시장 심리 분석
                    sentiment_result = self.monitor_service.monitor_market_sentiment(
                        symbol
                    )

                    # 결과 저장
                    results[symbol] = {
                        "name": name,
                        "current_price": current_price,
                        "price_change_pct": price_change_pct,
                        "signals": signals,
                        "sentiment": sentiment_result,
                        "indicators": comprehensive_result.get("indicators", {}),
                    }

                    # 신호 분류
                    if sentiment_result:
                        sentiment_ratio = sentiment_result["ratio"]
                        if sentiment_ratio >= 0.7:
                            signal_summary["bullish"].append(symbol)
                        elif sentiment_ratio <= 0.3:
                            signal_summary["bearish"].append(symbol)
                        else:
                            signal_summary["neutral"].append(symbol)

                    print(
                        f"  💰 현재가: {current_price:.2f} ({price_change_pct:+.2f}%)"
                    )
                    print(f"  🔔 신호: {len(signals)}개")
                    if sentiment_result:
                        print(
                            f"  🧠 심리: {sentiment_result['sentiment']} {sentiment_result['emoji']}"
                        )

            except Exception as e:
                print(f"  ❌ {symbol} 분석 실패: {e}")
                results[symbol] = {"error": str(e)}

        return {
            "portfolio_name": portfolio_name,
            "results": results,
            "signal_summary": signal_summary,
            "analysis_time": datetime.now(),
        }

    def calculate_portfolio_correlation(
        self, portfolio_key: str, period: str = "6mo"
    ) -> Dict[str, Any]:
        """포트폴리오 상관관계 분석"""
        if portfolio_key not in self.portfolios:
            return {}

        portfolio = self.portfolios[portfolio_key]
        symbols = list(portfolio["symbols"].keys())

        print(f"\n📊 {portfolio['name']} 상관관계 분석")

        # 가격 데이터 수집
        price_data = {}
        for symbol in symbols:
            try:
                df = self.yahoo_client.get_daily_data(symbol, period=period)
                if df is not None and len(df) > 50:
                    price_data[symbol] = df["Close"].pct_change().dropna()
                    print(f"  ✅ {symbol}: {len(price_data[symbol])}일 데이터")
                else:
                    print(f"  ❌ {symbol}: 데이터 부족")
            except Exception as e:
                print(f"  ❌ {symbol}: {e}")

        if len(price_data) < 2:
            print("❌ 상관관계 분석을 위한 데이터 부족")
            return {}

        # 상관관계 매트릭스 계산
        returns_df = pd.DataFrame(price_data)
        correlation_matrix = returns_df.corr()

        # 평균 상관관계
        avg_correlation = correlation_matrix.values[
            np.triu_indices_from(correlation_matrix.values, k=1)
        ].mean()

        # 가장 높은/낮은 상관관계 찾기
        corr_pairs = []
        for i in range(len(correlation_matrix.columns)):
            for j in range(i + 1, len(correlation_matrix.columns)):
                symbol1 = correlation_matrix.columns[i]
                symbol2 = correlation_matrix.columns[j]
                corr_value = correlation_matrix.iloc[i, j]
                corr_pairs.append((symbol1, symbol2, corr_value))

        # 정렬
        corr_pairs.sort(key=lambda x: abs(x[2]), reverse=True)

        return {
            "portfolio_name": portfolio["name"],
            "correlation_matrix": correlation_matrix,
            "average_correlation": avg_correlation,
            "highest_correlation": corr_pairs[0] if corr_pairs else None,
            "lowest_correlation": corr_pairs[-1] if corr_pairs else None,
            "all_correlations": corr_pairs,
        }

    def analyze_sector_rotation(self) -> Dict[str, Any]:
        """섹터 로테이션 분석"""
        print("\n🔄 섹터 로테이션 분석")

        # 섹터 ETF들
        sector_etfs = {
            "XLK": "기술",
            "XLF": "금융",
            "XLV": "헬스케어",
            "XLE": "에너지",
            "XLI": "산업",
            "XLY": "소비재",
            "XLP": "필수소비재",
            "XLU": "유틸리티",
            "XLB": "소재",
            "XLRE": "부동산",
        }

        sector_performance = {}

        for symbol, sector_name in sector_etfs.items():
            try:
                # 최근 1개월, 3개월, 6개월 성과 계산
                df_1m = self.yahoo_client.get_daily_data(symbol, period="1mo")
                df_3m = self.yahoo_client.get_daily_data(symbol, period="3mo")
                df_6m = self.yahoo_client.get_daily_data(symbol, period="6mo")

                performance = {}

                if df_1m is not None and len(df_1m) >= 2:
                    performance["1m"] = (
                        (df_1m["Close"].iloc[-1] / df_1m["Close"].iloc[0]) - 1
                    ) * 100

                if df_3m is not None and len(df_3m) >= 2:
                    performance["3m"] = (
                        (df_3m["Close"].iloc[-1] / df_3m["Close"].iloc[0]) - 1
                    ) * 100

                if df_6m is not None and len(df_6m) >= 2:
                    performance["6m"] = (
                        (df_6m["Close"].iloc[-1] / df_6m["Close"].iloc[0]) - 1
                    ) * 100

                # 기술적 신호 분석
                signals = self.monitor_service.monitor_comprehensive_signals(symbol)
                sentiment = self.monitor_service.monitor_market_sentiment(symbol)

                sector_performance[symbol] = {
                    "name": sector_name,
                    "performance": performance,
                    "signals": signals.get("signals", {}) if signals else {},
                    "sentiment": sentiment,
                }

                print(
                    f"  📊 {sector_name} ({symbol}): "
                    f"1M {performance.get('1m', 0):+.1f}%, "
                    f"3M {performance.get('3m', 0):+.1f}%, "
                    f"6M {performance.get('6m', 0):+.1f}%"
                )

            except Exception as e:
                print(f"  ❌ {sector_name} ({symbol}): {e}")

        # 성과 순위
        rankings = {}
        for period in ["1m", "3m", "6m"]:
            period_data = [
                (symbol, data["performance"].get(period, 0))
                for symbol, data in sector_performance.items()
                if period in data["performance"]
            ]
            period_data.sort(key=lambda x: x[1], reverse=True)
            rankings[period] = period_data

        return {
            "sector_performance": sector_performance,
            "rankings": rankings,
            "analysis_time": datetime.now(),
        }

    def generate_portfolio_report(self, portfolio_key: str):
        """포트폴리오 종합 리포트 생성"""
        print(f"\n📋 {self.portfolios[portfolio_key]['name']} 종합 리포트")
        print("=" * 60)

        # 1. 신호 분석
        signal_analysis = self.analyze_portfolio_signals(portfolio_key)

        if signal_analysis:
            print(f"\n🔔 신호 분석 결과:")
            signal_summary = signal_analysis["signal_summary"]
            print(f"  📈 강세 종목: {len(signal_summary['bullish'])}개")
            if signal_summary["bullish"]:
                for symbol in signal_summary["bullish"]:
                    name = signal_analysis["results"][symbol]["name"]
                    price_change = signal_analysis["results"][symbol][
                        "price_change_pct"
                    ]
                    print(f"    - {symbol} ({name}): {price_change:+.2f}%")

            print(f"  📉 약세 종목: {len(signal_summary['bearish'])}개")
            if signal_summary["bearish"]:
                for symbol in signal_summary["bearish"]:
                    name = signal_analysis["results"][symbol]["name"]
                    price_change = signal_analysis["results"][symbol][
                        "price_change_pct"
                    ]
                    print(f"    - {symbol} ({name}): {price_change:+.2f}%")

            print(f"  � 중립 종목: {len(signal_summary['neutral'])}개")

        # 2. 상관관계 분석
        correlation_analysis = self.calculate_portfolio_correlation(portfolio_key)

        if correlation_analysis:
            print(f"\n📊 상관관계 분석:")
            print(f"  평균 상관관계: {correlation_analysis['average_correlation']:.3f}")

            if correlation_analysis["highest_correlation"]:
                high_corr = correlation_analysis["highest_correlation"]
                print(
                    f"  최고 상관관계: {high_corr[0]} - {high_corr[1]} ({high_corr[2]:.3f})"
                )

            if correlation_analysis["lowest_correlation"]:
                low_corr = correlation_analysis["lowest_correlation"]
                print(
                    f"  최저 상관관계: {low_corr[0]} - {low_corr[1]} ({low_corr[2]:.3f})"
                )

        # 3. 투자 추천
        print(f"\n💡 투자 추천:")
        if signal_analysis:
            bullish_count = len(signal_summary["bullish"])
            total_count = len(signal_analysis["results"])

            if bullish_count / total_count >= 0.6:
                recommendation = "적극 매수 🚀"
            elif bullish_count / total_count >= 0.4:
                recommendation = "선별 매수 📈"
            elif bullish_count / total_count >= 0.2:
                recommendation = "관망 🔄"
            else:
                recommendation = "주의 📉"

            print(f"  포트폴리오 전망: {recommendation}")
            print(
                f"  강세 비율: {bullish_count}/{total_count} ({bullish_count/total_count:.1%})"
            )

    def print_correlation_matrix(self, correlation_analysis: Dict[str, Any]):
        """상관관계 매트릭스 출력"""
        if not correlation_analysis or "correlation_matrix" not in correlation_analysis:
            return

        corr_matrix = correlation_analysis["correlation_matrix"]

        print(f"\n📊 {correlation_analysis['portfolio_name']} 상관관계 매트릭스:")
        print("-" * 60)

        # 헤더 출력
        symbols = corr_matrix.columns.tolist()
        header = "      " + "".join(f"{s:>8}" for s in symbols)
        print(header)

        # 매트릭스 출력
        for i, symbol in enumerate(symbols):
            row = f"{symbol:>6}"
            for j, corr_val in enumerate(corr_matrix.iloc[i]):
                if i == j:
                    row += f"{'1.000':>8}"
                elif j > i:
                    row += f"{corr_val:>8.3f}"
                else:
                    row += f"{'':>8}"
            print(row)


def main():
    """메인 함수"""
    print("🚀 포트폴리오 기술적 분석 시스템")
    print("=" * 60)

    analyzer = PortfolioAnalyzer()

    try:
        # 1. 각 포트폴리오별 분석
        for portfolio_key in analyzer.portfolios.keys():
            analyzer.generate_portfolio_report(portfolio_key)
            print("\n" + "=" * 60)

        # 2. 섹터 로테이션 분석
        sector_analysis = analyzer.analyze_sector_rotation()

        if sector_analysis:
            print(f"\n🔄 섹터 로테이션 분석 결과")
            print("-" * 40)

            rankings = sector_analysis["rankings"]

            for period in ["1m", "3m", "6m"]:
                if period in rankings:
                    print(f"\n📊 {period.upper()} 섹터 성과 순위:")
                    for i, (symbol, performance) in enumerate(rankings[period][:5], 1):
                        sector_name = sector_analysis["sector_performance"][symbol][
                            "name"
                        ]
                        print(f"  {i}. {sector_name} ({symbol}): {performance:+.1f}%")

        # 3. 상관관계 매트릭스 출력 (ETF 포트폴리오)
        etf_correlation = analyzer.calculate_portfolio_correlation("etf_portfolio")
        analyzer.print_correlation_matrix(etf_correlation)

        print(f"\n✅ 포트폴리오 분석 완료!")
        print(f"⏰ 분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    except Exception as e:
        print(f"❌ 포트폴리오 분석 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
