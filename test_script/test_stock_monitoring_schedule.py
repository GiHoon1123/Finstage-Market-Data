#!/usr/bin/env python3
"""
개별 종목 가격 모니터링 스케줄 확인 테스트
"""

import os
import sys
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.common.constants.symbol_names import (
    SYMBOL_PRICE_MAP,
    STOCK_SYMBOLS,
    INDEX_SYMBOLS,
)


def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("📊 개별 종목 가격 모니터링 스케줄 확인")
    print("=" * 80)
    print(f"🕐 확인 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print("\n📈 현재 모니터링 대상 종목들:")
    print("-" * 60)

    # 지수 종목들
    print("🔹 주요 지수:")
    for symbol, name in INDEX_SYMBOLS.items():
        print(f"  • {symbol}: {name}")

    # 개별 종목들
    print("\n🔹 개별 종목:")
    for symbol, name in STOCK_SYMBOLS.items():
        print(f"  • {symbol}: {name}")

    print(f"\n📊 총 모니터링 종목 수: {len(SYMBOL_PRICE_MAP)}개")
    print(f"  - 지수: {len(INDEX_SYMBOLS)}개")
    print(f"  - 개별 종목: {len(STOCK_SYMBOLS)}개")

    print("\n⏰ 현재 스케줄링 설정:")
    print("-" * 60)
    print("🔄 실시간 가격 모니터링: 3분마다 실행")
    print("📡 함수명: run_realtime_price_monitor_job()")
    print("📋 처리 방식:")
    print("  1. SYMBOL_PRICE_MAP의 모든 종목을 순회")
    print("  2. 각 종목마다 5초 간격으로 처리")
    print("  3. PriceMonitorService.check_price_against_baseline() 호출")
    print("  4. 기준선 대비 가격 변화 체크")

    # 실제 처리 시간 계산
    total_symbols = len(SYMBOL_PRICE_MAP)
    processing_time_per_symbol = 5  # 초
    total_processing_time = total_symbols * processing_time_per_symbol

    print(f"\n⏱️ 예상 처리 시간:")
    print(f"  • 총 종목 수: {total_symbols}개")
    print(f"  • 종목당 처리 시간: {processing_time_per_symbol}초")
    print(
        f"  • 총 처리 시간: {total_processing_time}초 ({total_processing_time//60}분 {total_processing_time%60}초)"
    )
    print(f"  • 스케줄 간격: 3분 (180초)")

    if total_processing_time > 180:
        print("  ⚠️ 처리 시간이 스케줄 간격보다 깁니다!")
        print("  💡 권장사항: 병렬 처리 또는 간격 조정 필요")
    else:
        print("  ✅ 처리 시간이 스케줄 간격 내에 완료 가능합니다")

    print("\n🎯 모니터링되는 빅테크 종목들:")
    print("-" * 60)
    big_tech = ["AAPL", "AMZN", "GOOGL", "TSLA", "MSFT", "META", "NVDA"]

    for symbol in big_tech:
        if symbol in STOCK_SYMBOLS:
            print(f"  ✅ {symbol}: {STOCK_SYMBOLS[symbol]} - 3분마다 모니터링")
        else:
            print(f"  ❌ {symbol}: 모니터링 대상 아님")

    print("\n📱 알림 방식:")
    print("-" * 60)
    print("🔔 가격 변화 감지 시:")
    print("  • 기준선 대비 일정 비율 이상 변화 시 알림")
    print("  • 텔레그램으로 즉시 알림 전송")
    print("  • 로그에 상세 정보 기록")

    print("\n💡 개선 제안:")
    print("-" * 60)
    print("1. 🚀 병렬 처리: 여러 종목을 동시에 처리하여 속도 향상")
    print("2. ⚡ 간격 조정: 중요 종목은 더 자주, 일반 종목은 덜 자주")
    print("3. 🎯 선별 모니터링: 변동성이 큰 종목 우선 모니터링")
    print("4. 📊 배치 처리: 여러 종목을 한 번에 조회하여 API 호출 최적화")

    print(f"\n🕐 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    main()
