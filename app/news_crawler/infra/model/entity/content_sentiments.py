from sqlalchemy import Column, BigInteger, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.common.infra.database.config.database_config import Base
from app.news_crawler.infra.model.entity.content import Content


class ContentSentiment(Base):
    """
    뉴스 콘텐츠의 감정분석 결과를 저장하는 엔티티
    
    VADER Lexicon 기반 감정분석 결과를 저장하며,
    시장 영향도와 신뢰도를 포함합니다.
    """
    __tablename__ = "content_sentiments"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="PK")
    
    # 외래키: 원본 콘텐츠 참조
    content_id = Column(BigInteger, ForeignKey("contents.id", ondelete="CASCADE"), nullable=False, comment="원본 콘텐츠 FK")
    
    # 감정분석 결과
    sentiment_score = Column(Float, nullable=False, comment="감정 점수 (-1.0 ~ +1.0)")
    sentiment_label = Column(String(20), nullable=False, comment="감정 라벨 (positive, negative, neutral)")
    confidence = Column(Float, nullable=False, comment="분석 신뢰도 (0.0 ~ 1.0)")
    
    # VADER 세부 점수
    positive_score = Column(Float, nullable=False, comment="긍정 점수 (0.0 ~ 1.0)")
    negative_score = Column(Float, nullable=False, comment="부정 점수 (0.0 ~ 1.0)")
    neutral_score = Column(Float, nullable=False, comment="중립 점수 (0.0 ~ 1.0)")
    compound_score = Column(Float, nullable=False, comment="복합 점수 (-1.0 ~ +1.0)")
    
    # 시장 영향도
    market_impact_score = Column(Float, nullable=True, comment="시장 영향도 점수 (-1.0 ~ +1.0)")
    is_market_sensitive = Column(Boolean, default=False, comment="시장 민감 뉴스 여부")
    
    # 분석 메타데이터
    analyzer_type = Column(String(50), nullable=False, default="vader", comment="사용한 분석기 (vader, textblob 등)")
    analyzed_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="분석 시각")
    
    # 관계 설정
    content = relationship("Content", backref="sentiments", lazy="joined")

    def __repr__(self):
        return f"<ContentSentiment(content_id={self.content_id}, sentiment={self.sentiment_label}, score={self.sentiment_score:.3f})>"
    
    def is_positive(self) -> bool:
        """긍정적 감정인지 확인"""
        return self.sentiment_score > 0.1
    
    def is_negative(self) -> bool:
        """부정적 감정인지 확인"""
        return self.sentiment_score < -0.1
    
    def is_neutral(self) -> bool:
        """중립적 감정인지 확인"""
        return -0.1 <= self.sentiment_score <= 0.1
    
    def is_market_sensitive_news(self) -> bool:
        """시장에 민감한 뉴스인지 확인"""
        return abs(self.market_impact_score or 0) > 0.5
