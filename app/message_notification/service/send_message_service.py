import asyncio
from datetime import datetime

from app.common.infra.database.config.database_config import SessionLocal
from app.common.utils.telegram_notifier import send_text_message_async
from app.message_notification.infra.model.entity.message_log import MessageLog
from app.message_notification.infra.model.repository.message_log_repository import (
    MessageLogRepository,
)
import asyncio


class SendMessageService:
    def __init__(self):
        self.session = None
        self.repository = None

    def _get_session_and_repo(self):
        """세션과 리포지토리 지연 초기화"""
        if not self.session:
            self.session = SessionLocal()
            self.repository = MessageLogRepository(self.session)
        return self.session, self.repository

    def __del__(self):
        """소멸자에서 세션 정리"""
        if self.session:
            self.session.close()

    async def send_message(self, message: str):
        now = datetime.utcnow()

        try:
            # 1. 텔레그램으로 비동기 전송
            asyncio.create_task(send_text_message_async(message))

            # 2. DB에 로그 저장
            log = MessageLog(message=message, sent_at=now)
            self.repository.save(log)
            self.session.commit()

            print(f"✅ 메시지 전송 및 저장 완료: {message}")
        except Exception as e:
            self.session.rollback()
            print(f"❌ 메시지 전송 실패: {e}")
        finally:
            self.session.close()
