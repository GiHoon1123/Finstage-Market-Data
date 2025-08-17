from app.common.infra.database.config.database_config import SessionLocal
from app.common.utils.translate_to_korean import translate_to_korean
from app.common.utils.telegram_notifier import send_news_telegram_message
from app.news_crawler.infra.model.entity.content import Content
from app.news_crawler.infra.model.entity.content_translations import ContentTranslation
from app.news_crawler.infra.model.repository.content_repository import ContentRepository
from app.news_crawler.infra.model.repository.content_translation_repository import (
    ContentTranslationRepository,
)


class NewsProcessor:
    def __init__(self, news_items: list[dict], telegram_enabled: bool = False):
        self.news_items = news_items
        self.session = None
        self.content_repo = None
        self.translation_repo = None
        self.telegram_enabled = telegram_enabled  # 텔레그램 알림 선택적 활성화

    def _get_session_and_repos(self):
        """세션과 리포지토리 지연 초기화"""
        if not self.session:
            self.session = SessionLocal()
            self.content_repo = ContentRepository(self.session)
            self.translation_repo = ContentTranslationRepository(self.session)
        return self.session, self.content_repo, self.translation_repo

    def __del__(self):
        """소멸자에서 세션 정리"""
        if self.session:
            self.session.close()

    def run(self):
        """뉴스 데이터베이스 저장만 수행 (텔레그램 전송 제외)"""
        try:
            session, content_repo, translation_repo = self._get_session_and_repos()

            for item in self.news_items:
                try:
                    if self._is_duplicate(item):
                        continue

                    content = self._save_content(item)
                    title_ko, summary_ko, symbol = self._save_translation(content)
                    
                    # 텔레그램 전송 (선택적)
                    if self.telegram_enabled:
                        try:
                            self._send_notification(content, title_ko, summary_ko, symbol)
                        except Exception as telegram_error:
                            print(f"⚠️ 텔레그램 전송 실패 (저장은 성공): {telegram_error}")
                            # 텔레그램 실패해도 저장은 계속 진행
                except Exception as item_error:
                    print(f"❌ 개별 뉴스 처리 실패: {item_error}")
                    continue  # 개별 뉴스 실패해도 계속 진행

            session.commit()
        except Exception as e:
            if self.session:
                self.session.rollback()
            print(f"❌ 처리 중 예외 발생: {e}")
        finally:
            if self.session:
                self.session.close()

    def _is_duplicate(self, item: dict) -> bool:
        session, content_repo, translation_repo = self._get_session_and_repos()
        if content_repo.exists_by_hash(item["content_hash"]):
            print(f"🔁 중복 스킵: {item['title']}")
            return True
        return False

    def _save_content(self, item: dict) -> Content:
        session, content_repo, translation_repo = self._get_session_and_repos()
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
        content_repo.save(content)
        session.flush()
        return content

    def _save_translation(self, content: Content) -> tuple[str, str | None]:  # ✅ 수정
        session, content_repo, translation_repo = self._get_session_and_repos()
        title_ko = translate_to_korean(content.title)
        summary_ko = translate_to_korean(content.summary) if content.summary else None
        symbol = content.symbol
        translation = ContentTranslation(
            content_id=content.id,
            language="ko",
            title_translated=title_ko,
            summary_translated=summary_ko,
            translator="google",
            published_at=content.published_at,
        )
        translation_repo.save(translation)
        session.flush()  # 세션 플러시 추가
        print(f"✅ 저장 완료: {content.title} → {title_ko}")
        return title_ko, summary_ko, symbol  # ✅ 번역 결과 반환

    def _send_notification(
        self, content: Content, title_ko: str, summary_ko: str, symbol: str
    ):
        # telegram_enabled 속성이 없으면 기본값으로 True 사용
        telegram_enabled = getattr(self, "telegram_enabled", True)

        if not telegram_enabled:
            return

        try:
            send_news_telegram_message(
                title=title_ko,
                summary=summary_ko,
                url=content.url,
                published_at=content.published_at,
                symbol=symbol,
            )
        except Exception as e:
            print(f"❌ 텔레그램 전송 실패: {e}")
