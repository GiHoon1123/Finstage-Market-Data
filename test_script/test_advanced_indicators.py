#!/usr/bin/env python3
"""
고급 기술적 지표 테스트 스크립트

MACD, 스토캐스틱, 거래량 지표, 종합 분석 테스트
"""

import os
import sys
from datetime import datetime

# 상위 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.common.infra.client.yahoo_price_client import YahooPriceClient
from app.technical_analysis.service.technical_indicator_service import (
    TechnicalIndicatorService,
)


def test_macd_indicator():
    """MACD 지표 테스트"""
    print("🧪 MACD 지표 테스트 시작")

    # 클라이언트 및 서비스 초기화
    yahoo_client = YahooPriceClient()
    indicator_service = TechnicalIndicatorService()

    # 나스닥 지수 데이터 가져오기
    symbol = "^IXIC"
    df = yahoo_client.get_daily_data(symbol, period="6mo")

    if df is None or len(df) < 50:
        print(f"❌ {symbol} 데이터 부족")
        return

    # 컬럼명을 소문자로 변환
    df.columns = df.columns.str.lower()

    current_price = df["close"].iloc[-1]
    print(f"💰 {symbol} 현재가: {current_price:.2f}")

    # MACD 계산
    macd_data = indicator_service.calculate_macd(df["close"])

    if macd_data:
        current_macd = macd_data["macd"].iloc[-1]
        current_signal = macd_data["signal"].iloc[-1]
        current_histogram = macd_data["histogram"].iloc[-1]

        print(f"\n📊 MACD 현재값:")
        print(f"  MACD Line  : {current_macd:8.4f}")
        print(f"  Signal Line: {current_signal:8.4f}")
        print(f"  Histogram  : {current_histogram:8.4f}")

        # MACD 신호 감지
        if len(macd_data["macd"]) >= 2:
            prev_macd = macd_data["macd"].iloc[-2]
            prev_signal = macd_data["signal"].iloc[-2]

            macd_signal = indicator_service.detect_macd_signals(
                current_macd, current_signal, prev_macd, prev_signal
            )

            if macd_signal:
                print(f"🔔 MACD 신호: {macd_signal}")
            else:
                print("🔄 MACD 특별한 신호 없음")

        # MACD 상태 분석
        if current_macd > current_signal:
            momentum = "상승"
            emoji = "📈"
        else:
            momentum = "하락"
            emoji = "📉"

        if current_macd > 0:
            trend = "상승 추세"
            trend_emoji = "🚀"
        else:
            trend = "하락 추세"
            trend_emoji = "📉"

        print(f"  {emoji} 모멘텀: {momentum}")
        print(f"  {trend_emoji} 추세: {trend}")


def test_stochastic_indicator():
    """스토캐스틱 지표 테스트"""
    print("\n🧪 스토캐스틱 지표 테스트 시작")

    # 클라이언트 및 서비스 초기화
    yahoo_client = YahooPriceClient()
    indicator_service = TechnicalIndicatorService()

    # 나스닥 지수 데이터 가져오기
    symbol = "^IXIC"
    df = yahoo_client.get_daily_data(symbol, period="3mo")

    if df is None or len(df) < 30:
        print(f"❌ {symbol} 데이터 부족")
        return

    # 컬럼명을 소문자로 변환
    df.columns = df.columns.str.lower()

    current_price = df["close"].iloc[-1]
    print(f"💰 {symbol} 현재가: {current_price:.2f}")

    # 스토캐스틱 계산
    stoch_data = indicator_service.calculate_stochastic(df)

    if stoch_data:
        current_k = stoch_data["k_percent"].iloc[-1]
        current_d = stoch_data["d_percent"].iloc[-1]

        print(f"\n📊 스토캐스틱 현재값:")
        print(f"  %K: {current_k:6.2f}")
        print(f"  %D: {current_d:6.2f}")

        # 스토캐스틱 신호 감지
        if len(stoch_data["k_percent"]) >= 2:
            prev_k = stoch_data["k_percent"].iloc[-2]
            prev_d = stoch_data["d_percent"].iloc[-2]

            stoch_signal = indicator_service.detect_stochastic_signals(
                current_k, current_d, prev_k, prev_d
            )

            if stoch_signal:
                print(f"🔔 스토캐스틱 신호: {stoch_signal}")
            else:
                print("🔄 스토캐스틱 특별한 신호 없음")

        # 스토캐스틱 상태 분석
        if current_k >= 80 or current_d >= 80:
            status = "과매수 구간 (조정 가능성)"
            emoji = "🔴"
        elif current_k <= 20 or current_d <= 20:
            status = "과매도 구간 (반등 가능성)"
            emoji = "🟢"
        else:
            status = "중립 구간"
            emoji = "🟡"

        print(f"  {emoji} 상태: {status}")


