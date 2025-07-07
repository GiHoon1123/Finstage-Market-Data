from sqlalchemy.orm import Session
from app.crawler.infra.model.entity.content import Content


class ContentRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, content: Content):
        self.session.add(content)

    def get_by_hash(self, content_hash: str) -> Content | None:
        return (
            self.session.query(Content)
            .filter_by(content_hash=content_hash)
            .first()
        )

    def exists_by_hash(self, content_hash: str) -> bool:
        return (
            self.session.query(Content)
            .filter_by(content_hash=content_hash)
            .first()
            is not None
        )

    def get_by_symbol(self, symbol: str, limit: int = 50) -> list[Content]:
        return (
            self.session.query(Content)
            .filter_by(symbol=symbol)
            .order_by(Content.crawled_at.desc())
            .limit(limit)
            .all()
        )
