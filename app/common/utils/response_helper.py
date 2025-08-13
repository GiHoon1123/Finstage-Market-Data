from typing import Any, List
from fastapi import HTTPException
from app.common.dto.api_response import ApiResponse


def success_response(data: Any = None, message: str = "성공적으로 처리되었습니다"):
    """성공 응답 헬퍼"""
    return ApiResponse.success(data=data, message=message)


def paginated_response(
    items: List[Any],
    page: int,
    size: int,
    total: int,
    message: str = "조회가 완료되었습니다",
):
    """페이징 응답 헬퍼"""
    return ApiResponse.success_with_pagination(
        items=items, page=page, size=size, total=total, message=message
    )


def error_response(status: int, message: str, data: Any = None):
    """에러 응답 헬퍼 (HTTPException 발생)"""
    response = ApiResponse.error(status=status, message=message, data=data)
    raise HTTPException(status_code=status, detail=response)


def not_found_response(message: str = "요청한 리소스를 찾을 수 없습니다"):
    """404 에러 응답"""
    response = ApiResponse.not_found(message=message)
    raise HTTPException(status_code=404, detail=response)


def bad_request_response(message: str = "잘못된 요청입니다"):
    """400 에러 응답"""
    response = ApiResponse.bad_request(message=message)
    raise HTTPException(status_code=400, detail=response)


def handle_service_error(
    e: Exception, default_message: str = "서비스 처리 중 오류가 발생했습니다"
):
    """서비스 에러 처리 헬퍼"""
    if isinstance(e, HTTPException):
        raise e
    else:
        response = ApiResponse.server_error(f"{default_message}: {str(e)}")
        raise HTTPException(status_code=500, detail=response)
