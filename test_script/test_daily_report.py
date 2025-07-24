#!/usr/bin/env python3
"""
일일 시장 상태 리포트 테스트 스크립트

매일 오전 7시 KST에 실행되는 일봉 분석 리포트를 테스트합니다:
- 나스닥 & S&P 500 일봉 분석
- 모든 이동평균선 포함 (SMA 5,10,21,50,200 + EMA 9,21,50 + VWAP)
- 기술적 지표 현황 (RSI, MACD, 스토캐스틱, 거래량)
- 시장 심리 분석
- 텔레그램 자동 전송
"""

import os
from dotenv import load_dotenv
from app.technical_analysis.service.technical_monitor_service import (
    TechnicalMonitorService,
)


def test_daily_report():
    """일일 시장 상태 리포트 테스트 실행"""
    print("🚀 일일 시장 상태 리포트 테스트 시작")
    print("=" * 60)

    # main.py와 동일한 방식으로 환경변수 로드
    mode = os.getenv("ENV_MODE", "test")  # 기본값을 test로 설정
    env_file = f".env.{mode}"
    load_dotenv(dotenv_path=env_file)

    print(f"🔍 환경설정: ENV_MODE = {mode}, env_file = {env_file}")

    try:
        service = TechnicalMonitorService()

        # 일일 상태 리포트 생성 및 전송 테스트
        print("📊 일일 상태 리포트 생성 중...")
        service.run_hourly_status_report()  # 함수명은 hourly지만 실제로는 일봉 데이터 사용

        print("=" * 60)
        print("✅ 일일 시장 상태 리포트 테스트 완료!")
        print("📱 텔레그램에서 메시지를 확인해보세요.")
        print("⏰ 실제로는 매일 오전 7시 KST에 자동 전송됩니다.")

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_daily_report()
