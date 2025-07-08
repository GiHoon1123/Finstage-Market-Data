from app.common.infra.database.config.database_config import SessionLocal
from app.common.utils.translate_to_korean import translate_to_korean
from app.common.utils.telegram_notifier import send_news_telegram_message
from app.news_crawler.infra.model.entity.content import Content
from app.news_crawler.infra.model.entity.content_translations import ContentTranslation
from app.news_crawler.infra.model.repository.content_repository import ContentRepository
from app.news_crawler.infra.model.repository.content_translation_repository import ContentTranslationRepository


class NewsProcessor:
    def __init__(self, news_items: list[dict]):
        self.news_items = news_items
        self.session = SessionLocal()
        self.content_repo = ContentRepository(self.session)
        self.translation_repo = ContentTranslationRepository(self.session)
        self.telegram_enabled = True

    def run(self):
        try:
            for item in self.news_items:
                if self._is_duplicate(item):
                    continue

                content = self._save_content(item)
                title_ko, summary_ko, symbol = self._save_translation(content)  
                self._send_notification(content, title_ko, summary_ko, symbol)  

            self.session.commit()
        except Exception as e:
            self.session.rollback()
            print(f"❌ 처리 중 예외 발생: {e}")
        finally:
            self.session.close()

    def _is_duplicate(self, item: dict) -> bool:
        if self.content_repo.exists_by_hash(item["content_hash"]):
            print(f"🔁 중복 스킵: {item['title']}")
            return True
        return False

    def _save_content(self, item: dict) -> Content:
        content = Content(
            symbol=item["symbol"],
            title=item["title"],
            summary=item["summary"],
            url=item["url"],
            html=item["html"],
            source=item["source"],
            crawled_at=item["crawled_at"],
            published_at=item["published_at"],
            content_hash=item["content_hash"],
        )
        self.content_repo.save(content)
        self.session.flush()
        return content

    def _save_translation(self, content: Content) -> tuple[str, str | None]:  # ✅ 수정
        title_ko = translate_to_korean(content.title)
        summary_ko = translate_to_korean(content.summary) if content.summary else None
        symbol = content.symbol 
        translation = ContentTranslation(
            content_id=content.id,
            language="ko",
            title_translated=title_ko,
            summary_translated=summary_ko,
            translator="google",
            published_at=content.published_at
        )
        self.translation_repo.save(translation)
        print(f"✅ 저장 완료: {content.title} → {title_ko}")
        return title_ko, summary_ko, symbol  # ✅ 번역 결과 반환

    def _send_notification(self, content: Content, title_ko: str, summary_ko: str, symbol: str):
        if not self.telegram_enabled:
            return

        try:
            send_news_telegram_message(
                title=title_ko,
                summary=summary_ko,
                url=content.url,
                published_at=content.published_at,
                symbol=symbol
            )
        except Exception as e:
            print(f"❌ 텔레그램 전송 실패: {e}")
