from sqlalchemy.orm import Session
from app.market_price.infra.model.entity.price_high_records import PriceHighRecord


class PriceHighRecordRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, record: PriceHighRecord):
        self.session.add(record)

    def get_high_record(self, symbol: str) -> PriceHighRecord | None:
        return (
            self.session.query(PriceHighRecord)
            .filter_by(symbol=symbol)
            .order_by(PriceHighRecord.price.desc())
            .first()
        )

    def exists_by_symbol_and_price(self, symbol: str, price: float) -> bool:
        return (
            self.session.query(PriceHighRecord)
            .filter_by(symbol=symbol, price=price)
            .first()
            is not None
        )
