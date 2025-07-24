#!/usr/bin/env python3
"""
종합 기술적 분석 테스트 스크립트

시장 심리 분석, 일일 종합 분석 등 고급 기능 테스트
"""

import os
import sys
from datetime import datetime

# 상위 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.technical_analysis.service.technical_monitor_service import (
    TechnicalMonitorService,
)


def test_comprehensive_monitoring():
    """종합 기술적 지표 모니터링 테스트"""
    print("🧪 종합 기술적 지표 모니터링 테스트 시작")

    monitor_service = TechnicalMonitorService()

    # 나스닥 지수 종합 분석
    result = monitor_service.monitor_comprehensive_signals("^IXIC")

    if result:
        print("✅ 종합 모니터링 성공")

        # 주요 결과 출력
        signals = result.get("signals", {})
        indicators = result.get("indicators", {})

        print(f"\n📊 분석 결과 요약:")
        print(f"  감지된 신호: {len(signals)}개")
        print(f"  분석된 지표: {len(indicators)}개")

        if signals:
            print(f"\n🔔 활성 신호들:")
            for indicator, signal in signals.items():
                print(f"  - {indicator}: {signal}")
    else:
        print("❌ 종합 모니터링 실패")


def test_market_sentiment():
    """시장 심리 분석 테스트"""
    print("\n🧪 시장 심리 분석 테스트 시작")

    monitor_service = TechnicalMonitorService()

    # 나스닥 지수 시장 심리 분석
    sentiment_result = monitor_service.monitor_market_sentiment("^IXIC")

    if sentiment_result:
        print("✅ 시장 심리 분석 성공")

        print(f"\n🧠 시장 심리 결과:")
        print(
            f"  전체 심리: {sentiment_result['sentiment']} {sentiment_result['emoji']}"
        )
        print(
            f"  종합 점수: {sentiment_result['score']}/{sentiment_result['max_score']}"
        )
        print(f"  심리 비율: {sentiment_result['ratio']:.2%}")

        print(f"\n📊 개별 지표 점수:")
        for indicator, score in sentiment_result["individual_scores"].items():
            if score >= 1:
                status = "강세"
                emoji = "📈"
            elif score <= -1:
                status = "약세"
                emoji = "📉"
            else:
                status = "중립"
                emoji = "🔄"
            print(f"  {indicator.upper()}: {score:+2d} ({status} {emoji})")
    else:
        print("❌ 시장 심리 분석 실패")


def test_daily_analysis():
    """일일 종합 분석 테스트"""
    print("\n🧪 일일 종합 분석 테스트 시작")

    monitor_service = TechnicalMonitorService()

    # 일일 종합 분석 실행
    monitor_service.run_daily_comprehensive_analysis()

    print("✅ 일일 종합 분석 테스트 완료")


def test_multiple_symbols():
    """여러 심볼 분석 테스트"""
    print("\n🧪 여러 심볼 분석 테스트 시작")

    monitor_service = TechnicalMonitorService()
    symbols = ["^IXIC", "^GSPC"]  # 나스닥, S&P 500

    for symbol in symbols:
        print(f"\n📊 {symbol} 분석:")

        # 종합 분석
        result = monitor_service.monitor_comprehensive_signals(symbol)

        if result:
            current_price = result["current_price"]
            price_change_pct = result["price_change_pct"]
            signals = result.get("signals", {})

            print(f"  💰 현재가: {current_price:.2f} ({price_change_pct:+.2f}%)")
            print(f"  🔔 신호 수: {len(signals)}개")

            # 시장 심리도 함께 분석
            sentiment = monitor_service.monitor_market_sentiment(symbol)
            if sentiment:
                print(f"  🧠 시장 심리: {sentiment['sentiment']} {sentiment['emoji']}")


def main():
    """메인 함수"""
    print("🚀 종합 기술적 분석 테스트 시작")
    print(f"⏰ 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 1. 종합 모니터링 테스트
        test_comprehensive_monitoring()

        # 2. 시장 심리 분석 테스트
        test_market_sentiment()

        # 3. 여러 심볼 분석 테스트
        test_multiple_symbols()

        # 4. 일일 종합 분석 테스트 (마지막에 실행)
        test_daily_analysis()

        print("\n✅ 모든 종합 분석 테스트 완료!")

    except Exception as e:
        print(f"❌ 테스트 실행 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
