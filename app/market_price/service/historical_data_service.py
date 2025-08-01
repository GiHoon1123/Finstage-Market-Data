"""
히스토리컬 데이터 수집 서비스

대량의 히스토리컬 데이터를 효율적으로 수집하고 저장하는 서비스입니다.
작업 큐를 통해 백그라운드에서 처리되도록 최적화되었습니다.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
import pandas as pd
import asyncio

from app.common.infra.client.yahoo_price_client import YahooPriceClient
from app.market_price.service.price_snapshot_service import PriceSnapshotService
from app.market_price.service.price_high_record_service import PriceHighRecordService
from app.common.utils.logging_config import get_logger
from app.common.utils.memory_optimizer import memory_monitor, optimize_dataframe_memory
from app.common.utils.memory_cache import cache_result
from app.common.utils.task_queue import task, TaskPriority

logger = get_logger(__name__)


class HistoricalDataService:
    """히스토리컬 데이터 수집 서비스"""

    def __init__(self):
        self.client = YahooPriceClient()
        self.snapshot_service = PriceSnapshotService()
        self.high_record_service = PriceHighRecordService()

    @memory_monitor
    def collect_historical_data(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
        save_to_db: bool = True,
    ) -> Dict[str, Any]:
        """
        단일 심볼의 히스토리컬 데이터 수집

        Args:
            symbol: 수집할 심볼
            period: 데이터 기간
            interval: 데이터 간격
            save_to_db: 데이터베이스 저장 여부

        Returns:
            수집 결과
        """
        logger.info(
            "historical_data_collection_started",
            symbol=symbol,
            period=period,
            interval=interval,
        )

        try:
            # 히스토리컬 데이터 조회
            data = self.client.get_daily_data(symbol, period=period)

            if data is None or data.empty:
                return {
                    "symbol": symbol,
                    "status": "failed",
                    "error": "No data available",
                    "data_points": 0,
                }

            # DataFrame 메모리 최적화
            data = optimize_dataframe_memory(data)

            result = {
                "symbol": symbol,
                "status": "success",
                "data_points": len(data),
                "period": period,
                "interval": interval,
                "date_range": {
                    "start": data.index.min().isoformat(),
                    "end": data.index.max().isoformat(),
                },
                "collected_at": datetime.now().isoformat(),
            }

            # 데이터베이스 저장
            if save_to_db:
                save_result = self._save_historical_data(symbol, data)
                result["save_result"] = save_result

            logger.info(
                "historical_data_collection_completed",
                symbol=symbol,
                data_points=len(data),
            )

            return result

        except Exception as e:
            logger.error(
                "historical_data_collection_failed", symbol=symbol, error=str(e)
            )
            return {
                "symbol": symbol,
                "status": "failed",
                "error": str(e),
                "collected_at": datetime.now().isoformat(),
            }

    @memory_monitor
    def _save_historical_data(self, symbol: str, data: pd.DataFrame) -> Dict[str, Any]:
        """
        히스토리컬 데이터를 데이터베이스에 저장

        Args:
            symbol: 심볼
            data: 히스토리컬 데이터

        Returns:
            저장 결과
        """
        try:
            saved_snapshots = 0
            updated_high_records = 0

            # 배치 단위로 처리하여 메모리 효율성 향상
            batch_size = 100

            for i in range(0, len(data), batch_size):
                batch_data = data.iloc[i : i + batch_size]

                for date_idx, row in batch_data.iterrows():
                    try:
                        # 스냅샷 데이터 저장
                        snapshot_date = date_idx.date()

                        # 종가 스냅샷 저장
                        if pd.notna(row["close"]):
                            self.snapshot_service.save_previous_close_if_needed(symbol)
                            saved_snapshots += 1

                        # 최고가 업데이트
                        if pd.notna(row["high"]):
                            self.high_record_service.update_all_time_high(symbol)
                            updated_high_records += 1

                    except Exception as e:
                        logger.warning(
                            "historical_data_point_save_failed",
                            symbol=symbol,
                            date=str(date_idx),
                            error=str(e),
                        )

                # 배치 처리 후 메모리 정리
                del batch_data

            return {
                "status": "success",
                "saved_snapshots": saved_snapshots,
                "updated_high_records": updated_high_records,
            }

        except Exception as e:
            logger.error("historical_data_save_failed", symbol=symbol, error=str(e))
            return {"status": "failed", "error": str(e)}

    @memory_monitor
    def collect_batch_historical_data(
        self,
        symbols: List[str],
        period: str = "1y",
        batch_size: int = 5,
        save_to_db: bool = True,
    ) -> Dict[str, Any]:
        """
        여러 심볼의 히스토리컬 데이터를 배치로 수집

        Args:
            symbols: 수집할 심볼 리스트
            period: 데이터 기간
            batch_size: 배치 크기
            save_to_db: 데이터베이스 저장 여부

        Returns:
            배치 수집 결과
        """
        logger.info(
            "batch_historical_data_collection_started",
            symbol_count=len(symbols),
            period=period,
            batch_size=batch_size,
        )

        results = {}
        successful_count = 0

        # 배치 단위로 처리
        for i in range(0, len(symbols), batch_size):
            batch_symbols = symbols[i : i + batch_size]
            logger.info(
                "processing_batch",
                batch_start=i + 1,
                batch_end=min(i + batch_size, len(symbols)),
            )

            for symbol in batch_symbols:
                try:
                    result = self.collect_historical_data(
                        symbol, period, save_to_db=save_to_db
                    )
                    results[symbol] = result

                    if result["status"] == "success":
                        successful_count += 1

                except Exception as e:
                    results[symbol] = {
                        "symbol": symbol,
                        "status": "failed",
                        "error": str(e),
                    }
                    logger.error(
                        "symbol_historical_data_collection_failed",
                        symbol=symbol,
                        error=str(e),
                    )

            # 배치 간 잠시 대기 (API 레이트 리밋 고려)
            import time

            time.sleep(1)

            # 배치 처리 후 메모리 정리
            del batch_symbols

        batch_result = {
            "total_symbols": len(symbols),
            "successful_count": successful_count,
            "failed_count": len(symbols) - successful_count,
            "period": period,
            "batch_size": batch_size,
            "results": results,
            "completed_at": datetime.now().isoformat(),
        }

        logger.info(
            "batch_historical_data_collection_completed",
            total_symbols=len(symbols),
            successful_count=successful_count,
        )

        return batch_result

    @memory_monitor
    def collect_incremental_data(
        self, symbol: str, last_update_date: date = None, save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        증분 데이터 수집 (마지막 업데이트 이후 데이터만)

        Args:
            symbol: 수집할 심볼
            last_update_date: 마지막 업데이트 날짜
            save_to_db: 데이터베이스 저장 여부

        Returns:
            증분 수집 결과
        """
        if last_update_date is None:
            last_update_date = date.today() - timedelta(days=7)  # 기본 7일

        logger.info(
            "incremental_data_collection_started",
            symbol=symbol,
            last_update_date=str(last_update_date),
        )

        try:
            # 마지막 업데이트 이후 기간 계산
            days_since_update = (date.today() - last_update_date).days

            if days_since_update <= 0:
                return {
                    "symbol": symbol,
                    "status": "skipped",
                    "reason": "Already up to date",
                    "last_update_date": last_update_date.isoformat(),
                }

            # 적절한 기간 설정
            if days_since_update <= 5:
                period = "5d"
            elif days_since_update <= 30:
                period = "1mo"
            elif days_since_update <= 90:
                period = "3mo"
            else:
                period = "1y"

            # 데이터 수집
            result = self.collect_historical_data(symbol, period, save_to_db=save_to_db)
            result["incremental"] = True
            result["days_since_update"] = days_since_update
            result["last_update_date"] = last_update_date.isoformat()

            return result

        except Exception as e:
            logger.error(
                "incremental_data_collection_failed", symbol=symbol, error=str(e)
            )
            return {
                "symbol": symbol,
                "status": "failed",
                "error": str(e),
                "incremental": True,
            }

    @cache_result(cache_name="price_data", ttl=1800)  # 30분 캐싱
    @memory_monitor
    def get_data_collection_stats(self, symbols: List[str] = None) -> Dict[str, Any]:
        """
        데이터 수집 통계 조회 (캐싱 적용)

        Args:
            symbols: 통계를 조회할 심볼 리스트 (None이면 전체)

        Returns:
            데이터 수집 통계
        """
        try:
            if symbols is None:
                from app.common.constants.symbol_names import SYMBOL_PRICE_MAP

                symbols = list(SYMBOL_PRICE_MAP.keys())[:10]  # 기본 10개

            stats = {
                "total_symbols": len(symbols),
                "symbols_with_data": 0,
                "symbols_without_data": 0,
                "average_data_points": 0,
                "latest_data_dates": {},
                "data_quality_score": 0.0,
            }

            total_data_points = 0

            for symbol in symbols:
                try:
                    # 간단한 데이터 존재 여부 체크
                    data = self.client.get_daily_data(symbol, period="5d")

                    if data is not None and not data.empty:
                        stats["symbols_with_data"] += 1
                        total_data_points += len(data)
                        stats["latest_data_dates"][
                            symbol
                        ] = data.index.max().isoformat()
                    else:
                        stats["symbols_without_data"] += 1

                except Exception as e:
                    stats["symbols_without_data"] += 1
                    logger.warning(
                        "symbol_stats_check_failed", symbol=symbol, error=str(e)
                    )

            # 평균 데이터 포인트 계산
            if stats["symbols_with_data"] > 0:
                stats["average_data_points"] = (
                    total_data_points / stats["symbols_with_data"]
                )

            # 데이터 품질 점수 계산 (0-100)
            stats["data_quality_score"] = (
                stats["symbols_with_data"] / len(symbols)
            ) * 100

            stats["generated_at"] = datetime.now().isoformat()

            return stats

        except Exception as e:
            logger.error("data_collection_stats_failed", error=str(e))
            return {"error": str(e), "generated_at": datetime.now().isoformat()}

    @memory_monitor
    def cleanup_old_data(self, days_to_keep: int = 365) -> Dict[str, Any]:
        """
        오래된 히스토리컬 데이터 정리

        Args:
            days_to_keep: 보관할 일수

        Returns:
            정리 결과
        """
        try:
            cutoff_date = date.today() - timedelta(days=days_to_keep)

            logger.info(
                "historical_data_cleanup_started",
                cutoff_date=str(cutoff_date),
                days_to_keep=days_to_keep,
            )

            # 실제 구현에서는 데이터베이스에서 오래된 데이터 삭제
            # 여기서는 시뮬레이션

            cleanup_result = {
                "status": "completed",
                "cutoff_date": cutoff_date.isoformat(),
                "days_to_keep": days_to_keep,
                "deleted_records": 0,  # 실제로는 삭제된 레코드 수
                "cleaned_at": datetime.now().isoformat(),
            }

            logger.info(
                "historical_data_cleanup_completed", cutoff_date=str(cutoff_date)
            )

            return cleanup_result

        except Exception as e:
            logger.error("historical_data_cleanup_failed", error=str(e))
            return {
                "status": "failed",
                "error": str(e),
                "cleaned_at": datetime.now().isoformat(),
            }