def test_volume_analysis():
    """거래량 분석 테스트"""
    print("\n🧪 거래량 분석 테스트 시작")

    # 클라이언트 및 서비스 초기화
    yahoo_client = YahooPriceClient()
    indicator_service = TechnicalIndicatorService()

    # 나스닥 지수 데이터 가져오기
    symbol = "^IXIC"
    df = yahoo_client.get_daily_data(symbol, period="3mo")

    if df is None or len(df) < 30:
        print(f"❌ {symbol} 데이터 부족")
        return

    # 컬럼명을 소문자로 변환
    df.columns = df.columns.str.lower()

    current_price = df["close"].iloc[-1]
    prev_price = df["close"].iloc[-2]
    price_change_pct = ((current_price - prev_price) / prev_price) * 100

    print(f"💰 {symbol} 현재가: {current_price:.2f} ({price_change_pct:+.2f}%)")

    # 거래량 분석
    current_volume = df["volume"].iloc[-1]
    volume_sma = indicator_service.calculate_volume_sma(df["volume"])

    if not volume_sma.empty:
        avg_volume = volume_sma.iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0

        print(f"\n📊 거래량 분석:")
        print(f"  현재 거래량: {current_volume:15,.0f}")
        print(f"  평균 거래량: {avg_volume:15,.0f}")
        print(f"  거래량 비율: {volume_ratio:8.2f}배")

        # 거래량 신호 감지
        volume_signal = indicator_service.detect_volume_signals(
            current_volume, avg_volume, price_change_pct
        )

        if volume_signal:
            print(f"🔔 거래량 신호: {volume_signal}")
        else:
            print("🔄 거래량 특별한 신호 없음")

        # 거래량 상태 분석
        if volume_ratio >= 2.0:
            status = "거래량 급증"
            emoji = "🔥"
        elif volume_ratio >= 1.5:
            status = "거래량 증가"
            emoji = "📈"
        elif volume_ratio <= 0.5:
            status = "거래량 부족"
            emoji = "😴"
        else:
            status = "정상 거래량"
            emoji = "🔄"

        print(f"  {emoji} 상태: {status}")


def test_comprehensive_analysis():
    """종합 기술적 분석 테스트"""
    print("\n🧪 종합 기술적 분석 테스트 시작")

    # 클라이언트 및 서비스 초기화
    yahoo_client = YahooPriceClient()
    indicator_service = TechnicalIndicatorService()

    # 나스닥 지수 데이터 가져오기
    symbol = "^IXIC"
    df = yahoo_client.get_daily_data(symbol, period="1y")

    if df is None or len(df) < 200:
        print(f"❌ {symbol} 데이터 부족")
        return

    # 컬럼명을 소문자로 변환
    df.columns = df.columns.str.lower()

    print(f"💰 {symbol} 종합 분석")

    # 종합 분석 수행
    analysis_result = indicator_service.analyze_comprehensive_signals(df)

    if analysis_result:
        print(
            f"\n📊 분석 시간: {analysis_result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(f"💰 현재가: {analysis_result['current_price']:.2f}")
        print(f"📈 가격 변화: {analysis_result['price_change_pct']:+.2f}%")

        # 감지된 신호들 출력
        signals = analysis_result.get("signals", {})
        if signals:
            print(f"\n🔔 감지된 신호들 ({len(signals)}개):")
            for indicator_name, signal in signals.items():
                print(f"  {indicator_name.upper()}: {signal}")
        else:
            print("\n🔄 현재 특별한 신호 없음")

        # 주요 지표 현재값 출력
        indicators = analysis_result.get("indicators", {})

        # RSI
        if "rsi" in indicators:
            rsi_current = indicators["rsi"]["current"]
            if rsi_current >= 70:
                rsi_status = "과매수"
                rsi_emoji = "🔴"
            elif rsi_current <= 30:
                rsi_status = "과매도"
                rsi_emoji = "🟢"
            else:
                rsi_status = "중립"
                rsi_emoji = "🟡"
            print(f"\n📊 RSI: {rsi_current:.1f} ({rsi_emoji} {rsi_status})")

        # MACD
        if "macd" in indicators:
            macd_current = indicators["macd"]["current_macd"]
            signal_current = indicators["macd"]["current_signal"]
            histogram = indicators["macd"]["current_histogram"]

            if macd_current > signal_current:
                macd_status = "상승 모멘텀"
                macd_emoji = "📈"
            else:
                macd_status = "하락 모멘텀"
                macd_emoji = "📉"

            print(f"📊 MACD: {macd_current:.4f} ({macd_emoji} {macd_status})")
            print(f"    Signal: {signal_current:.4f}, Histogram: {histogram:.4f}")

        # 스토캐스틱
        if "stochastic" in indicators:
            k_percent = indicators["stochastic"]["k_percent"]
            d_percent = indicators["stochastic"]["d_percent"]

            if k_percent >= 80 or d_percent >= 80:
                stoch_status = "과매수"
                stoch_emoji = "🔴"
            elif k_percent <= 20 or d_percent <= 20:
                stoch_status = "과매도"
                stoch_emoji = "🟢"
            else:
                stoch_status = "중립"
                stoch_emoji = "🟡"

            print(
                f"📊 스토캐스틱: %K={k_percent:.1f}, %D={d_percent:.1f} ({stoch_emoji} {stoch_status})"
            )

        # 거래량
        if "volume" in indicators:
            volume_ratio = indicators["volume"]["ratio"]
            if volume_ratio >= 2.0:
                volume_status = "급증"
                volume_emoji = "🔥"
            elif volume_ratio >= 1.5:
                volume_status = "증가"
                volume_emoji = "📈"
            elif volume_ratio <= 0.5:
                volume_status = "부족"
                volume_emoji = "😴"
            else:
                volume_status = "정상"
                volume_emoji = "🔄"

            print(f"📊 거래량: {volume_ratio:.2f}배 ({volume_emoji} {volume_status})")


def main():
    """메인 함수"""
    print("🚀 고급 기술적 지표 테스트 시작")
    print(f"⏰ 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 1. MACD 지표 테스트
        test_macd_indicator()

        # 2. 스토캐스틱 지표 테스트
        test_stochastic_indicator()

        # 3. 거래량 분석 테스트
        test_volume_analysis()

        # 4. 종합 기술적 분석 테스트
        test_comprehensive_analysis()

        print("\n✅ 모든 고급 지표 테스트 완료!")

    except Exception as e:
        print(f"❌ 테스트 실행 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
