#!/usr/bin/env python3
"""
텔레그램 알림 테스트 스크립트

이 스크립트는 텔레그램 알림 기능을 테스트하기 위한 것입니다.
다양한 유형의 기술적 분석 알림을 테스트할 수 있습니다.
"""

import os
import sys
from datetime import datetime

# 상위 디렉토리를 파이썬 경로에 추가 (상대 임포트를 위해)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.common.utils.telegram_notifier import (
    send_ma_breakout_message,
    send_rsi_alert_message,
    send_bollinger_alert_message,
    send_golden_cross_message,
    send_dead_cross_message,
    send_price_rise_message,
    send_price_drop_message,
    send_new_high_message,
    send_drop_from_high_message,
)
from app.technical_analysis.service.technical_monitor_service import (
    TechnicalMonitorService,
)


def test_all_alerts():
    """모든 유형의 알림을 테스트합니다."""
    print("🧪 모든 알림 유형 테스트 시작...")

    # 기술적 모니터링 서비스의 테스트 함수 호출
    service = TechnicalMonitorService()
    service.test_all_technical_alerts()

    print("✅ 모든 알림 테스트 완료!")


def test_ma_breakout():
    """이동평균선 돌파 알림 테스트"""
    print("🧪 이동평균선 돌파 알림 테스트...")

    now = datetime.utcnow()

    # 나스닥 지수 50일선 상향 돌파 테스트
    send_ma_breakout_message(
        symbol="^IXIC",
        timeframe="1day",
        ma_period=50,
        current_price=20950.50,
        ma_value=20900.25,
        signal_type="breakout_up",
        now=now,
    )

    # S&P 500 지수 200일선 하향 이탈 테스트
    send_ma_breakout_message(
        symbol="^GSPC",
        timeframe="1day",
        ma_period=200,
        current_price=6290.75,
        ma_value=6310.50,
        signal_type="breakout_down",
        now=now,
    )

    print("✅ 이동평균선 돌파 알림 테스트 완료!")


def test_rsi_signals():
    """RSI 신호 알림 테스트"""
    print("🧪 RSI 신호 알림 테스트...")

    now = datetime.utcnow()

    # 나스닥 지수 RSI 과매수 테스트
    send_rsi_alert_message(
        symbol="^IXIC",
        timeframe="1day",
        current_rsi=75.8,
        signal_type="overbought",
        now=now,
    )

    # S&P 500 지수 RSI 과매도 테스트
    send_rsi_alert_message(
        symbol="^GSPC",
        timeframe="1day",
        current_rsi=28.3,
        signal_type="oversold",
        now=now,
    )

    print("✅ RSI 신호 알림 테스트 완료!")


def test_cross_signals():
    """골든크로스/데드크로스 알림 테스트"""
    print("🧪 크로스 신호 알림 테스트...")

    now = datetime.utcnow()

    # 나스닥 지수 골든크로스 테스트
    send_golden_cross_message(
        symbol="^IXIC",
        ma_50=20950.50,
        ma_200=20900.25,
        now=now,
    )

    # S&P 500 지수 데드크로스 테스트
    send_dead_cross_message(
        symbol="^GSPC",
        ma_50=6290.75,
        ma_200=6310.50,
        now=now,
    )

    print("✅ 크로스 신호 알림 테스트 완료!")


def test_price_alerts():
    """가격 알림 테스트"""
    print("🧪 가격 알림 테스트...")

    now = datetime.utcnow()

    # 나스닥 지수 가격 상승 테스트
    send_price_rise_message(
        symbol="^IXIC",
        current_price=20950.50,
        prev_close=20700.25,
        percent=1.21,
        now=now,
    )

    # S&P 500 지수 가격 하락 테스트
    send_price_drop_message(
        symbol="^GSPC",
        current_price=6290.75,
        prev_close=6350.50,
        percent=-0.94,
        now=now,
    )

    # 나스닥 지수 최고가 갱신 테스트
    send_new_high_message(
        symbol="^IXIC",
        current_price=21050.75,
        now=now,
    )

    print("✅ 가격 알림 테스트 완료!")


def main():
    """메인 함수"""
    print("🚀 텔레그램 알림 테스트 시작...")

    # 명령줄 인수 처리
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        if test_type == "all":
            test_all_alerts()
        elif test_type == "ma":
            test_ma_breakout()
        elif test_type == "rsi":
            test_rsi_signals()
        elif test_type == "cross":
            test_cross_signals()
        elif test_type == "price":
            test_price_alerts()
        else:
            print(f"❌ 알 수 없는 테스트 유형: {test_type}")
            print("사용 가능한 테스트 유형: all, ma, rsi, cross, price")
    else:
        # 기본적으로 모든 테스트 실행
        test_all_alerts()

    print("🎉 텔레그램 알림 테스트 완료!")


if __name__ == "__main__":
    main()
