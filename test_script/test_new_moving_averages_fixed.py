#!/usr/bin/env python3
"""
새로운 이동평균선 테스트 스크립트 (수정된 버전)

SMA5, SMA10, SMA21, SMA50, SMA100, SMA200
EMA9, EMA21, EMA50
VWAP
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


def test_individual_moving_averages():
    """개별 이동평균선 테스트"""
    print("🧪 개별 이동평균선 테스트 시작")

    # 클라이언트 및 서비스 초기화
    yahoo_client = YahooPriceClient()
    indicator_service = TechnicalIndicatorService()

    # 나스닥 지수 데이터 가져오기
    symbol = "^IXIC"
    df = yahoo_client.get_daily_data(symbol, period="1y")

    if df is None or len(df) < 200:
        print(f"❌ {symbol} 데이터 부족")
        return

    # 컬럼명을 소문자로 변환 (Yahoo Finance 클라이언트가 대문자로 반환)
    df.columns = df.columns.str.lower()

    current_price = df["close"].iloc[-1]
    print(f"💰 {symbol} 현재가: {current_price:.2f}")

    # 1. SMA 테스트
    print("\n📊 단순이동평균(SMA) 테스트")
    sma_periods = [5, 10, 21, 50, 100, 200]

    for period in sma_periods:
        sma = indicator_service.calculate_sma(df["close"], period)
        if not sma.empty:
            current_sma = sma.iloc[-1]
            position = "위" if current_price > current_sma else "아래"
            diff_pct = ((current_price - current_sma) / current_sma) * 100
            print(
                f"  SMA{period:3d}: {current_sma:8.2f} (현재가가 {position}, 차이: {diff_pct:+6.2f}%)"
            )

    # 2. EMA 테스트
    print("\n📊 지수이동평균(EMA) 테스트")
    ema_periods = [9, 21, 50]

    for period in ema_periods:
        ema = indicator_service.calculate_ema(df["close"], period)
        if not ema.empty:
            current_ema = ema.iloc[-1]
            position = "위" if current_price > current_ema else "아래"
            diff_pct = ((current_price - current_ema) / current_ema) * 100
            print(
                f"  EMA{period:3d}: {current_ema:8.2f} (현재가가 {position}, 차이: {diff_pct:+6.2f}%)"
            )

    # 3. VWAP 테스트
    print("\n📊 거래량가중평균가격(VWAP) 테스트")
    vwap = indicator_service.calculate_vwap(df)
    if not vwap.empty:
        current_vwap = vwap.iloc[-1]
        position = "위" if current_price > current_vwap else "아래"
        diff_pct = ((current_price - current_vwap) / current_vwap) * 100
        print(
            f"  VWAP   : {current_vwap:8.2f} (현재가가 {position}, 차이: {diff_pct:+6.2f}%)"
        )


def test_all_moving_averages():
    """모든 이동평균선 일괄 테스트"""
    print("\n🧪 모든 이동평균선 일괄 테스트 시작")

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

    current_price = df["close"].iloc[-1]
    print(f"💰 {symbol} 현재가: {current_price:.2f}")

    # 모든 이동평균선 계산
    ma_results = indicator_service.calculate_all_moving_averages(df)

    print("\n📊 모든 이동평균선 현재값:")
    for ma_key, ma_series in ma_results.items():
        if not ma_series.empty:
            current_ma = ma_series.iloc[-1]
            position = "위" if current_price > current_ma else "아래"
            diff_pct = ((current_price - current_ma) / current_ma) * 100
            print(
                f"  {ma_key:8s}: {current_ma:8.2f} (현재가가 {position}, 차이: {diff_pct:+6.2f}%)"
            )


def test_ma_crossovers():
    """이동평균선 교차 테스트"""
    print("\n🧪 이동평균선 교차 테스트 시작")

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

    current_price = df["close"].iloc[-1]
    print(f"💰 {symbol} 현재가: {current_price:.2f}")

    # 주요 이동평균선들 계산
    sma_21 = indicator_service.calculate_sma(df["close"], 21)
    sma_50 = indicator_service.calculate_sma(df["close"], 50)
    sma_200 = indicator_service.calculate_sma(df["close"], 200)
    ema_9 = indicator_service.calculate_ema(df["close"], 9)
    ema_21 = indicator_service.calculate_ema(df["close"], 21)

    print("\n📊 이동평균선 배열 상태:")

    # 현재값들
    current_sma21 = sma_21.iloc[-1]
    current_sma50 = sma_50.iloc[-1]
    current_sma200 = sma_200.iloc[-1]
    current_ema9 = ema_9.iloc[-1]
    current_ema21 = ema_21.iloc[-1]

    print(f"  현재가  : {current_price:8.2f}")
    print(f"  EMA9   : {current_ema9:8.2f}")
    print(f"  EMA21  : {current_ema21:8.2f}")
    print(f"  SMA21  : {current_sma21:8.2f}")
    print(f"  SMA50  : {current_sma50:8.2f}")
    print(f"  SMA200 : {current_sma200:8.2f}")

    # 정배열/역배열 확인
    if (
        current_price
        > current_ema9
        > current_ema21
        > current_sma21
        > current_sma50
        > current_sma200
    ):
        print("\n🚀 완전 정배열 상태 - 강한 상승 추세!")
    elif (
        current_price
        < current_ema9
        < current_ema21
        < current_sma21
        < current_sma50
        < current_sma200
    ):
        print("\n📉 완전 역배열 상태 - 강한 하락 추세!")
    else:
        print("\n🔄 혼재 상태 - 추세 전환 구간일 가능성")

    # 골든크로스/데드크로스 확인
    if current_sma50 > current_sma200:
        cross_pct = ((current_sma50 - current_sma200) / current_sma200) * 100
        print(f"✅ SMA50 > SMA200: 중장기 상승 추세 (차이: {cross_pct:+.2f}%)")
    else:
        cross_pct = ((current_sma200 - current_sma50) / current_sma50) * 100
        print(f"❌ SMA50 < SMA200: 중장기 하락 추세 (차이: {cross_pct:+.2f}%)")

    # 크로스 신호 감지
    cross_signal = indicator_service.detect_cross_signals(sma_50, sma_200)
    if cross_signal:
        print(f"🔔 크로스 신호 감지: {cross_signal}")


def main():
    """메인 함수"""
    print("🚀 새로운 이동평균선 테스트 시작")
    print(f"⏰ 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 1. 개별 이동평균선 테스트
        test_individual_moving_averages()

        # 2. 모든 이동평균선 일괄 테스트
        test_all_moving_averages()

        # 3. 이동평균선 교차 테스트
        test_ma_crossovers()

        print("\n✅ 모든 테스트 완료!")

    except Exception as e:
        print(f"❌ 테스트 실행 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
