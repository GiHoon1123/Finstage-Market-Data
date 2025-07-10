from datetime import datetime
from app.market_price.infra.model.repository.price_snapshot_repository import PriceSnapshotRepository
from app.market_price.infra.model.entity.price_snapshots import PriceSnapshot
from app.common.infra.client.yahoo_price_client import YahooPriceClient
from app.common.infra.database.config.database_config import SessionLocal


class PriceSnapshotService:
    def __init__(self):
        self.session = SessionLocal()
        self.repository = PriceSnapshotRepository(self.session)
        self.client = YahooPriceClient()

    def save_previous_close_if_needed(self, symbol: str):
        try:
            close_price, snapshot_at = self.client.get_previous_close(symbol)

            if close_price is None or snapshot_at is None:
                print(f"⚠️ {symbol} 전일 종가 없음 (yfinance 응답 없음)")
                return

            existing = self.repository.get_by_symbol_and_time(symbol, snapshot_at)
            if existing:
                print(f"ℹ️ {symbol} {snapshot_at.date()} 종가 이미 존재")
                return

            snapshot = PriceSnapshot(
                symbol=symbol,
                source="yahoo",
                close=close_price,
                snapshot_at=snapshot_at,
            )

            self.repository.save(snapshot)
            self.session.commit()
            print(f"📦 {symbol} 전일 종가 저장: {close_price} ({snapshot_at.date()})")
        except Exception as e:
            self.session.rollback()
            print(f"❌ {symbol} 종가 저장 실패: {e}")
        finally:
            self.session.close()

    def get_latest_snapshot(self, symbol: str) -> PriceSnapshot | None:
        try:
            return self.repository.get_latest_by_symbol(symbol)
        except Exception as e:
            print(f"❌ {symbol} 종가 조회 실패: {e}")
            return None
