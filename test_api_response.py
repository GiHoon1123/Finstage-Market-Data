#!/usr/bin/env python3
"""
API 응답 구조 테스트 스크립트

공통 응답 구조가 올바르게 작동하는지 테스트합니다.
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_api_response_structure():
    """API 응답 구조 테스트"""
    try:
        from app.common.dto.api_response import ApiResponse
        
        print("✅ ApiResponse 클래스 import 성공")
        
        # 기본 성공 응답 테스트
        success_response = ApiResponse.success(data={"test": "data"}, message="테스트 성공")
        assert success_response["status"] == 200
        assert success_response["message"] == "테스트 성공"
        assert success_response["data"] == {"test": "data"}
        print("✅ 기본 성공 응답 테스트 통과")
        
        # 페이징 응답 테스트
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        paginated_response = ApiResponse.success_with_pagination(
            items=items, page=1, size=10, total=100, message="페이징 테스트"
        )
        assert paginated_response["status"] == 200
        assert paginated_response["message"] == "페이징 테스트"
        assert "pagination" in paginated_response["data"]
        assert paginated_response["data"]["items"] == items
        assert paginated_response["data"]["pagination"]["page"] == 1
        assert paginated_response["data"]["pagination"]["size"] == 10
        assert paginated_response["data"]["pagination"]["total"] == 100
        print("✅ 페이징 응답 테스트 통과")
        
        # 에러 응답 테스트
        error_response = ApiResponse.error(status=400, message="잘못된 요청", data={"error": "details"})
        assert error_response["status"] == 400
        assert error_response["message"] == "잘못된 요청"
        assert error_response["data"] == {"error": "details"}
        print("✅ 에러 응답 테스트 통과")
        
        # 404 응답 테스트
        not_found_response = ApiResponse.not_found("리소스를 찾을 수 없습니다")
        assert not_found_response["status"] == 404
        assert not_found_response["message"] == "리소스를 찾을 수 없습니다"
        print("✅ 404 응답 테스트 통과")
        
        print("\n🎉 모든 API 응답 구조 테스트 통과!")
        return True
        
    except Exception as e:
        print(f"❌ API 응답 구조 테스트 실패: {str(e)}")
        return False

def test_response_helper():
    """응답 헬퍼 함수 테스트"""
    try:
        from app.common.utils.response_helper import (
            success_response,
            paginated_response,
            error_response,
            not_found_response,
            handle_service_error
        )
        
        print("✅ 응답 헬퍼 함수 import 성공")
        
        # 성공 응답 헬퍼 테스트
        success_data = success_response(data={"test": "helper"}, message="헬퍼 테스트")
        assert success_data["status"] == 200
        assert success_data["message"] == "헬퍼 테스트"
        assert success_data["data"] == {"test": "helper"}
        print("✅ 성공 응답 헬퍼 테스트 통과")
        
        # 페이징 응답 헬퍼 테스트
        items = [{"id": 1}, {"id": 2}]
        paginated_data = paginated_response(
            items=items, page=2, size=5, total=50, message="페이징 헬퍼 테스트"
        )
        assert paginated_data["status"] == 200
        assert paginated_data["message"] == "페이징 헬퍼 테스트"
        assert paginated_data["data"]["items"] == items
        print("✅ 페이징 응답 헬퍼 테스트 통과")
        
        print("\n🎉 모든 응답 헬퍼 테스트 통과!")
        return True
        
    except Exception as e:
        print(f"❌ 응답 헬퍼 테스트 실패: {str(e)}")
        return False

def main():
    """메인 테스트 함수"""
    print("🚀 API 응답 구조 테스트 시작")
    print("=" * 50)
    
    # API 응답 구조 테스트
    print("\n🧪 API 응답 구조 테스트 중...")
    api_test_result = test_api_response_structure()
    
    # 응답 헬퍼 테스트
    print("\n🧪 응답 헬퍼 함수 테스트 중...")
    helper_test_result = test_response_helper()
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("📊 테스트 결과 요약")
    print("=" * 50)
    
    total_tests = 2
    passed_tests = sum([api_test_result, helper_test_result])
    
    print(f"총 테스트: {total_tests}개")
    print(f"통과: {passed_tests}개 ✅")
    print(f"실패: {total_tests - passed_tests}개 ❌")
    print(f"성공률: {(passed_tests / total_tests) * 100:.1f}%")
    
    if passed_tests == total_tests:
        print("\n🎉 모든 테스트가 통과했습니다!")
        return 0
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
