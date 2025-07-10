from app.message_notification.service.send_message_service import SendMessageService

service = SendMessageService()

async def handle_send_message(message: str):
    await service.send_message(message)
