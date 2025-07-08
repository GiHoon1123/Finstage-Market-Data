from app.market_price.infra.model.repository.price_high_record_repository import PriceHighRecordRepository
from app.market_price.infra.model.entity.price_high_records import PriceHighRecord
from app.market_price.infra.client.yahoo_price_client import YahooPriceClient
from app.common.infra.database.config.database_config import SessionLocal


class PriceHighRecordService:
    def __init__(self):
        self.session = SessionLocal()
        self.repository = PriceHighRecordRepository(self.session)
        self.client = YahooPriceClient()

    def update_all_time_high(self, symbol: str):
        try:
            current_price, recorded_at = self.client.get_all_time_high(symbol)
            source = "yahoo"

            existing = self.repository.get_high_record(symbol)

            if existing is None or current_price > existing.price:
                new_high = PriceHighRecord(
                    symbol=symbol,
                    source=source,
                    price=current_price,
                    recorded_at=recorded_at
                )
                self.repository.save(new_high)
                self.session.commit()
                print(f"🚀 {symbol} 최고가 갱신: {current_price}")
            else:
                print(f"ℹ️ {symbol} 최고가 유지 중: {existing.price}")
        except Exception as e:
            self.session.rollback()
            print(f"❌ 최고가 저장 중 오류: {e}")
        finally:
            self.session.close()

    def get_latest_record(self, symbol: str) -> PriceHighRecord | None:
        try:
            return self.repository.get_high_record(symbol)
        except Exception as e:
            print(f"❌ {symbol} 최고가 조회 실패: {e}")
            return None
