#!/usr/bin/env python3
"""
일일 리포트 테스트 (실제 클러스터링 결과 사용)
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
    print("📊 일일 종합 리포트 테스트 (실제 클러스터링 결과 사용)")
    print("=" * 80)
    print(f"🕐 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 서비스 초기화
    report_service = DailyComprehensiveReportService()

    try:
        # 일일 리포트 생성
        print("\n🔄 일일 리포트 생성 중...")
        result = report_service.generate_daily_report()

        if result.get("status") == "success":
            print("✅ 일일 리포트 생성 성공!")
            print(f"📅 리포트 날짜: {result.get('report_date')}")
            print(f"📈 분석 심볼: {', '.join(result.get('analyzed_symbols', []))}")
            print(
                f"📱 텔레그램 전송: {'성공' if result.get('telegram_sent') else '실패'}"
            )

            # ML 분석 결과 출력
            print("\n🤖 머신러닝 분석 결과:")
            for symbol, data in result.get("data", {}).items():
                ml_data = data.get("ml_analysis", {})
                if ml_data.get("status") == "success":
                    print(f"  📊 {symbol}:")
                    print(f"    - 클러스터 그룹: {ml_data.get('cluster_groups', 0)}개")
                    print(f"    - 전체 패턴: {ml_data.get('total_patterns', 0)}개")
                    print(f"    - 상승 패턴: {ml_data.get('bullish_patterns', 0)}개")
                    print(f"    - 하락 패턴: {ml_data.get('bearish_patterns', 0)}개")
                    print(f"    - 중립 패턴: {ml_data.get('neutral_patterns', 0)}개")

                    # 가장 강한 클러스터 정보
                    strongest_bullish = ml_data.get("strongest_bullish")
                    if strongest_bullish:
                        print(
                            f"    - 최강 상승 클러스터: {strongest_bullish['name']} ({strongest_bullish['pattern_count']}개, 성공률 {strongest_bullish['success_rate']:.1f}%)"
                        )

                    strongest_bearish = ml_data.get("strongest_bearish")
                    if strongest_bearish:
                        print(
                            f"    - 최강 하락 클러스터: {strongest_bearish['name']} ({strongest_bearish['pattern_count']}개, 성공률 {strongest_bearish['success_rate']:.1f}%)"
                        )
                else:
                    print(f"  ❌ {symbol}: {ml_data.get('message', '분석 실패')}")

            # 투자 인사이트 출력
            print("\n🎯 투자 인사이트:")
            insights = result.get("insights", {})
            for key, value in insights.items():
                if key not in [
                    "overall_accuracy",
                    "analyzed_patterns",
                    "ml_clusters",
                    "risk_level",
                ]:
                    print(f"  • {value}")

            print(f"\n📊 종합 분석:")
            print(f"  • 전체 정확도: {insights.get('overall_accuracy', 0):.1f}%")
            print(f"  • 분석된 패턴: {insights.get('analyzed_patterns', 0)}개")
            print(f"  • ML 클러스터: {insights.get('ml_clusters', 0)}개")
            print(f"  • 리스크 수준: {insights.get('risk_level', '알 수 없음')}")

        else:
            print(f"❌ 일일 리포트 생성 실패: {result.get('error')}")

    except Exception as e:
        print(f"❌ 테스트 실행 실패: {e}")

    print(f"\n🕐 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    main()
