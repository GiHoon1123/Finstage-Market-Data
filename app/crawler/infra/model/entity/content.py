from sqlalchemy import Column, BigInteger, String, Text, DateTime, Boolean
from datetime import datetime
from app.common.infra.database.config.database_config import Base

class Content(Base):
    __tablename__ = "contents"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="PK")
    symbol = Column(String(20), nullable=False, comment="종목 티커 (예: TSLA)")
    title = Column(Text, nullable=False, comment="기사 제목")
    summary = Column(Text, nullable=True, comment="기사 요약 또는 본문 일부")
    url = Column(Text, nullable=False, comment="기사 원본 URL")
    html = Column(Text, nullable=False, comment="기사 원본 URL")
    source = Column(String(255), nullable=True, comment="출처 도메인 (예: reuters.com)")
    crawled_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="크롤링 시각")
    published_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="기사 발행 시각")
    content_hash = Column(String(64), nullable=False, unique=True, comment="중복 방지를 위한 콘텐츠 해시")
    is_duplicate = Column(Boolean, default=False, comment="중복 여부")


    def __repr__(self):
        return f"<Content(symbol='{self.symbol}', title='{self.title[:30]}...')>"
