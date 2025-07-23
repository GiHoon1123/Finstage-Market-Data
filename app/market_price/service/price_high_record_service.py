from app.market_price.infra.model.repository.price_high_record_repository import (
    PriceHighRecordRepository,
)
from app.market_price.infra.model.entity.price_high_records import PriceHighRecord
from app.common.infra.client.yahoo_price_client import YahooPriceClient
from app.common.infra.database.config.database_config import SessionLocal


class PriceHighRecordService:
    def __init__(self):
        self.session = None
        self.repository = None
        self.client = YahooPriceClient()

    def _get_session_and_repo(self):
        """세션과 리포지토리 지연 초기화"""
        if not self.session:
            self.session = SessionLocal()
            self.repository = PriceHighRecordRepository(self.session)
        return self.session, self.repository

    def __del__(self):
        """소멸자에서 세션 정리"""
        if self.session:
            self.session.close()

    def update_all_time_high(self, symbol: str):
        session = None
        try:
            session, repository = self._get_session_and_repo()
            current_price, recorded_at = self.client.get_all_time_high(symbol)
            source = "yahoo"

            existing = repository.get_high_record(symbol)

            if existing is None or current_price > existing.price:
                new_high = PriceHighRecord(
                    symbol=symbol,
                    source=source,
                    price=current_price,
                    recorded_at=recorded_at,
                )
                repository.save(new_high)
                session.commit()
                print(f"🚀 {symbol} 최고가 갱신: {current_price}")
            else:
                print(f"ℹ️ {symbol} 최고가 유지 중: {existing.price}")
        except Exception as e:
            if session:
                session.rollback()
            print(f"❌ 최고가 저장 중 오류: {e}")
        finally:
            if session:
                session.close()

    def get_latest_record(self, symbol: str) -> PriceHighRecord | None:
        session = None
        try:
            session, repository = self._get_session_and_repo()
            return repository.get_high_record(symbol)
        except Exception as e:
            print(f"❌ {symbol} 최고가 조회 실패: {e}")
            return None
        finally:
            if session:
                session.close()
