from sqlalchemy.orm import Session
from app.crawler.infra.model.entity.content_translations import ContentTranslation

class ContentTranslationRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, translation: ContentTranslation):
        self.session.add(translation)

    def get_by_content_id(self, content_id: int) -> list[ContentTranslation]:
        return (
            self.session.query(ContentTranslation)
            .filter_by(content_id=content_id)
            .order_by(ContentTranslation.translated_at.desc())
            .all()
        )

    def get_by_content_id_and_lang(self, content_id: int, lang: str) -> ContentTranslation | None:
        return (
            self.session.query(ContentTranslation)
            .filter_by(content_id=content_id, language=lang)
            .first()
        )
