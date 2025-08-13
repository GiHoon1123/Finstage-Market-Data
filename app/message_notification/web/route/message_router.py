from fastapi import APIRouter, status, HTTPException
from app.message_notification.dto.message_request import MessageRequest
from app.message_notification.handler.message_handler import handle_send_message
from app.common.config.api_metadata import common_responses
from app.common.utils.response_helper import handle_service_error

router = APIRouter()


@router.post(
    "/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="텔레그램 메시지 전송",
    description="""
    지정된 메시지를 텔레그램으로 전송합니다.
    
    **주요 기능:**
    - 비동기 메시지 전송으로 빠른 응답
    - 전송 로그 자동 저장
    - 실패 시 재시도 메커니즘
    - 메시지 형식 자동 검증
    
    **사용 사례:**
    - 시스템 알림 전송
    - 거래 신호 알림
    - 에러 상황 알림
    - 일일 리포트 전송
    
    **제한사항:**
    - 메시지 길이: 최대 4096자
    - 전송 빈도: 분당 최대 30회
    """,
    tags=["Message Notification"],
    responses={
        **common_responses,
        204: {"description": "메시지가 성공적으로 전송 큐에 추가되었습니다."},
        429: {
            "description": "전송 빈도 제한 초과",
            "content": {
                "application/json": {
                    "example": {
                        "error": "RATE_LIMIT_EXCEEDED",
                        "message": "메시지 전송 빈도 제한을 초과했습니다",
                        "retry_after": 60,
                        "timestamp": "2025-08-09T12:00:00Z",
                    }
                }
            },
        },
    },
)
async def send_message(request: MessageRequest):
    """
    텔레그램으로 메시지를 전송합니다.

    메시지는 비동기로 처리되며, 전송 결과는 별도로 로깅됩니다.
    전송 실패 시 자동으로 재시도하며, 최종 실패 시에도 로그가 남습니다.
    """
    try:
        await handle_send_message(request.message)
        # 204 상태 코드는 성공이지만 응답 본문이 없음
    except Exception as e:
        handle_service_error(e, "메시지 전송 실패")
