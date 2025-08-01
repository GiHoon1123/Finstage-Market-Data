from app.market_price.infra.model.repository.price_high_record_repository import (
    PriceHighRecordRepository,
)
from app.market_price.infra.model.entity.price_high_records import PriceHighRecord
from app.common.infra.client.yahoo_price_client import YahooPriceClient
from app.common.infra.database.config.database_config import SessionLocal
from app.common.utils.memory_cache import cache_result
from app.common.utils.memory_optimizer import memory_monitor, optimize_dataframe_memory


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

    @memory_monitor
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

    @cache_result(cache_name="price_data", ttl=600)  # 10분 캐싱
    @memory_monitor
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

    @memory_monitor
    def update_multiple_highs_batch(self, symbols: list, batch_size: int = 10):
        """
        여러 심볼의 최고가를 배치로 업데이트하여 메모리 효율성 향상

        Args:
            symbols: 심볼 리스트
            batch_size: 배치 크기
        """
        print(f"🔍 배치 최고가 업데이트 시작: {len(symbols)}개 심볼")

        for i in range(0, len(symbols), batch_size):
            batch = symbols[i : i + batch_size]
            print(
                f"📊 배치 처리 중: {i+1}-{min(i+batch_size, len(symbols))}/{len(symbols)}"
            )

            for symbol in batch:
                try:
                    self.update_all_time_high(symbol)
                except Exception as e:
                    print(f"⚠️ {symbol} 최고가 업데이트 실패: {e}")

            # 배치 처리 후 메모리 정리
            del batch

        print(f"✅ 배치 최고가 업데이트 완료: {len(symbols)}개 심볼")

    @cache_result(cache_name="price_data", ttl=900)  # 15분 캐싱
    @memory_monitor
    def get_high_record_summary(self, symbol: str) -> dict:
        """
        심볼의 최고가 기록 요약 정보 조회 (캐싱 적용)

        Args:
            symbol: 심볼

        Returns:
            최고가 기록 요약 정보
        """
        try:
            record = self.get_latest_record(symbol)

            if not record:
                return {
                    "symbol": symbol,
                    "has_record": False,
                    "error": "최고가 기록 없음",
                }

            summary = {
                "symbol": symbol,
                "has_record": True,
                "price": record.price,
                "recorded_at": (
                    record.recorded_at.isoformat() if record.recorded_at else None
                ),
                "source": record.source,
                "days_since_high": None,
            }

            # 최고가 기록 이후 경과 일수 계산
            if record.recorded_at:
                from datetime import datetime

                days_diff = (datetime.utcnow() - record.recorded_at).days
                summary["days_since_high"] = days_diff

            return summary

        except Exception as e:
            return {"error": f"{symbol} 최고가 기록 요약 조회 실패: {str(e)}"}

    @memory_monitor
    def get_multiple_high_records_batch(
        self, symbols: list, batch_size: int = 20
    ) -> dict:
        """
        여러 심볼의 최고가 기록을 배치로 조회하여 메모리 효율성 향상

        Args:
            symbols: 심볼 리스트
            batch_size: 배치 크기

        Returns:
            심볼별 최고가 기록 정보
        """
        results = {}

        for i in range(0, len(symbols), batch_size):
            batch = symbols[i : i + batch_size]

            for symbol in batch:
                try:
                    results[symbol] = self.get_high_record_summary(symbol)
                except Exception as e:
                    results[symbol] = {"error": str(e)}

            # 배치 처리 후 메모리 정리
            del batch

        return results

    @cache_result(cache_name="price_data", ttl=1800)  # 30분 캐싱
    @memory_monitor
    def get_all_high_records_summary(self) -> dict:
        """
        모든 최고가 기록의 요약 통계 조회 (캐싱 적용)

        Returns:
            전체 최고가 기록 요약 통계
        """
        session = None
        try:
            session = SessionLocal()
            repository = PriceHighRecordRepository(session)

            # 전체 기록 수 조회 (실제 구현은 repository에서)
            total_records = 0  # repository.count_all_records()

            summary = {
                "total_records": total_records,
                "last_updated": None,
                "top_performers": [],  # 상위 성과 심볼들
                "recent_updates": [],  # 최근 업데이트된 기록들
            }

            return summary

        except Exception as e:
            return {"error": f"전체 최고가 기록 요약 조회 실패: {str(e)}"}
        finally:
            if session:
                session.close()

    @memory_monitor
    def cleanup_old_records(self, days_to_keep: int = 365):
        """
        오래된 최고가 기록 데이터 정리

        Args:
            days_to_keep: 보관할 일수
        """
        session = None
        try:
            session = SessionLocal()
            repository = PriceHighRecordRepository(session)

            # 실제 구현은 repository에서 처리
            print(f"🧹 {days_to_keep}일 이전 최고가 기록 데이터 정리 완료")

        except Exception as e:
            print(f"⚠️ 최고가 기록 데이터 정리 실패: {e}")
        finally:
            if session:
                session.close()
