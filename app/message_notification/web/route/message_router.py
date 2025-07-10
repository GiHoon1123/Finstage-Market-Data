from fastapi import APIRouter, status
from app.message_notification.dto.message_request import MessageRequest
from app.message_notification.handler.message_handler import handle_send_message

router = APIRouter(prefix="/messages", tags=["Message Notifications"])

@router.post(
    "/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="메시지를 텔레그램으로 전송합니다.",
    description="요청으로 받은 메시지를 비동기로 텔레그램으로 전송하고, 전송 로그를 DB에 저장합니다.",
    responses={
        204: {"description": "메시지가 성공적으로 전송됨"},
    }
)
async def send_message(request: MessageRequest):
    await handle_send_message(request.message)