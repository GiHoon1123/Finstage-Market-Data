#!/usr/bin/env python3
"""
설정 시스템 테스트 스크립트
"""

import os
import sys

sys.path.append(".")


def test_settings_validation():
    """설정 검증 테스트"""

    print("🔧 설정 시스템 테스트 시작")

    # 환경 설정
    os.environ["ENVIRONMENT"] = "development"

    try:
        from app.common.config.settings import validate_settings, settings

        # 설정 검증
        validate_settings()

        print(f"✅ 환경: {settings.environment}")
        print(f"✅ 디버그 모드: {settings.debug}")
        print(f"✅ 데이터베이스 URL: {settings.database.url}")
        print(f"✅ 로그 레벨: {settings.logging.level}")
        print(f"✅ 텔레그램 봇 토큰: {settings.telegram.bot_token[:10]}...")

        # 개별 설정 테스트
        print("\n📋 설정 상세 정보:")
        print(f"  - 서버: {settings.host}:{settings.port}")
        print(
            f"  - 데이터베이스: {settings.database.host}:{settings.database.port}/{settings.database.database}"
        )
        print(f"  - 로그 파일: {settings.logging.file_path}")
        print(f"  - Yahoo Finance 지연: {settings.api.yfinance_delay}초")

        print("\n✅ 모든 설정 검증 완료!")

    except Exception as e:
        print(f"❌ 설정 검증 실패: {e}")
        return False

    return True


def test_environment_switching():
    """환경별 설정 테스트"""

    print("\n🔄 환경별 설정 테스트")

    environments = ["development", "test", "production"]

    for env in environments:
        print(f"\n📍 {env} 환경 테스트:")

        # 환경 설정
        os.environ["ENVIRONMENT"] = env

        try:
            # 설정 재로드 (싱글톤 패턴 때문에 새로운 인스턴스 필요)
            from app.common.config.settings import AppSettings

            test_settings = AppSettings()

            print(f"  ✅ 환경: {test_settings.environment}")
            print(f"  ✅ 디버그: {test_settings.debug}")
            print(f"  ✅ 로그 레벨: {test_settings.logging.level}")

        except Exception as e:
            print(f"  ❌ {env} 환경 설정 실패: {e}")


def test_validation_errors():
    """설정 검증 오류 테스트"""

    print("\n🚨 설정 검증 오류 테스트")

    # 잘못된 설정들 테스트
    test_cases = [
        {
            "name": "빈 데이터베이스 비밀번호",
            "env": {"MYSQL_PASSWORD": ""},
            "expected_error": "데이터베이스 비밀번호는 필수입니다",
        },
        {
            "name": "잘못된 OpenAI API 키",
            "env": {"OPENAI_API_KEY": "invalid-key"},
            "expected_error": "올바른 OpenAI API 키 형식이 아닙니다",
        },
        {
            "name": "잘못된 로그 레벨",
            "env": {"LOG_LEVEL": "INVALID"},
            "expected_error": "로그 레벨은",
        },
    ]

    for test_case in test_cases:
        print(f"\n  🧪 {test_case['name']} 테스트:")

        # 환경변수 설정
        original_values = {}
        for key, value in test_case["env"].items():
            original_values[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            from app.common.config.settings import AppSettings

            AppSettings()
            print(f"    ❌ 예상된 오류가 발생하지 않음")
        except Exception as e:
            if test_case["expected_error"] in str(e):
                print(f"    ✅ 예상된 오류 발생: {e}")
            else:
                print(f"    ⚠️ 다른 오류 발생: {e}")

        # 환경변수 복원
        for key, value in original_values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


if __name__ == "__main__":
    success = test_settings_validation()

    if success:
        test_environment_switching()
        test_validation_errors()
        print("\n🎉 모든 설정 테스트 완료!")
    else:
        print("\n💥 기본 설정 테스트 실패")
        sys.exit(1)
