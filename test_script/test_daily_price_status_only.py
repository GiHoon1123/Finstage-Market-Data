#!/usr/bin/env python3
"""
일봉 데이터 현황만 확인하는 간단한 테스트
"""

import os
import sys
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.market_price.service.daily_price_auto_updater import DailyPriceAutoUpdater


def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("📊 일봉 데이터 현황 확인")
    print("=" * 80)
    print(f"🕐 확인 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    updater = DailyPriceAutoUpdater()
    status = updater.get_data_status()

    if status.get("status") == "success":
        print("\n✅ 데이터 현황 조회 성공!")

        for symbol, info in status["symbols"].items():
            print(f"\n🔹 {info['symbol_name']} ({symbol})")
            print(f"  📈 총 레코드: {info['total_records']:,}개")
            print(f"  📅 데이터 기간: {info['first_date']} ~ {info['last_date']}")
            print(f"  📊 최근 7일: {info['recent_7days_count']}개")

            if info["days_behind"] is not None:
                if info["days_behind"] == 0:
                    print("  🕐 상태: ✅ 최신 (오늘 데이터)")
                elif info["days_behind"] == 1:
                    print("  🕐 상태: ✅ 거의 최신 (1일 전)")
                elif info["days_behind"] <= 3:
                    print(f"  🕐 상태: ⚠️ 약간 지연 ({info['days_behind']}일 전)")
                else:
                    print(f"  🕐 상태: ❌ 업데이트 필요 ({info['days_behind']}일 전)")
            else:
                print("  🕐 상태: ❓ 데이터 없음")

            print(f"  📉 예상 누락: {info['estimated_gaps']}개")

            # 데이터 완성도 계산
            if info["expected_trading_days"] > 0:
                completeness = (
                    info["total_records"] / info["expected_trading_days"]
                ) * 100
                print(f"  📊 데이터 완성도: {completeness:.1f}%")

            print(
                f"  🎯 전체 상태: {'✅ 양호' if info['is_up_to_date'] and info['estimated_gaps'] < 10 else '⚠️ 점검 필요'}"
            )

        # 전체 요약
        total_records = sum(
            info["total_records"] for info in status["symbols"].values()
        )
        avg_gaps = sum(
            info["estimated_gaps"] for info in status["symbols"].values()
        ) / len(status["symbols"])

        print(f"\n📋 전체 요약:")
        print(f"  📈 총 레코드: {total_records:,}개")
        print(f"  📉 평균 누락: {avg_gaps:.1f}개")
        print(f"  🕐 확인 시점: {status['checked_at']}")

        # 권장사항
        if avg_gaps > 50:
            print(
                f"\n💡 권장사항: 데이터 업데이트 실행 필요 (평균 {avg_gaps:.0f}개 누락)"
            )
        elif avg_gaps > 10:
            print(
                f"\n💡 권장사항: 소규모 데이터 보완 권장 (평균 {avg_gaps:.0f}개 누락)"
            )
        else:
            print(f"\n💡 상태: 데이터 상태 양호 ✅")

    else:
        print(f"❌ 데이터 현황 조회 실패: {status.get('error')}")

    print(f"\n🕐 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    main()
