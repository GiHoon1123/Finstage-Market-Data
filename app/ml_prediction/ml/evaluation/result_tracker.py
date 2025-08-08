"""
예측 결과 추적 시스템

이 모듈은 ML 예측 결과를 추적하고 실제 결과와 비교하는 기능을 제공합니다.
예측 정확도 모니터링과 성능 분석을 위한 핵심 컴포넌트입니다.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, date, timedelta
import asyncio
import logging
from dataclasses import dataclass

from app.ml_prediction.infra.model.repository.ml_prediction_repository import (
    MLPredictionRepository,
)
from app.ml_prediction.infra.model.entity.ml_prediction import MLPrediction
from app.ml_prediction.common.exceptions import (
    MLPredictionError,
    DataNotFoundError,
    ValidationError,
)
from app.common.infra.database.config.database_config import SessionLocal
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class PredictionAccuracy:
    """예측 정확도 정보"""

    timeframe: str
    total_predictions: int
    correct_predictions: int
    accuracy_rate: float
    avg_price_error: float
    avg_direction_accuracy: float


@dataclass
class ResultUpdateSummary:
    """결과 업데이트 요약"""

    updated_count: int
    failed_count: int
    total_processed: int
    accuracy_improvements: Dict[str, float]


class PredictionResultTracker:
    """
    예측 결과 추적 클래스

    ML 예측 결과를 실제 시장 데이터와 비교하여 정확도를 추적하고
    모델 성능을 모니터링하는 기능을 제공합니다.
    """

    def __init__(self):
        """초기화"""
        self.logger = logger

    async def update_prediction_results(
        self,
        target_date: date,
        symbols: Optional[List[str]] = None,
        batch_size: int = 100,
    ) -> ResultUpdateSummary:
        """
        예측 결과 업데이트

        지정된 날짜의 예측들에 대해 실제 결과를 업데이트합니다.

        Args:
            target_date: 업데이트할 예측의 목표 날짜
            symbols: 업데이트할 심볼 목록 (None이면 전체)
            batch_size: 배치 처리 크기

        Returns:
            ResultUpdateSummary: 업데이트 결과 요약
        """
        session = SessionLocal()
        try:
            self.logger.info(
                "prediction_result_update_started",
                target_date=target_date.isoformat(),
                symbols=symbols,
                batch_size=batch_size,
            )

            # 업데이트할 예측들 조회
            predictions = await self._get_predictions_for_update(
                target_date, symbols, session
            )

            if not predictions:
                self.logger.info(
                    "no_predictions_to_update", target_date=target_date.isoformat()
                )
                return ResultUpdateSummary(
                    updated_count=0,
                    failed_count=0,
                    total_processed=0,
                    accuracy_improvements={},
                )

            # 배치별로 처리
            updated_count = 0
            failed_count = 0
            accuracy_improvements = {}

            for i in range(0, len(predictions), batch_size):
                batch = predictions[i : i + batch_size]
                batch_results = await self._process_prediction_batch(batch)

                updated_count += batch_results["updated"]
                failed_count += batch_results["failed"]
                accuracy_improvements.update(batch_results["accuracy_improvements"])

                # 배치 간 잠시 대기 (시스템 부하 방지)
                if i + batch_size < len(predictions):
                    await asyncio.sleep(0.1)

            summary = ResultUpdateSummary(
                updated_count=updated_count,
                failed_count=failed_count,
                total_processed=len(predictions),
                accuracy_improvements=accuracy_improvements,
            )

            self.logger.info(
                "prediction_result_update_completed",
                target_date=target_date.isoformat(),
                summary=summary.__dict__,
            )

            return summary

        except Exception as e:
            self.logger.error(
                "prediction_result_update_failed",
                target_date=target_date.isoformat(),
                error=str(e),
            )
            raise MLPredictionError(f"예측 결과 업데이트 실패: {str(e)}")
        finally:
            session.close()

    async def get_prediction_accuracy(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        timeframes: Optional[List[str]] = None,
    ) -> List[PredictionAccuracy]:
        """
        예측 정확도 조회

        지정된 조건에 따른 예측 정확도를 계산하여 반환합니다.

        Args:
            symbol: 주식 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜
            timeframes: 타임프레임 목록

        Returns:
            List[PredictionAccuracy]: 타임프레임별 정확도 정보
        """
        session = SessionLocal()
        try:
            # 기본값 설정
            if end_date is None:
                end_date = date.today()
            if start_date is None:
                start_date = end_date - timedelta(days=30)
            if timeframes is None:
                timeframes = ["7d", "14d", "30d"]

            self.logger.info(
                "prediction_accuracy_calculation_started",
                symbol=symbol,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                timeframes=timeframes,
            )

            accuracies = []

            for timeframe in timeframes:
                accuracy = await self._calculate_timeframe_accuracy(
                    symbol, start_date, end_date, timeframe, session
                )
                accuracies.append(accuracy)

            self.logger.info(
                "prediction_accuracy_calculation_completed",
                symbol=symbol,
                accuracies=[acc.__dict__ for acc in accuracies],
            )

            return accuracies

        except Exception as e:
            self.logger.error(
                "prediction_accuracy_calculation_failed",
                symbol=symbol,
                error=str(e),
            )
            raise MLPredictionError(f"예측 정확도 계산 실패: {str(e)}")
        finally:
            session.close()

    async def get_recent_performance_summary(
        self, days: int = 30
    ) -> Dict[str, Dict[str, float]]:
        """
        최근 성능 요약

        최근 지정된 일수 동안의 전체적인 예측 성능을 요약합니다.

        Args:
            days: 조회할 일수

        Returns:
            Dict: 심볼별, 타임프레임별 성능 요약
        """
        session = SessionLocal()
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            self.logger.info(
                "performance_summary_calculation_started",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                days=days,
            )

            # 활성 심볼들 조회
            active_symbols = await self._get_active_symbols(
                start_date, end_date, session
            )

            performance_summary = {}

            for symbol in active_symbols:
                accuracies = await self.get_prediction_accuracy(
                    symbol, start_date, end_date
                )

                performance_summary[symbol] = {
                    acc.timeframe: {
                        "accuracy_rate": acc.accuracy_rate,
                        "avg_price_error": acc.avg_price_error,
                        "avg_direction_accuracy": acc.avg_direction_accuracy,
                        "total_predictions": acc.total_predictions,
                    }
                    for acc in accuracies
                }

            self.logger.info(
                "performance_summary_calculation_completed",
                days=days,
                symbols_count=len(active_symbols),
            )

            return performance_summary

        except Exception as e:
            self.logger.error(
                "performance_summary_calculation_failed", days=days, error=str(e)
            )
            raise MLPredictionError(f"성능 요약 계산 실패: {str(e)}")
        finally:
            session.close()

    async def _get_predictions_for_update(
        self, target_date: date, symbols: Optional[List[str]], session
    ) -> List[MLPrediction]:
        """업데이트할 예측들 조회"""
        try:
            repository = MLPredictionRepository(session)
            # 실제 구현에서는 repository를 통해 조회
            # 현재는 빈 리스트 반환 (데이터베이스 연결 후 구현)
            return []

        except Exception as e:
            self.logger.error(
                "get_predictions_for_update_failed",
                target_date=target_date.isoformat(),
                error=str(e),
            )
            return []

    async def _process_prediction_batch(
        self, predictions: List[MLPrediction]
    ) -> Dict[str, any]:
        """예측 배치 처리"""
        try:
            updated = 0
            failed = 0
            accuracy_improvements = {}

            for prediction in predictions:
                try:
                    # 실제 결과 조회 및 업데이트 로직
                    # 현재는 시뮬레이션
                    updated += 1

                except Exception as e:
                    self.logger.warning(
                        "prediction_update_failed",
                        prediction_id=(
                            prediction.id if hasattr(prediction, "id") else "unknown"
                        ),
                        error=str(e),
                    )
                    failed += 1

            return {
                "updated": updated,
                "failed": failed,
                "accuracy_improvements": accuracy_improvements,
            }

        except Exception as e:
            self.logger.error("process_prediction_batch_failed", error=str(e))
            return {
                "updated": 0,
                "failed": len(predictions),
                "accuracy_improvements": {},
            }

    async def _calculate_timeframe_accuracy(
        self, symbol: str, start_date: date, end_date: date, timeframe: str, session
    ) -> PredictionAccuracy:
        """타임프레임별 정확도 계산"""
        try:
            repository = MLPredictionRepository(session)
            # 실제 구현에서는 데이터베이스에서 예측과 실제 결과를 비교
            # 현재는 시뮬레이션 데이터 반환
            return PredictionAccuracy(
                timeframe=timeframe,
                total_predictions=100,
                correct_predictions=75,
                accuracy_rate=0.75,
                avg_price_error=2.5,
                avg_direction_accuracy=0.80,
            )

        except Exception as e:
            self.logger.error(
                "calculate_timeframe_accuracy_failed",
                symbol=symbol,
                timeframe=timeframe,
                error=str(e),
            )
            return PredictionAccuracy(
                timeframe=timeframe,
                total_predictions=0,
                correct_predictions=0,
                accuracy_rate=0.0,
                avg_price_error=0.0,
                avg_direction_accuracy=0.0,
            )

    async def _get_active_symbols(
        self, start_date: date, end_date: date, session
    ) -> List[str]:
        """활성 심볼들 조회"""
        try:
            repository = MLPredictionRepository(session)
            # 실제 구현에서는 데이터베이스에서 조회
            # 현재는 기본 심볼들 반환
            return ["^GSPC", "^IXIC"]

        except Exception as e:
            self.logger.error(
                "get_active_symbols_failed",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                error=str(e),
            )
            return []
