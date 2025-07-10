from sqlalchemy.orm import Session
from app.market_price.infra.model.entity.price_snapshots import PriceSnapshot
from datetime import timedelta, datetime
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

    def get_previous_high(self, symbol: str) -> float | None:
            latest = self.get_latest_by_symbol(symbol)
            if not latest:
                return None

            prev_day = latest.snapshot_at.date() - timedelta(days=1)
            snapshot = (
                self.session.query(PriceSnapshot)
                .filter(
                    PriceSnapshot.symbol == symbol,
                    PriceSnapshot.snapshot_at >= datetime.combine(prev_day, datetime.min.time()),
                    PriceSnapshot.snapshot_at < datetime.combine(prev_day, datetime.max.time()),
                    PriceSnapshot.high != None
                )
                .order_by(PriceSnapshot.snapshot_at.desc())
                .first()
            )
            return snapshot.high if snapshot else None

    def get_previous_low(self, symbol: str) -> float | None:
        latest = self.get_latest_by_symbol(symbol)
        if not latest:
            return None

        prev_day = latest.snapshot_at.date() - timedelta(days=1)
        snapshot = (
            self.session.query(PriceSnapshot)
            .filter(
                PriceSnapshot.symbol == symbol,
                PriceSnapshot.snapshot_at >= datetime.combine(prev_day, datetime.min.time()),
                PriceSnapshot.snapshot_at < datetime.combine(prev_day, datetime.max.time()),
                PriceSnapshot.low != None
            )
            .order_by(PriceSnapshot.snapshot_at.desc())
            .first()
        )
        return snapshot.low if snapshot else None

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
