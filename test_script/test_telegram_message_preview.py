#!/usr/bin/env python3
"""
개선된 텔레그램 메시지 미리보기 테스트
"""

import os
import sys
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.technical_analysis.service.daily_comprehensive_report_service import (
    DailyComprehensiveReportService,
)


def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("📱 개선된 텔레그램 메시지 미리보기")
    print("=" * 80)
    print(f"🕐 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 서비스 초기화
    report_service = DailyComprehensiveReportService()

    try:
        # 일일 리포트 생성
        print("\n🔄 리포트 생성 중...")
        result = report_service.generate_daily_report()

        if result.get("status") == "success":
            print("✅ 리포트 생성 성공!")

            # 텔레그램 메시지 재생성 (미리보기용)
            telegram_message = report_service._format_telegram_message(
                result.get("data", {}), result.get("insights", {})
            )

            print("\n" + "=" * 80)
            print("📱 텔레그램 메시지 미리보기")
            print("=" * 80)
            print(telegram_message)
            print("=" * 80)

            # 메시지 통계
            lines = telegram_message.split("\n")
            chars = len(telegram_message)

            print(f"\n📊 메시지 통계:")
            print(f"  📝 총 줄 수: {len(lines)}줄")
            print(f"  📏 총 글자 수: {chars:,}자")
            print(f"  📱 텔레그램 제한: {4096}자 (여유: {4096-chars:,}자)")

            if chars > 4096:
                print("  ⚠️ 텔레그램 메시지 길이 제한 초과!")
            else:
                print("  ✅ 텔레그램 메시지 길이 적정")

        else:
            print(f"❌ 리포트 생성 실패: {result.get('error')}")

    except Exception as e:
        print(f"❌ 테스트 실행 실패: {e}")

    print(f"\n🕐 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    main()
