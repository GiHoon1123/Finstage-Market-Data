#!/usr/bin/env python3
"""
가격 알림 설정 확인 테스트 (테스트용 0 임계치)
"""

import os
import sys
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.common.constants.thresholds import CATEGORY_THRESHOLDS, SYMBOL_THRESHOLDS
from app.common.constants.symbol_names import STOCK_SYMBOLS, INDEX_SYMBOLS


def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("🔔 가격 알림 설정 확인 (테스트용 0 임계치)")
    print("=" * 80)
    print(f"🕐 확인 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print("\n📊 현재 임계치 설정:")
    print("-" * 60)

    for category, thresholds in CATEGORY_THRESHOLDS.items():
        print(f"\n🔹 {category} 카테고리:")
        for alert_type, value in thresholds.items():
            alert_name = {
                "price_rise": "상승 알림",
                "price_drop": "하락 알림",
                "drop_from_high": "고점 대비 하락",
            }.get(alert_type, alert_type)

            print(f"  • {alert_name}: {value}%")

    print("\n🎯 적용 대상 종목:")
    print("-" * 60)

    print("📈 지수 (지수 카테고리 적용):")
    for symbol, name in INDEX_SYMBOLS.items():
        print(f"  • {symbol}: {name}")
        print(f"    - 상승 알림: {CATEGORY_THRESHOLDS['지수']['price_rise']}% 이상")
        print(f"    - 하락 알림: {CATEGORY_THRESHOLDS['지수']['price_drop']}% 이상")

    print("\n📱 개별 종목 (종목 카테고리 적용):")
    for symbol, name in STOCK_SYMBOLS.items():
        print(f"  • {symbol}: {name}")
        print(f"    - 상승 알림: {CATEGORY_THRESHOLDS['종목']['price_rise']}% 이상")
        print(f"    - 하락 알림: {CATEGORY_THRESHOLDS['종목']['price_drop']}% 이상")

    print("\n⏰ 알림 주기 및 방식:")
    print("-" * 60)
    print("🔄 모니터링 주기: 3분마다")
    print("🔔 중복 알림 방지: 3분 (테스트용)")
    print("📱 알림 방식: 텔레그램 즉시 전송")

    print("\n🧪 테스트 설정 효과:")
    print("-" * 60)
    print("✅ 임계치 0% = 모든 가격 변화에 알림")
    print("✅ 중복 방지 3분 = 3분마다 새로운 알림 가능")
    print("✅ 모니터링 3분 = 3분마다 가격 체크")
    print("📊 예상 결과: 3분마다 모든 종목의 가격 변화 알림")

    print("\n⚠️ 테스트 주의사항:")
    print("-" * 60)
    print("1. 🔔 알림 폭주 가능성: 9개 종목 × 3분마다 = 매우 많은 알림")
    print("2. 📱 텔레그램 Rate Limit: 너무 많은 메시지 시 제한 가능")
    print("3. 🔋 리소스 사용: 지속적인 API 호출로 리소스 사용량 증가")
    print("4. 📊 로그 증가: 모든 알림이 DB에 저장되어 로그 급증")

    print("\n🔧 테스트 후 복구 방법:")
    print("-" * 60)
    print("1. thresholds.py에서 임계치를 원래 값으로 복구")
    print("2. price_monitor_service.py에서 중복 방지 시간을 1440분으로 복구")
    print("3. 스케줄러 재시작으로 설정 적용")

    print("\n💡 권장 테스트 시간:")
    print("-" * 60)
    print("🕐 단기 테스트: 10-15분 (3-5회 알림 확인)")
    print("⚠️ 장기 테스트 비권장: 알림 폭주 및 리소스 낭비")

    print(f"\n🕐 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    print("\n🚀 테스트 시작 준비 완료!")
    print("📱 텔레그램에서 3분마다 종목 알림을 확인하세요.")


if __name__ == "__main__":
    main()
