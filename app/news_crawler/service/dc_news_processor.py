from datetime import datetime
from app.news_crawler.infra.model.entity.content import Content
from app.news_crawler.infra.model.repository.content_repository import ContentRepository
from app.common.utils.telegram_notifier import send_news_telegram_message
from app.common.infra.database.config.database_config import SessionLocal


class DcNewsProcessor:
    def __init__(self, news_items: list):
        self.news_items = news_items
        self.session = SessionLocal()
        self.content_repo = ContentRepository(self.session)

    def run(self):
        try:
            for item in self.news_items:
                if self.content_repo.exists_by_hash(item["content_hash"]):
                    print(f"🔁 중복 스킵: {item['title']}")
                    continue

                # 날짜 처리
                try:
                    published_at = datetime.strptime(item["published_at"], "%Y-%m-%d %H:%M:%S")
                except:
                    published_at = datetime.now()

                # Content ORM 객체로 변환
                content = Content(
                    title=item["title"],
                    url=item["url"],
                    source=item.get("source", "dcinside"),
                    summary=item.get("summary"),
                    html=item.get("html", ""),
                    symbol=item.get("symbol", "DCINSIDE"),
                    content_hash=item["content_hash"],
                    published_at=published_at,
                    crawled_at=datetime.now()
                )

                self.content_repo.save(content)
                self.session.flush()

                # 텔레그램 전송
                send_news_telegram_message(
                    title=content.title,
                    summary=content.summary,
                    url=content.url,
                    published_at=content.published_at,
                    symbol=content.symbol
                )

            self.session.commit()
        except Exception as e:
            self.session.rollback()
            print(f"❌ 처리 중 예외 발생: {e}")
        finally:
            self.session.close()