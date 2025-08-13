from typing import Any, Optional, List
from pydantic import BaseModel
import math


class ApiResponse(BaseModel):
    """통일된 API 응답 구조 - status, message, data 세 키는 반드시 포함"""

    status: int
    message: str
    data: Optional[Any] = None

    @staticmethod
    def success(data: Any = None, message: str = "성공적으로 처리되었습니다"):
        """성공 응답"""
        return {"status": 200, "message": message, "data": data}

    @staticmethod
    def success_with_pagination(
        items: List[Any],
        page: int,
        size: int,
        total: int,
        message: str = "조회가 완료되었습니다",
    ):
        """페이징이 있는 성공 응답"""
        total_pages = math.ceil(total / size) if size > 0 else 0
        has_next = page < total_pages
        has_prev = page > 1

        return {
            "status": 200,
            "message": message,
            "data": {
                "items": items,
                "pagination": {
                    "page": page,
                    "size": size,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev,
                },
            },
        }

    @staticmethod
    def error(status: int, message: str, data: Any = None):
        """에러 응답"""
        return {"status": status, "message": message, "data": data}

    @staticmethod
    def not_found(message: str = "요청한 리소스를 찾을 수 없습니다"):
        """404 에러"""
        return {"status": 404, "message": message, "data": None}

    @staticmethod
    def bad_request(message: str = "잘못된 요청입니다"):
        """400 에러"""
        return {"status": 400, "message": message, "data": None}

    @staticmethod
    def server_error(message: str = "서버 오류가 발생했습니다"):
        """500 에러"""
        return {"status": 500, "message": message, "data": None}
