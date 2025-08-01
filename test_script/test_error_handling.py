#!/usr/bin/env python3
"""
에러 핸들링 시스템 테스트 스크립트
"""

import sys

sys.path.append(".")

from app.common.exceptions.base import (
    FinstageException,
    DatabaseError,
    APIError,
    AnalysisError,
    ErrorCode,
)
from app.common.exceptions.handlers import (
    handle_errors,
    handle_database_errors,
    handle_api_errors,
    safe_execute,
    create_error_response,
)
from app.common.utils.logging_config import setup_logging, get_logger

# 로깅 시스템 초기화
setup_logging()
logger = get_logger("test_error_handling")


def test_custom_exceptions():
    """커스텀 예외 클래스 테스트"""
    print("🧪 커스텀 예외 클래스 테스트")

    # 기본 예외
    try:
        raise FinstageException(
            message="테스트 예외입니다",
            error_code=ErrorCode.VALIDATION_ERROR,
            details={"field": "test_field", "value": "invalid_value"},
        )
    except FinstageException as e:
        print(f"  ✅ 기본 예외: {e}")
        print(f"     에러 코드: {e.error_code.value}")
        print(f"     세부 정보: {e.details}")

    # 데이터베이스 예외
    try:
        raise DatabaseError(
            message="데이터베이스 연결 실패",
            error_code=ErrorCode.DATABASE_CONNECTION_ERROR,
            details={"host": "localhost", "port": 3306},
        )
    except DatabaseError as e:
        print(f"  ✅ 데이터베이스 예외: {e}")
        print(f"     딕셔너리 변환: {e.to_dict()}")

    # API 예외
    try:
        raise APIError(
            message="외부 API 호출 실패",
            error_code=ErrorCode.API_TIMEOUT_ERROR,
            details={"url": "https://api.example.com", "timeout": 30},
        )
    except APIError as e:
        print(f"  ✅ API 예외: {e}")


def test_error_decorators():
    """에러 핸들링 데코레이터 테스트"""
    print("\n🎭 에러 핸들링 데코레이터 테스트")

    @handle_errors(reraise=False, return_on_error="에러 발생")
    def function_with_error():
        raise ValueError("테스트 에러")

    @handle_database_errors(reraise=False, return_on_error={"error": "DB 에러"})
    def database_function_with_error():
        from sqlalchemy.exc import SQLAlchemyError

        raise SQLAlchemyError("데이터베이스 에러")

    @handle_api_errors(reraise=False, return_on_error=None)
    def api_function_with_error():
        import requests

        raise requests.RequestException("API 에러")

    # 일반 에러 테스트
    result = function_with_error()
    print(f"  ✅ 일반 에러 처리: {result}")

    # 데이터베이스 에러 테스트
    result = database_function_with_error()
    print(f"  ✅ 데이터베이스 에러 처리: {result}")

    # API 에러 테스트
    result = api_function_with_error()
    print(f"  ✅ API 에러 처리: {result}")


def test_safe_execute():
    """안전한 함수 실행 테스트"""
    print("\n🛡️ 안전한 함수 실행 테스트")

    def normal_function(x, y):
        return x + y

    def error_function():
        raise ValueError("의도적 에러")

    # 정상 함수 실행
    result = safe_execute(normal_function, 10, 20)
    print(f"  ✅ 정상 함수 실행: {result}")

    # 에러 함수 실행 (기본값 반환)
    result = safe_execute(error_function, default_return="기본값")
    print(f"  ✅ 에러 함수 실행 (기본값): {result}")

    # 에러 함수 실행 (None 반환)
    result = safe_execute(error_function)
    print(f"  ✅ 에러 함수 실행 (None): {result}")


def test_error_response_creation():
    """에러 응답 생성 테스트"""
    print("\n📋 에러 응답 생성 테스트")

    # 커스텀 예외 응답
    custom_error = AnalysisError(
        message="기술적 분석 실패",
        error_code=ErrorCode.ANALYSIS_CALCULATION_ERROR,
        details={"symbol": "AAPL", "strategy": "RSI"},
    )

    response = create_error_response(custom_error)
    print(f"  ✅ 커스텀 예외 응답:")
    for key, value in response.items():
        print(f"     {key}: {value}")

    # 일반 예외 응답
    general_error = ValueError("일반 에러")
    response = create_error_response(general_error)
    print(f"  ✅ 일반 예외 응답:")
    for key, value in response.items():
        print(f"     {key}: {value}")


def test_logging_integration():
    """로깅 시스템 통합 테스트"""
    print("\n📝 로깅 시스템 통합 테스트")

    @handle_errors(log_errors=True, reraise=False, return_on_error="로깅 테스트 완료")
    def function_with_logging_error():
        raise RuntimeError("로깅 테스트 에러")

    result = function_with_logging_error()
    print(f"  ✅ 로깅 통합 테스트: {result}")
    print("     (로그 파일에서 에러 로그 확인 가능)")


def test_real_world_scenario():
    """실제 시나리오 테스트"""
    print("\n🌍 실제 시나리오 테스트")

    @handle_database_errors(
        reraise=False, return_on_error={"success": False, "error": "DB 연결 실패"}
    )
    def simulate_database_operation(symbol):
        """데이터베이스 작업 시뮬레이션"""
        if symbol == "ERROR":
            from sqlalchemy.exc import OperationalError

            raise OperationalError("Connection failed", None, None)
        return {"success": True, "data": f"{symbol} 데이터"}

    @handle_api_errors(reraise=False, return_on_error=None)
    def simulate_api_call(url):
        """API 호출 시뮬레이션"""
        if "error" in url:
            import requests

            raise requests.ConnectionError("API 연결 실패")
        return {"status": "success", "data": "API 응답"}

    # 정상 케이스
    db_result = simulate_database_operation("AAPL")
    api_result = simulate_api_call("https://api.example.com/data")
    print(f"  ✅ 정상 DB 작업: {db_result}")
    print(f"  ✅ 정상 API 호출: {api_result}")

    # 에러 케이스
    db_error_result = simulate_database_operation("ERROR")
    api_error_result = simulate_api_call("https://api.error.com/data")
    print(f"  ✅ DB 에러 처리: {db_error_result}")
    print(f"  ✅ API 에러 처리: {api_error_result}")


if __name__ == "__main__":
    print("🚀 에러 핸들링 시스템 테스트 시작\n")

    test_custom_exceptions()
    test_error_decorators()
    test_safe_execute()
    test_error_response_creation()
    test_logging_integration()
    test_real_world_scenario()

    print("\n🎉 모든 에러 핸들링 테스트 완료!")
    print("\n📁 로그 파일을 확인하여 에러 로깅이 제대로 작동하는지 확인하세요:")
    print("   - logs/app.log")
    print("   - logs/error.log")
