"""
복구 핸들러

라우터와 서비스 사이의 중간 계층으로, 복구 관련 비즈니스 로직을 처리합니다.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from app.technical_analysis.service.recovery_service import RecoveryService
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class RecoveryHandler:
    """복구 핸들러"""

    def __init__(self):
        self.recovery_service = RecoveryService()

    async def handle_historical_data_recovery(
        self, symbols: List[str], years: int, force_update: bool
    ) -> Dict[str, Any]:
        """
        10년치 과거 데이터 복구 처리

        Args:
            symbols: 복구할 심볼 리스트
            years: 복구할 연도 수
            force_update: 기존 데이터 강제 업데이트 여부

        Returns:
            복구 처리 결과
        """
        try:
            logger.info(
                "historical_data_recovery_handler_started",
                symbols=symbols,
                years=years,
                force_update=force_update,
            )

            # 입력 검증
            if not symbols:
                raise ValueError("심볼 리스트가 비어있습니다")

            if years < 1 or years > 25:
                raise ValueError("연도 수는 1~25년 사이여야 합니다")

            # 지원되는 심볼 체크
            supported_symbols = ["^IXIC", "^GSPC"]
            invalid_symbols = [s for s in symbols if s not in supported_symbols]
            if invalid_symbols:
                raise ValueError(
                    f"지원되지 않는 심볼: {invalid_symbols}. 지원 심볼: {supported_symbols}"
                )

            # 복구 서비스 호출
            result = await self.recovery_service.recover_historical_data(
                symbols, years, force_update
            )

            # 결과 가공
            total_saved = sum(
                r.get("saved_count", 0) for r in result.values() if isinstance(r, dict)
            )
            total_duplicates = sum(
                r.get("duplicate_count", 0)
                for r in result.values()
                if isinstance(r, dict)
            )
            total_errors = sum(
                r.get("error_count", 0) for r in result.values() if isinstance(r, dict)
            )

            processed_result = {
                "status": "completed",
                "summary": {
                    "total_symbols": len(symbols),
                    "successful_symbols": len(
                        [
                            r
                            for r in result.values()
                            if isinstance(r, dict) and r.get("status") == "completed"
                        ]
                    ),
                    "total_saved": total_saved,
                    "total_duplicates": total_duplicates,
                    "total_errors": total_errors,
                },
                "symbol_details": result,
                "processed_at": datetime.now().isoformat(),
            }

            logger.info(
                "historical_data_recovery_handler_completed", result=processed_result
            )
            return processed_result

        except ValueError as e:
            logger.error("historical_data_recovery_validation_failed", error=str(e))
            raise Exception(f"입력 검증 실패: {str(e)}")
        except Exception as e:
            logger.error("historical_data_recovery_handler_failed", error=str(e))
            raise Exception(f"과거 데이터 복구 처리 실패: {str(e)}")

    async def handle_technical_analysis_recovery(
        self, symbols: List[str], analysis_types: List[str], date_range_days: int
    ) -> Dict[str, Any]:
        """
        기술적 분석 복구 처리

        Args:
            symbols: 분석할 심볼 리스트
            analysis_types: 수행할 분석 타입들
            date_range_days: 분석할 날짜 범위

        Returns:
            분석 복구 처리 결과
        """
        try:
            logger.info(
                "technical_analysis_recovery_handler_started",
                symbols=symbols,
                analysis_types=analysis_types,
                date_range_days=date_range_days,
            )

            # 입력 검증
            if not symbols:
                raise ValueError("심볼 리스트가 비어있습니다")

            if not analysis_types:
                raise ValueError("분석 타입 리스트가 비어있습니다")

            valid_analysis_types = ["signals", "patterns", "outcomes", "clusters"]
            invalid_types = [t for t in analysis_types if t not in valid_analysis_types]
            if invalid_types:
                raise ValueError(
                    f"유효하지 않은 분석 타입: {invalid_types}. 사용 가능: {valid_analysis_types}"
                )

            if date_range_days < 30 or date_range_days > 3650:
                raise ValueError("날짜 범위는 30~3650일 사이여야 합니다")

            # 복구 서비스 호출
            result = await self.recovery_service.recover_technical_analysis(
                symbols, analysis_types, date_range_days
            )

            # 결과 가공
            processed_result = {
                "status": "completed",
                "summary": {
                    "total_symbols": len(symbols),
                    "analysis_types": analysis_types,
                    "date_range_days": date_range_days,
                    "successful_symbols": len(
                        [r for r in result.values() if isinstance(r, dict)]
                    ),
                },
                "symbol_details": result,
                "processed_at": datetime.now().isoformat(),
            }

            logger.info(
                "technical_analysis_recovery_handler_completed", result=processed_result
            )
            return processed_result

        except ValueError as e:
            logger.error("technical_analysis_recovery_validation_failed", error=str(e))
            raise Exception(f"입력 검증 실패: {str(e)}")
        except Exception as e:
            logger.error("technical_analysis_recovery_handler_failed", error=str(e))
            raise Exception(f"기술적 분석 복구 처리 실패: {str(e)}")

    async def handle_full_recovery(
        self, symbols: List[str], years: int, force_update: bool
    ) -> Dict[str, Any]:
        """
        전체 복구 처리 (데이터 수집 + 분석)

        Args:
            symbols: 복구할 심볼 리스트
            years: 복구할 연도 수
            force_update: 기존 데이터 강제 업데이트 여부

        Returns:
            전체 복구 처리 결과
        """
        try:
            logger.info(
                "full_recovery_handler_started",
                symbols=symbols,
                years=years,
                force_update=force_update,
            )

            # 입력 검증 (historical_data_recovery와 동일)
            if not symbols:
                raise ValueError("심볼 리스트가 비어있습니다")

            if years < 1 or years > 25:
                raise ValueError("연도 수는 1~25년 사이여야 합니다")

            supported_symbols = ["^IXIC", "^GSPC"]
            invalid_symbols = [s for s in symbols if s not in supported_symbols]
            if invalid_symbols:
                raise ValueError(
                    f"지원되지 않는 심볼: {invalid_symbols}. 지원 심볼: {supported_symbols}"
                )

            # 전체 복구는 백그라운드에서만 실행
            # 여기서는 시작 확인만 처리
            processed_result = {
                "status": "started",
                "message": "전체 복구 작업이 백그라운드에서 시작되었습니다",
                "phases": [
                    "1단계: 10년치 일봉 데이터 수집",
                    "2단계: 기술적 신호 분석",
                    "3단계: 신호 패턴 분석",
                    "4단계: 신호 결과 추적",
                    "5단계: 패턴 클러스터링",
                ],
                "symbols": symbols,
                "years": years,
                "force_update": force_update,
                "estimated_total_time": f"{len(symbols) * years * 5}분",
                "started_at": datetime.now().isoformat(),
            }

            logger.info(
                "full_recovery_handler_started_background", result=processed_result
            )
            return processed_result

        except ValueError as e:
            logger.error("full_recovery_validation_failed", error=str(e))
            raise Exception(f"입력 검증 실패: {str(e)}")
        except Exception as e:
            logger.error("full_recovery_handler_failed", error=str(e))
            raise Exception(f"전체 복구 처리 실패: {str(e)}")

    async def handle_recovery_status_check(self) -> Dict[str, Any]:
        """
        복구 작업 상태 확인 처리

        Returns:
            상태 확인 결과
        """
        try:
            logger.info("recovery_status_check_handler_started")

            # 복구 서비스에서 상태 조회
            status = await self.recovery_service.get_recovery_status()

            # 상태 정보 가공
            processed_status = {
                "timestamp": datetime.now().isoformat(),
                "database_status": "connected",
                "recovery_status": status,
                "database_info": {
                    "daily_prices_count": status.get("daily_prices_count", 0),
                    "technical_signals_count": status.get("technical_signals_count", 0),
                    "signal_patterns_count": status.get("signal_patterns_count", 0),
                    "signal_outcomes_count": status.get("signal_outcomes_count", 0),
                    "pattern_clusters_count": status.get("pattern_clusters_count", 0),
                },
                "symbol_breakdown": status.get("symbol_breakdown", {}),
            }

            logger.info(
                "recovery_status_check_handler_completed", status=processed_status
            )
            return processed_status

        except Exception as e:
            logger.error("recovery_status_check_handler_failed", error=str(e))
            raise Exception(f"상태 확인 처리 실패: {str(e)}")

    async def handle_data_summary_request(
        self, symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        데이터 요약 요청 처리

        Args:
            symbol: 특정 심볼 필터

        Returns:
            데이터 요약 결과
        """
        try:
            logger.info("data_summary_request_handler_started", symbol=symbol)

            # 심볼 검증 (제공된 경우)
            if symbol:
                supported_symbols = ["^IXIC", "^GSPC"]
                if symbol not in supported_symbols:
                    raise ValueError(
                        f"지원되지 않는 심볼: {symbol}. 지원 심볼: {supported_symbols}"
                    )

            # 복구 서비스에서 요약 조회
            summary = await self.recovery_service.get_data_summary(symbol)

            # 요약 정보 가공
            processed_summary = {
                "timestamp": datetime.now().isoformat(),
                "symbol_filter": symbol,
                "data_summary": summary,
                "total_symbols": len(summary) if isinstance(summary, dict) else 0,
            }

            # 전체 통계 계산 (심볼 필터가 없는 경우)
            if not symbol and isinstance(summary, dict):
                total_daily_prices = sum(
                    s.get("daily_prices_count", 0) for s in summary.values()
                )
                total_signals = sum(
                    s.get("technical_signals_count", 0) for s in summary.values()
                )
                total_patterns = sum(
                    s.get("signal_patterns_count", 0) for s in summary.values()
                )

                processed_summary["overall_statistics"] = {
                    "total_daily_prices": total_daily_prices,
                    "total_technical_signals": total_signals,
                    "total_signal_patterns": total_patterns,
                }

            logger.info(
                "data_summary_request_handler_completed", summary=processed_summary
            )
            return processed_summary

        except ValueError as e:
            logger.error("data_summary_validation_failed", error=str(e))
            raise Exception(f"입력 검증 실패: {str(e)}")
        except Exception as e:
            logger.error("data_summary_request_handler_failed", error=str(e))
            raise Exception(f"데이터 요약 요청 처리 실패: {str(e)}")

    async def handle_test_data_cleanup(
        self, data_types: List[str], confirm: bool
    ) -> Dict[str, Any]:
        """
        테스트 데이터 정리 처리

        Args:
            data_types: 정리할 데이터 타입들
            confirm: 정리 확인

        Returns:
            정리 처리 결과
        """
        try:
            logger.info(
                "test_data_cleanup_handler_started",
                data_types=data_types,
                confirm=confirm,
            )

            # 입력 검증
            if not confirm:
                raise ValueError(
                    "데이터 정리를 위해서는 confirm=true 파라미터가 필요합니다"
                )

            if not data_types:
                raise ValueError("정리할 데이터 타입을 지정해야 합니다")

            valid_data_types = ["test_signals", "test_patterns", "test_outcomes"]
            invalid_types = [t for t in data_types if t not in valid_data_types]
            if invalid_types:
                raise ValueError(
                    f"유효하지 않은 데이터 타입: {invalid_types}. 사용 가능: {valid_data_types}"
                )

            # 복구 서비스에서 정리 실행
            cleanup_result = await self.recovery_service.cleanup_test_data(data_types)

            # 결과 가공
            processed_result = {
                "status": "completed",
                "message": "테스트 데이터 정리가 완료되었습니다",
                "cleanup_result": cleanup_result,
                "data_types_cleaned": data_types,
                "total_deleted": (
                    sum(cleanup_result.values())
                    if isinstance(cleanup_result, dict)
                    else 0
                ),
                "cleaned_at": datetime.now().isoformat(),
            }

            logger.info("test_data_cleanup_handler_completed", result=processed_result)
            return processed_result

        except ValueError as e:
            logger.error("test_data_cleanup_validation_failed", error=str(e))
            raise Exception(f"입력 검증 실패: {str(e)}")
        except Exception as e:
            logger.error("test_data_cleanup_handler_failed", error=str(e))
            raise Exception(f"테스트 데이터 정리 처리 실패: {str(e)}")

    def handle_health_check(self) -> Dict[str, Any]:
        """
        복구 서비스 상태 확인 처리

        Returns:
            서비스 상태 정보
        """
        try:
            logger.info("recovery_health_check_handler_started")

            health_info = {
                "service": "Recovery Service",
                "status": "healthy",
                "handler_status": "operational",
                "features": [
                    "10년치 과거 데이터 수집",
                    "전체 기술적 분석 수행",
                    "신호 패턴 분석",
                    "결과 추적 및 백테스팅",
                    "패턴 클러스터링",
                    "데이터 요약 및 상태 확인",
                ],
                "supported_symbols": ["^IXIC", "^GSPC"],
                "supported_analysis_types": [
                    "signals",
                    "patterns",
                    "outcomes",
                    "clusters",
                ],
                "max_years": 25,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info("recovery_health_check_handler_completed", health=health_info)
            return health_info

        except Exception as e:
            logger.error("recovery_health_check_handler_failed", error=str(e))
            return {
                "service": "Recovery Service",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
