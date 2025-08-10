from pydantic import BaseModel, Field, validator


class MessageRequest(BaseModel):
    """텔레그램 메시지 전송 요청"""

    message: str = Field(
        ...,
        example="🚀 AAPL 매수 신호 발생! 현재가: $150.25 (+2.3%)",
        description="전송할 메시지 내용",
        min_length=1,
        max_length=4096,
    )

    @validator("message")
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError("메시지 내용은 필수입니다")

        # 텔레그램 메시지 길이 제한
        if len(v) > 4096:
            raise ValueError("메시지는 4096자를 초과할 수 없습니다")

        return v.strip()

    class Config:
        schema_extra = {
            "example": {
                "message": "🚀 AAPL 매수 신호 발생!\n현재가: $150.25 (+2.3%)\n시간: 2025-08-09 12:00:00"
            }
        }
