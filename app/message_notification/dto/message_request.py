from pydantic import BaseModel, Field

class MessageRequest(BaseModel):
    message: str = Field(..., example="🚀 알림 테스트 메시지입니다!")