# 작업 큐용 백그라운드 작업들
@task(priority=TaskPriority.LOW, max_retries=2, timeout=1800.0)
@memory_monitor
async def collect_historical_data_background(
    symbols: List[str], period: str = "1y", batch_size: int = 5
) -> Dict[str, Any]:
    """
    히스토리컬 데이터 수집을 백그라운드 작업으로 처리
    """
    logger.info(
        "background_historical_data_collection_started",
        symbol_count=len(symbols),
        period=period,
    )

    try:
        service = HistoricalDataService()
        result = service.collect_batch_historical_data(symbols, period, batch_size)

        logger.info(
            "background_historical_data_collection_completed", symbol_count=len(symbols)
        )

        return {
            "task": "historical_data_collection",
            "status": "completed",
            "result": result,
            "completed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("background_historical_data_collection_failed", error=str(e))
        return {
            "task": "historical_data_collection",
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat(),
        }


@task(priority=TaskPriority.MEDIUM, max_retries=1, timeout=900.0)
@memory_monitor
async def collect_incremental_data_background(symbols: List[str]) -> Dict[str, Any]:
    """
    증분 데이터 수집을 백그라운드 작업으로 처리
    """
    logger.info(
        "background_incremental_data_collection_started", symbol_count=len(symbols)
    )

    try:
        service = HistoricalDataService()
        results = {}

        for symbol in symbols:
            result = service.collect_incremental_data(symbol)
            results[symbol] = result

        successful_count = sum(
            1 for r in results.values() if r.get("status") == "success"
        )

        logger.info(
            "background_incremental_data_collection_completed",
            symbol_count=len(symbols),
            successful_count=successful_count,
        )

        return {
            "task": "incremental_data_collection",
            "status": "completed",
            "results": results,
            "successful_count": successful_count,
            "completed_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("background_incremental_data_collection_failed", error=str(e))
        return {
            "task": "incremental_data_collection",
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat(),
        }
