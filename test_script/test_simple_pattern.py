#!/usr/bin/env python3
"""
간단한 패턴 생성 테스트 스크립트

서버가 실행 중일 때 API를 통해 패턴을 생성합니다.
"""

import requests
import json


def test_pattern_creation():
    """패턴 생성 테스트"""
    print("🔍 패턴 생성 테스트 시작...")

    base_url = "http://localhost:8081"

    try:
        # 1. 나스닥 패턴 생성 테스트
        print("📊 나스닥 패턴 분석 요청...")
        response = requests.post(
            f"{base_url}/api/technical-analysis/test/pattern-analysis",
            params={"symbol": "^IXIC"},
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ 나스닥 패턴 분석 완료:")
            print(
                f"   - 생성된 패턴: {result.get('test_data', {}).get('created_patterns', 0)}개"
            )
        else:
            print(f"❌ 나스닥 패턴 분석 실패: {response.status_code}")
            print(f"   응답: {response.text}")

        # 2. S&P 500 패턴 생성 테스트
        print("\n📊 S&P 500 패턴 분석 요청...")
        response = requests.post(
            f"{base_url}/api/technical-analysis/test/pattern-analysis",
            params={"symbol": "^GSPC"},
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ S&P 500 패턴 분석 완료:")
            print(
                f"   - 생성된 패턴: {result.get('test_data', {}).get('created_patterns', 0)}개"
            )
        else:
            print(f"❌ S&P 500 패턴 분석 실패: {response.status_code}")
            print(f"   응답: {response.text}")

        print("\n🎉 패턴 생성 테스트 완료!")
        print("이제 일일 리포트에서 패턴 클러스터링 결과를 확인할 수 있습니다.")

    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다.")
        print("서버가 실행 중인지 확인해주세요: http://localhost:8081")
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")


if __name__ == "__main__":
    test_pattern_creation()
