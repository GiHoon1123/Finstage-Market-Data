#!/usr/bin/env python3
"""
결과 분석 API 엔드포인트 테스트 스크립트
"""

import requests
import json
from datetime import datetime

# API 베이스 URL
BASE_URL = "http://127.0.0.1:8081/api/technical-analysis/outcomes"


def test_api_endpoint(endpoint, method="GET", params=None, data=None):
    """API 엔드포인트 테스트"""
    url = f"{BASE_URL}{endpoint}"

    try:
        if method == "GET":
            response = requests.get(url, params=params)
        elif method == "POST":
            response = requests.post(url, params=params, json=data)

        print(f"\n{'='*60}")
        print(f"🔍 테스트: {method} {endpoint}")
        print(f"📡 URL: {url}")
        if params:
            print(f"📋 파라미터: {params}")
        print(f"📊 상태 코드: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ 성공!")
            print(f"📄 응답 데이터:")
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        else:
            print(f"❌ 실패: {response.text}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")


def main():
    print("🚀 결과 분석 API 테스트 시작")
    print(f"🌐 베이스 URL: {BASE_URL}")

    # 1. 추적 요약 정보
    test_api_endpoint("/tracking/summary")

    # 2. 진행 중인 추적 목록 (5개만)
    test_api_endpoint("/tracking/pending", params={"limit": 5})

    # 3. 신호 유형별 성과 분석 (상위 5개)
    test_api_endpoint("/performance/by-signal-type", params={"limit": 5})

    # 4. 최고 성과 신호들 (1일 기준, 5개)
    test_api_endpoint(
        "/performance/top-performers", params={"timeframe": "1d", "limit": 5}
    )

    # 5. 실시간 대시보드 데이터
    test_api_endpoint("/monitoring/dashboard")

    # 6. 간단한 백테스팅 (RSI 신호들)
    test_api_endpoint(
        "/backtesting/simple",
        method="POST",
        params={"signal_types": ["RSI_overbought", "RSI_oversold"]},
    )

    # 7. 수동 업데이트 테스트
    test_api_endpoint("/tracking/update", method="POST", params={"batch_size": 5})

    print(f"\n🎉 API 테스트 완료!")


if __name__ == "__main__":
    main()
