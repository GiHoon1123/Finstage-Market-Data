from sqlalchemy.orm import Session
from app.news_crawler.infra.model.entity.content_sentiments import ContentSentiment


class ContentSentimentRepository:
    """
    뉴스 감정분석 결과를 관리하는 리포지토리
    
    감정분석 결과의 저장, 조회, 통계 기능을 제공합니다.
    """
    
    def __init__(self, session: Session):
        self.session = session

    def save(self, sentiment: ContentSentiment):
        """감정분석 결과 저장"""
        self.session.add(sentiment)

    def get_by_content_id(self, content_id: int) -> ContentSentiment | None:
        """콘텐츠 ID로 감정분석 결과 조회"""
        return (
            self.session.query(ContentSentiment)
            .filter_by(content_id=content_id)
            .first()
        )

    def get_by_symbol(self, symbol: str, limit: int = 50) -> list[ContentSentiment]:
        """심볼별 감정분석 결과 조회"""
        return (
            self.session.query(ContentSentiment)
            .join(ContentSentiment.content)
            .filter(ContentSentiment.content.has(symbol=symbol))
            .order_by(ContentSentiment.analyzed_at.desc())
            .limit(limit)
            .all()
        )

    def get_positive_news(self, symbol: str, limit: int = 20) -> list[ContentSentiment]:
        """긍정적 뉴스 조회"""
        return (
            self.session.query(ContentSentiment)
            .join(ContentSentiment.content)
            .filter(
                ContentSentiment.content.has(symbol=symbol),
                ContentSentiment.sentiment_score > 0.1
            )
            .order_by(ContentSentiment.analyzed_at.desc())
            .limit(limit)
            .all()
        )

    def get_negative_news(self, symbol: str, limit: int = 20) -> list[ContentSentiment]:
        """부정적 뉴스 조회"""
        return (
            self.session.query(ContentSentiment)
            .join(ContentSentiment.content)
            .filter(
                ContentSentiment.content.has(symbol=symbol),
                ContentSentiment.sentiment_score < -0.1
            )
            .order_by(ContentSentiment.analyzed_at.desc())
            .limit(limit)
            .all()
        )

    def get_market_sensitive_news(self, symbol: str, limit: int = 20) -> list[ContentSentiment]:
        """시장 민감 뉴스 조회"""
        return (
            self.session.query(ContentSentiment)
            .join(ContentSentiment.content)
            .filter(
                ContentSentiment.content.has(symbol=symbol),
                ContentSentiment.is_market_sensitive == True
            )
            .order_by(ContentSentiment.analyzed_at.desc())
            .limit(limit)
            .all()
        )

    def exists_by_content_id(self, content_id: int) -> bool:
        """콘텐츠 ID로 감정분석 결과 존재 여부 확인"""
        return (
            self.session.query(ContentSentiment)
            .filter_by(content_id=content_id)
            .first()
            is not None
        )
