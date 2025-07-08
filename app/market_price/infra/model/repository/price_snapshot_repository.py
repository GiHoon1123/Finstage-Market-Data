from sqlalchemy.orm import Session
from datetime import datetime
from app.market_price.infra.model.entity.price_snapshots import PriceSnapshot


class PriceSnapshotRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, snapshot: PriceSnapshot):
        self.session.add(snapshot)

    def get_latest_by_symbol(self, symbol: str) -> PriceSnapshot | None:
        return (
            self.session.query(PriceSnapshot)
            .filter_by(symbol=symbol)
            .order_by(PriceSnapshot.snapshot_at.desc())
            .first()
        )

    def get_by_symbol_and_time(self, symbol: str, snapshot_at: datetime) -> PriceSnapshot | None:
        return (
            self.session.query(PriceSnapshot)
            .filter_by(symbol=symbol, snapshot_at=snapshot_at)
            .first()
        )

    def exists_by_symbol_and_snapshot_time(self, symbol: str, snapshot_at: datetime) -> bool:
        return (
            self.get_by_symbol_and_time(symbol, snapshot_at) is not None
        )
