from app.market_price.infra.model.repository.price_snapshot_repository import (
    PriceSnapshotRepository,
)
from app.market_price.infra.model.entity.price_snapshots import PriceSnapshot
from app.common.infra.client.yahoo_price_client import YahooPriceClient
from app.common.infra.database.config.database_config import SessionLocal


class PriceSnapshotService:
    def __init__(self):
        self.session = None
        self.repository = None
        self.client = YahooPriceClient()

    def _get_session_and_repo(self):
        """세션과 리포지토리 지연 초기화"""
        if not self.session:
            self.session = SessionLocal()
            self.repository = PriceSnapshotRepository(self.session)
        return self.session, self.repository

    def __del__(self):
        """소멸자에서 세션 정리"""
        if self.session:
            self.session.close()

    def save_previous_close_if_needed(self, symbol: str):
        session = None
        try:
            session = SessionLocal()
            repository = PriceSnapshotRepository(session)
            close_price, snapshot_at = self.client.get_previous_close(symbol)

            if close_price is None or snapshot_at is None:
                print(f"⚠️ {symbol} 전일 종가 없음 (yfinance 응답 없음)")
                return

            existing = repository.get_by_symbol_and_time(symbol, snapshot_at)
            if existing:
                print(f"ℹ️ {symbol} {snapshot_at.date()} 종가 이미 존재")
                return

            snapshot = PriceSnapshot(
                symbol=symbol,
                source="yahoo",
                close=close_price,
                snapshot_at=snapshot_at,
            )

            repository.save(snapshot)
            session.commit()
            print(f"📦 {symbol} 전일 종가 저장: {close_price} ({snapshot_at.date()})")
        except Exception as e:
            if session:
                session.rollback()
            print(f"❌ {symbol} 종가 저장 실패: {e}")
        finally:
            if session:
                session.close()

    def save_previous_high_if_needed(self, symbol: str):
        session = None
        try:
            session = SessionLocal()
            repository = PriceSnapshotRepository(session)
            high_price, snapshot_at = self.client.get_previous_high(symbol)

            if high_price is None or snapshot_at is None:
                print(f"⚠️ {symbol} 전일 고점 없음 (yfinance 응답 없음)")
                return

            existing = repository.get_by_symbol_and_time(symbol, snapshot_at)
            if existing and existing.high is not None:
                print(f"ℹ️ {symbol} {snapshot_at.date()} 고점 이미 존재")
                return

            snapshot = PriceSnapshot(
                symbol=symbol,
                source="yahoo",
                high=high_price,
                snapshot_at=snapshot_at,
            )

            repository.save(snapshot)
            session.commit()
            print(f"📦 {symbol} 전일 고점 저장: {high_price} ({snapshot_at.date()})")
        except Exception as e:
            if session:
                session.rollback()
            print(f"❌ {symbol} 고점 저장 실패: {e}")
        finally:
            if session:
                session.close()

    def save_previous_low_if_needed(self, symbol: str):
        session = None
        try:
            session = SessionLocal()
            repository = PriceSnapshotRepository(session)
            low_price, snapshot_at = self.client.get_previous_low(symbol)

            if low_price is None or snapshot_at is None:
                print(f"⚠️ {symbol} 전일 저점 없음 (yfinance 응답 없음)")
                return

            existing = repository.get_by_symbol_and_time(symbol, snapshot_at)
            if existing and existing.low is not None:
                print(f"ℹ️ {symbol} {snapshot_at.date()} 저점 이미 존재")
                return

            snapshot = PriceSnapshot(
                symbol=symbol,
                source="yahoo",
                low=low_price,
                snapshot_at=snapshot_at,
            )

            repository.save(snapshot)
            session.commit()
            print(f"📦 {symbol} 전일 저점 저장: {low_price} ({snapshot_at.date()})")
        except Exception as e:
            if session:
                session.rollback()
            print(f"❌ {symbol} 저점 저장 실패: {e}")
        finally:
            if session:
                session.close()

    def get_previous_high(self, symbol: str) -> float | None:
        session = None
        try:
            session = SessionLocal()
            repository = PriceSnapshotRepository(session)
            return repository.get_previous_high(symbol)
        except Exception as e:
            print(f"❌ {symbol} 전일 고점 조회 실패: {e}")
            return None
        finally:
            if session:
                session.close()

    def get_previous_low(self, symbol: str) -> float | None:
        session = None
        try:
            session = SessionLocal()
            repository = PriceSnapshotRepository(session)
            return repository.get_previous_low(symbol)
        except Exception as e:
            print(f"❌ {symbol} 전일 저점 조회 실패: {e}")
            return None
        finally:
            if session:
                session.close()

    def get_latest_snapshot(self, symbol: str) -> PriceSnapshot | None:
        session = None
        try:
            session = SessionLocal()
            repository = PriceSnapshotRepository(session)
            return repository.get_latest_by_symbol(symbol)
        except Exception as e:
            print(f"❌ {symbol} 종가 조회 실패: {e}")
            return None
        finally:
            if session:
                session.close()
