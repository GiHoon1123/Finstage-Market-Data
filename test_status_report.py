#!/usr/bin/env python3
"""
시장 상태 리포트 테스트 스크립트

새로 구현된 상태 리포트 시스템을 테스트합니다:
- 나스닥 & S&P 500 상태 분석
- 모든 이동평균선 포함 (SMA 5,10,21,50,200 + EMA 9,21,50 + VWAP)
- 기술적 지표 현황 (RSI, MACD, 스토캐스틱, 거래량)
- 시장 심리 분석
- 텔레그램 자동 전송
"""

from app.technical_analysis.service.technical_monitor_service import (
    TechnicalMonitorService,
)


def test_status_report():
    """상태 리포트 테스트 실행"""
    print("🚀 시장 상태 리포트 테스트 시작")
    print("=" * 60)

    try:
        service = TechnicalMonitorService()

        # 상태 리포트 생성 및 전송 테스트
        service.run_hourly_status_report()

        print("=" * 60)
        print("✅ 시장 상태 리포트 테스트 완료!")
        print("📱 텔레그램에서 메시지를 확인해보세요.")

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_status_report()
