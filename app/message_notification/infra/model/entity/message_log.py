from sqlalchemy import Column, BigInteger, String, DateTime
from datetime import datetime
from app.common.infra.database.config.database_config import Base

class MessageLog(Base):
    __tablename__ = "message_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="PK")
    message = Column(String(1000), nullable=False, comment="전송된 메시지 내용")
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="메시지 전송 시각")

    def __repr__(self):
        return f"<MessageLog(id={self.id}, sent_at={self.sent_at}, message={self.message[:30]}...)>"
