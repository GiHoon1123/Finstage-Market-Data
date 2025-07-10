from sqlalchemy.orm import Session
from app.message_notification.infra.model.entity.message_log import MessageLog
from datetime import datetime

class MessageLogRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, log: MessageLog):
        self.session.add(log)

    def get_all(self) -> list[MessageLog]:
        return self.session.query(MessageLog).order_by(MessageLog.sent_at.desc()).all()

    def get_by_id(self, log_id: int) -> MessageLog | None:
        return self.session.query(MessageLog).filter_by(id=log_id).first()

    def get_latest(self) -> MessageLog | None:
        return self.session.query(MessageLog).order_by(MessageLog.sent_at.desc()).first()
