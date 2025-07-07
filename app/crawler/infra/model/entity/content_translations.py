from sqlalchemy import Column, BigInteger, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.common.infra.database.config.database_config import Base


class ContentTranslation(Base):
    __tablename__ = "content_translations"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="PK")
    
    content_id = Column(BigInteger, ForeignKey("contents.id", ondelete="CASCADE"), nullable=False, comment="원본 콘텐츠 FK")
    language = Column(String(10), nullable=False, default="ko", comment="번역 언어 (예: ko)")
    title_translated = Column(Text, nullable=True, comment="번역된 제목")
    summary_translated = Column(Text, nullable=True, comment="번역된 요약")
    translator = Column(String(50), nullable=True, comment="사용한 번역기 (예: openai, deepl, papago 등)")
    translated_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="번역 시각")
    published_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="기사 발행 시각")

    content = relationship("Content", backref="translations")

    def __repr__(self):
        return f"<ContentTranslation(content_id={self.content_id}, lang={self.language})>"
