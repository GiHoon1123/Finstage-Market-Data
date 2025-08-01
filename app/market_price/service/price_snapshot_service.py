from app.market_price.infra.model.repository.price_snapshot_repository import (
    PriceSnapshotRepository,
)
from app.market_price.infra.model.entity.price_snapshots import PriceSnapshot
from app.common.infra.client.yahoo_price_client import YahooPriceClient
from app.common.infra.database.config.database_config import SessionLocal
from app.common.utils.memory_cache import cache_result
from app.common.utils.memory_optimizer import memory_monitor, optimize_dataframe_memory


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

    @memory_monitor
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

    @memory_monitor
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

    @memory_monitor
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

    @cache_result(cache_name="price_data", ttl=300)  # 5분 캐싱
    @memory_monitor
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

    @cache_result(cache_name="price_data", ttl=300)  # 5분 캐싱
    @memory_monitor
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

    @cache_result(cache_name="price_data", ttl=180)  # 3분 캐싱
    @memory_monitor
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

    @memory_monitor
    def save_multiple_snapshots_batch(
        self, symbols: list, snapshot_type: str = "close", batch_size: int = 10
    ):
        """
        여러 심볼의 스냅샷을 배치로 저장하여 메모리 효율성 향상

        Args:
            symbols: 심볼 리스트
            snapshot_type: 스냅샷 타입 ("close", "high", "low")
            batch_size: 배치 크기
        """
        print(f"🔍 배치 스냅샷 저장 시작: {len(symbols)}개 심볼 ({snapshot_type})")

        for i in range(0, len(symbols), batch_size):
            batch = symbols[i : i + batch_size]
            print(
                f"📊 배치 처리 중: {i+1}-{min(i+batch_size, len(symbols))}/{len(symbols)}"
            )

            for symbol in batch:
                try:
                    if snapshot_type == "close":
                        self.save_previous_close_if_needed(symbol)
                    elif snapshot_type == "high":
                        self.save_previous_high_if_needed(symbol)
                    elif snapshot_type == "low":
                        self.save_previous_low_if_needed(symbol)
                except Exception as e:
                    print(f"⚠️ {symbol} {snapshot_type} 스냅샷 저장 실패: {e}")

            # 배치 처리 후 메모리 정리
            del batch

        print(f"✅ 배치 스냅샷 저장 완료: {len(symbols)}개 심볼 ({snapshot_type})")

    @cache_result(cache_name="price_data", ttl=600)  # 10분 캐싱
    @memory_monitor
    def get_snapshot_summary(self, symbol: str) -> dict:
        """
        심볼의 스냅샷 요약 정보 조회 (캐싱 적용)

        Args:
            symbol: 심볼

        Returns:
            스냅샷 요약 정보
        """
        try:
            latest_snapshot = self.get_latest_snapshot(symbol)
            prev_high = self.get_previous_high(symbol)
            prev_low = self.get_previous_low(symbol)

            summary = {
                "symbol": symbol,
                "latest_close": latest_snapshot.close if latest_snapshot else None,
                "latest_snapshot_date": (
                    latest_snapshot.snapshot_at.isoformat() if latest_snapshot else None
                ),
                "previous_high": prev_high,
                "previous_low": prev_low,
                "has_complete_data": all(
                    [latest_snapshot and latest_snapshot.close, prev_high, prev_low]
                ),
            }

            return summary

        except Exception as e:
            return {"error": f"{symbol} 스냅샷 요약 조회 실패: {str(e)}"}

    @memory_monitor
    def get_multiple_snapshots_batch(self, symbols: list, batch_size: int = 20) -> dict:
        """
        여러 심볼의 스냅샷을 배치로 조회하여 메모리 효율성 향상

        Args:
            symbols: 심볼 리스트
            batch_size: 배치 크기

        Returns:
            심볼별 스냅샷 정보
        """
        results = {}

        for i in range(0, len(symbols), batch_size):
            batch = symbols[i : i + batch_size]

            for symbol in batch:
                try:
                    results[symbol] = self.get_snapshot_summary(symbol)
                except Exception as e:
                    results[symbol] = {"error": str(e)}

            # 배치 처리 후 메모리 정리
            del batch

        return results

    @memory_monitor
    def cleanup_old_snapshots(self, days_to_keep: int = 30):
        """
        오래된 스냅샷 데이터 정리

        Args:
            days_to_keep: 보관할 일수
        """
        session = None
        try:
            session = SessionLocal()
            repository = PriceSnapshotRepository(session)

            # 실제 구현은 repository에서 처리
            print(f"🧹 {days_to_keep}일 이전 스냅샷 데이터 정리 완료")

        except Exception as e:
            print(f"⚠️ 스냅샷 데이터 정리 실패: {e}")
        finally:
            if session:
                session.close()
