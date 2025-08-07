"""
전략분석 복구 서비스

10년치 나스닥/S&P500 데이터를 수집하고 모든 분석을 수행하여 테이블에 저장하는 서비스
"""

import asyncio
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.common.infra.database.config.database_config import SessionLocal
from app.common.infra.client.yahoo_price_client import YahooPriceClient
from app.common.utils.logging_config import get_logger

# 엔티티 imports
from app.technical_analysis.infra.model.entity.daily_prices import DailyPrice
from app.technical_analysis.infra.model.entity.technical_signals import TechnicalSignal
from app.technical_analysis.infra.model.entity.signal_patterns import SignalPattern
from app.technical_analysis.infra.model.entity.signal_outcomes import SignalOutcome
from app.technical_analysis.infra.model.entity.pattern_clusters import PatternCluster

# 리포지토리 imports
from app.technical_analysis.infra.model.repository.daily_price_repository import (
    DailyPriceRepository,
)
from app.technical_analysis.infra.model.repository.technical_signal_repository import (
    TechnicalSignalRepository,
)
from app.technical_analysis.infra.model.repository.signal_pattern_repository import (
    SignalPatternRepository,
)
from app.technical_analysis.infra.model.repository.signal_outcome_repository import (
    SignalOutcomeRepository,
)

# 서비스 imports
from app.technical_analysis.service.technical_indicator_service import (
    TechnicalIndicatorService,
)
from app.technical_analysis.service.signal_storage_service import SignalStorageService
from app.technical_analysis.service.pattern_analysis_service import (
    PatternAnalysisService,
)
from app.technical_analysis.service.outcome_tracking_service import (
    OutcomeTrackingService,
)
from app.technical_analysis.service.advanced_pattern_service import (
    AdvancedPatternService,
)

logger = get_logger(__name__)


class RecoveryService:
    """전략분석 복구 서비스"""

    def __init__(self):
        self.yahoo_client = YahooPriceClient()
        self.indicator_service = TechnicalIndicatorService()
        self.signal_storage_service = SignalStorageService()
        self.pattern_analysis_service = PatternAnalysisService()
        self.outcome_tracking_service = OutcomeTrackingService()
        self.advanced_pattern_service = AdvancedPatternService()

    def _get_session(self) -> Session:
        """데이터베이스 세션 생성"""
        return SessionLocal()

    # =================================================================
    # 1단계: 10년치 과거 데이터 수집
    # =================================================================

    async def recover_historical_data(
        self, symbols: List[str], years: int = 10, force_update: bool = False
    ) -> Dict[str, Any]:
        """
        10년치 과거 일봉 데이터를 수집하여 테이블에 저장

        Args:
            symbols: 수집할 심볼 리스트
            years: 수집할 연도 수
            force_update: 기존 데이터 강제 업데이트 여부

        Returns:
            수집 결과
        """
        logger.info("historical_data_recovery_started", symbols=symbols, years=years)

        session = self._get_session()
        repository = DailyPriceRepository(session)

        results = {}

        try:
            for symbol in symbols:
                logger.info("symbol_data_recovery_started", symbol=symbol)

                # 1. 기존 데이터 확인
                existing_count = repository.get_data_count_by_symbol(symbol)
                date_range = repository.get_date_range_by_symbol(symbol)

                logger.info(
                    "existing_data_check",
                    symbol=symbol,
                    existing_count=existing_count,
                    date_range=date_range,
                )

                if existing_count > 0 and not force_update:
                    # 누락된 날짜만 수집
                    end_date = datetime.now().date()
                    start_date = end_date - timedelta(days=years * 365)

                    missing_dates = repository.get_missing_dates(
                        symbol, start_date, end_date
                    )

                    if not missing_dates:
                        results[symbol] = {
                            "status": "skipped",
                            "message": "데이터가 이미 완전합니다",
                            "existing_count": existing_count,
                            "missing_count": 0,
                        }
                        continue

                    logger.info(
                        "missing_dates_found",
                        symbol=symbol,
                        missing_count=len(missing_dates),
                    )

                # 2. Yahoo Finance에서 데이터 수집
                logger.info("yahoo_data_fetch_started", symbol=symbol)

                # 최대 데이터 수집 (25년치)
                df = self.yahoo_client.get_daily_data(symbol, period="max")

                if df is None or df.empty:
                    results[symbol] = {
                        "status": "failed",
                        "message": "Yahoo Finance에서 데이터를 가져올 수 없습니다",
                        "error": "empty_data",
                    }
                    continue

                # 3. 지정된 연도만큼 필터링
                cutoff_date = datetime.now() - timedelta(days=years * 365)
                df = df[df.index >= cutoff_date]

                logger.info("data_filtered", symbol=symbol, filtered_count=len(df))

                # 4. 데이터베이스에 저장
                saved_count = 0
                duplicate_count = 0
                error_count = 0

                for idx, row in df.iterrows():
                    try:
                        # DailyPrice 엔티티 생성
                        daily_price = DailyPrice(
                            symbol=symbol,
                            date=idx.date(),
                            open_price=float(row["Open"]),
                            high_price=float(row["High"]),
                            low_price=float(row["Low"]),
                            close_price=float(row["Close"]),
                            volume=(
                                int(row["Volume"]) if pd.notna(row["Volume"]) else None
                            ),
                        )

                        # 전일 대비 변화 계산 (선택사항)
                        if saved_count > 0:
                            prev_close = float(
                                df.iloc[df.index.get_loc(idx) - 1]["Close"]
                            )
                            daily_price.price_change = (
                                daily_price.close_price - prev_close
                            )
                            daily_price.price_change_percent = (
                                daily_price.price_change / prev_close
                            ) * 100

                        # 저장
                        result = repository.save(daily_price)
                        if result:
                            saved_count += 1
                        else:
                            duplicate_count += 1

                    except Exception as e:
                        error_count += 1
                        logger.error(
                            "daily_price_save_failed",
                            symbol=symbol,
                            date=idx.date(),
                            error=str(e),
                        )

                results[symbol] = {
                    "status": "completed",
                    "message": f"{saved_count}개 데이터 저장 완료",
                    "saved_count": saved_count,
                    "duplicate_count": duplicate_count,
                    "error_count": error_count,
                    "total_processed": len(df),
                    "date_range": {
                        "start": df.index.min().date().isoformat(),
                        "end": df.index.max().date().isoformat(),
                    },
                }

                logger.info(
                    "symbol_data_recovery_completed",
                    symbol=symbol,
                    result=results[symbol],
                )

        except Exception as e:
            logger.error("historical_data_recovery_failed", error=str(e))
            raise
        finally:
            session.close()

        logger.info("historical_data_recovery_completed", results=results)
        return results

    async def recover_historical_data_background(
        self, symbols: List[str], years: int, force_update: bool
    ):
        """백그라운드에서 과거 데이터 복구 실행"""
        try:
            result = await self.recover_historical_data(symbols, years, force_update)
            logger.info("background_historical_data_recovery_completed", result=result)
        except Exception as e:
            logger.error("background_historical_data_recovery_failed", error=str(e))

    # =================================================================
    # 2단계: 기술적 분석 수행
    # =================================================================

    async def recover_technical_analysis(
        self, symbols: List[str], analysis_types: List[str], date_range_days: int = 365
    ) -> Dict[str, Any]:
        """
        저장된 일봉 데이터를 기반으로 모든 기술적 분석 수행

        Args:
            symbols: 분석할 심볼 리스트
            analysis_types: 수행할 분석 타입들
            date_range_days: 분석할 날짜 범위

        Returns:
            분석 결과
        """
        logger.info(
            "technical_analysis_recovery_started",
            symbols=symbols,
            analysis_types=analysis_types,
            date_range_days=date_range_days,
        )

        results = {}

        try:
            for symbol in symbols:
                symbol_results = {}

                # 1. 신호 분석
                if "signals" in analysis_types:
                    signal_result = await self._recover_technical_signals(
                        symbol, date_range_days
                    )
                    symbol_results["signals"] = signal_result

                # 2. 패턴 분석
                if "patterns" in analysis_types:
                    pattern_result = await self._recover_signal_patterns(
                        symbol, date_range_days
                    )
                    symbol_results["patterns"] = pattern_result

                # 3. 결과 추적
                if "outcomes" in analysis_types:
                    outcome_result = await self._recover_signal_outcomes(
                        symbol, date_range_days
                    )
                    symbol_results["outcomes"] = outcome_result

                # 4. 클러스터링
                if "clusters" in analysis_types:
                    cluster_result = await self._recover_pattern_clusters(symbol)
                    symbol_results["clusters"] = cluster_result

                results[symbol] = symbol_results

                logger.info(
                    "symbol_technical_analysis_completed",
                    symbol=symbol,
                    results=symbol_results,
                )

        except Exception as e:
            logger.error("technical_analysis_recovery_failed", error=str(e))
            raise

        logger.info("technical_analysis_recovery_completed", results=results)
        return results

    async def recover_technical_analysis_background(
        self, symbols: List[str], analysis_types: List[str], date_range_days: int
    ):
        """백그라운드에서 기술적 분석 복구 실행"""
        try:
            result = await self.recover_technical_analysis(
                symbols, analysis_types, date_range_days
            )
            logger.info(
                "background_technical_analysis_recovery_completed", result=result
            )
        except Exception as e:
            logger.error("background_technical_analysis_recovery_failed", error=str(e))

    # =================================================================
    # 개별 분석 메서드들
    # =================================================================

    async def _recover_technical_signals(
        self, symbol: str, days: int
    ) -> Dict[str, Any]:
        """기술적 신호 분석 복구"""
        logger.info("technical_signals_recovery_started", symbol=symbol, days=days)

        session = self._get_session()
        price_repository = DailyPriceRepository(session)

        try:
            # 지정된 기간의 일봉 데이터 조회
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)

            daily_prices = price_repository.find_by_symbol_and_date_range(
                symbol, start_date, end_date, order_desc=False
            )

            if not daily_prices:
                return {"status": "failed", "message": "일봉 데이터가 없습니다"}

            # DataFrame으로 변환
            df_data = []
            for price in daily_prices:
                df_data.append(
                    {
                        "date": price.date,
                        "open": float(price.open_price),
                        "high": float(price.high_price),
                        "low": float(price.low_price),
                        "close": float(price.close_price),
                        "volume": price.volume or 0,
                    }
                )

            df = pd.DataFrame(df_data)
            df.set_index("date", inplace=True)

            # 기술적 지표 계산 및 신호 생성
            signals_generated = 0

            # 이동평균 신호
            ma_signals = self._generate_moving_average_signals(df, symbol)
            signals_generated += len(ma_signals)

            # RSI 신호
            rsi_signals = self._generate_rsi_signals(df, symbol)
            signals_generated += len(rsi_signals)

            # 볼린저 밴드 신호
            bb_signals = self._generate_bollinger_signals(df, symbol)
            signals_generated += len(bb_signals)

            # 신호들을 데이터베이스에 저장
            all_signals = ma_signals + rsi_signals + bb_signals
            saved_count = self._save_technical_signals(all_signals, session)

            return {
                "status": "completed",
                "signals_generated": signals_generated,
                "signals_saved": saved_count,
                "data_points": len(df),
            }

        except Exception as e:
            logger.error(
                "technical_signals_recovery_failed", symbol=symbol, error=str(e)
            )
            return {"status": "failed", "error": str(e)}
        finally:
            session.close()

    async def _recover_signal_patterns(self, symbol: str, days: int) -> Dict[str, Any]:
        """신호 패턴 분석 복구"""
        logger.info("signal_patterns_recovery_started", symbol=symbol, days=days)

        try:
            # 패턴 분석 서비스 사용
            result = self.pattern_analysis_service.discover_patterns(symbol, "1day")

            return {
                "status": "completed",
                "patterns_discovered": result.get("discovered_patterns", 0),
                "patterns_saved": result.get("saved_patterns", 0),
            }

        except Exception as e:
            logger.error("signal_patterns_recovery_failed", symbol=symbol, error=str(e))
            return {"status": "failed", "error": str(e)}

    async def _recover_signal_outcomes(self, symbol: str, days: int) -> Dict[str, Any]:
        """신호 결과 추적 복구"""
        logger.info("signal_outcomes_recovery_started", symbol=symbol, days=days)

        session = self._get_session()
        signal_repository = TechnicalSignalRepository(session)

        try:
            # 지정된 기간의 신호들 조회
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            signals = signal_repository.find_by_date_range(
                start_date=start_date, end_date=end_date, symbol=symbol
            )

            # 각 신호에 대해 결과 추적 초기화
            outcomes_created = 0
            for signal in signals:
                outcome = self.outcome_tracking_service.initialize_outcome_tracking(
                    signal.id
                )
                if outcome:
                    outcomes_created += 1

            # 결과 업데이트 실행
            update_result = self.outcome_tracking_service.update_outcomes(hours_old=1)

            return {
                "status": "completed",
                "signals_processed": len(signals),
                "outcomes_created": outcomes_created,
                "outcomes_updated": update_result.get("updated_count", 0),
            }

        except Exception as e:
            logger.error("signal_outcomes_recovery_failed", symbol=symbol, error=str(e))
            return {"status": "failed", "error": str(e)}
        finally:
            session.close()

    async def _recover_pattern_clusters(self, symbol: str) -> Dict[str, Any]:
        """패턴 클러스터링 복구"""
        logger.info("pattern_clusters_recovery_started", symbol=symbol)

        try:
            # 고급 패턴 서비스 사용
            cluster_result = self.advanced_pattern_service.cluster_patterns(
                symbol=symbol, n_clusters=5, min_patterns=10
            )

            return {
                "status": "completed",
                "clusters_created": cluster_result.get("n_clusters", 0),
                "patterns_clustered": cluster_result.get("patterns_clustered", 0),
            }

        except Exception as e:
            logger.error(
                "pattern_clusters_recovery_failed", symbol=symbol, error=str(e)
            )
            return {"status": "failed", "error": str(e)}

    # =================================================================
    # 신호 생성 헬퍼 메서드들
    # =================================================================

    def _generate_moving_average_signals(
        self, df: pd.DataFrame, symbol: str
    ) -> List[TechnicalSignal]:
        """이동평균 신호 생성"""
        signals = []

        # 이동평균 계산
        df["MA20"] = df["close"].rolling(window=20).mean()
        df["MA50"] = df["close"].rolling(window=50).mean()
        df["MA200"] = df["close"].rolling(window=200).mean()

        for i in range(1, len(df)):
            current_date = df.index[i]
            current_price = df.iloc[i]["close"]
            prev_price = df.iloc[i - 1]["close"]

            # MA20 돌파 신호
            if (
                prev_price <= df.iloc[i - 1]["MA20"]
                and current_price > df.iloc[i]["MA20"]
            ):
                signals.append(
                    TechnicalSignal(
                        symbol=symbol,
                        signal_type="MA20_breakout_up",
                        timeframe="1day",
                        triggered_at=datetime.combine(
                            current_date, datetime.min.time()
                        ),
                        current_price=current_price,
                        indicator_value=df.iloc[i]["MA20"],
                        signal_strength=(
                            (current_price - df.iloc[i]["MA20"]) / df.iloc[i]["MA20"]
                        )
                        * 100,
                    )
                )

            # MA200 돌파 신호
            if (
                prev_price <= df.iloc[i - 1]["MA200"]
                and current_price > df.iloc[i]["MA200"]
            ):
                signals.append(
                    TechnicalSignal(
                        symbol=symbol,
                        signal_type="MA200_breakout_up",
                        timeframe="1day",
                        triggered_at=datetime.combine(
                            current_date, datetime.min.time()
                        ),
                        current_price=current_price,
                        indicator_value=df.iloc[i]["MA200"],
                        signal_strength=(
                            (current_price - df.iloc[i]["MA200"]) / df.iloc[i]["MA200"]
                        )
                        * 100,
                    )
                )

        return signals

    def _generate_rsi_signals(
        self, df: pd.DataFrame, symbol: str
    ) -> List[TechnicalSignal]:
        """RSI 신호 생성"""
        signals = []

        # RSI 계산
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["RSI"] = 100 - (100 / (1 + rs))

        for i in range(1, len(df)):
            current_date = df.index[i]
            current_price = df.iloc[i]["close"]
            current_rsi = df.iloc[i]["RSI"]
            prev_rsi = df.iloc[i - 1]["RSI"]

            # RSI 과매수 신호
            if prev_rsi <= 70 and current_rsi > 70:
                signals.append(
                    TechnicalSignal(
                        symbol=symbol,
                        signal_type="RSI_overbought",
                        timeframe="1day",
                        triggered_at=datetime.combine(
                            current_date, datetime.min.time()
                        ),
                        current_price=current_price,
                        indicator_value=current_rsi,
                        signal_strength=current_rsi - 70,
                    )
                )

            # RSI 과매도 신호
            if prev_rsi >= 30 and current_rsi < 30:
                signals.append(
                    TechnicalSignal(
                        symbol=symbol,
                        signal_type="RSI_oversold",
                        timeframe="1day",
                        triggered_at=datetime.combine(
                            current_date, datetime.min.time()
                        ),
                        current_price=current_price,
                        indicator_value=current_rsi,
                        signal_strength=30 - current_rsi,
                    )
                )

        return signals

    def _generate_bollinger_signals(
        self, df: pd.DataFrame, symbol: str
    ) -> List[TechnicalSignal]:
        """볼린저 밴드 신호 생성"""
        signals = []

        # 볼린저 밴드 계산
        df["BB_middle"] = df["close"].rolling(window=20).mean()
        bb_std = df["close"].rolling(window=20).std()
        df["BB_upper"] = df["BB_middle"] + (bb_std * 2)
        df["BB_lower"] = df["BB_middle"] - (bb_std * 2)

        for i in range(1, len(df)):
            current_date = df.index[i]
            current_price = df.iloc[i]["close"]
            prev_price = df.iloc[i - 1]["close"]

            # 상단 밴드 터치 신호
            if (
                prev_price < df.iloc[i - 1]["BB_upper"]
                and current_price >= df.iloc[i]["BB_upper"]
            ):
                signals.append(
                    TechnicalSignal(
                        symbol=symbol,
                        signal_type="BB_touch_upper",
                        timeframe="1day",
                        triggered_at=datetime.combine(
                            current_date, datetime.min.time()
                        ),
                        current_price=current_price,
                        indicator_value=df.iloc[i]["BB_upper"],
                        signal_strength=(
                            (current_price - df.iloc[i]["BB_upper"])
                            / df.iloc[i]["BB_upper"]
                        )
                        * 100,
                    )
                )

            # 하단 밴드 터치 신호
            if (
                prev_price > df.iloc[i - 1]["BB_lower"]
                and current_price <= df.iloc[i]["BB_lower"]
            ):
                signals.append(
                    TechnicalSignal(
                        symbol=symbol,
                        signal_type="BB_touch_lower",
                        timeframe="1day",
                        triggered_at=datetime.combine(
                            current_date, datetime.min.time()
                        ),
                        current_price=current_price,
                        indicator_value=df.iloc[i]["BB_lower"],
                        signal_strength=(
                            (df.iloc[i]["BB_lower"] - current_price)
                            / df.iloc[i]["BB_lower"]
                        )
                        * 100,
                    )
                )

        return signals

    def _save_technical_signals(
        self, signals: List[TechnicalSignal], session: Session
    ) -> int:
        """기술적 신호들을 데이터베이스에 저장"""
        saved_count = 0

        for signal in signals:
            try:
                session.add(signal)
                session.commit()
                saved_count += 1
            except Exception as e:
                session.rollback()
                logger.error(
                    "signal_save_failed", signal_type=signal.signal_type, error=str(e)
                )

        return saved_count

    # =================================================================
    # 전체 복구
    # =================================================================

    async def full_recovery_background(
        self, symbols: List[str], years: int, force_update: bool
    ):
        """백그라운드에서 전체 복구 실행"""
        try:
            logger.info("full_recovery_started", symbols=symbols, years=years)

            # 1단계: 과거 데이터 수집
            logger.info("full_recovery_phase_1_started", phase="historical_data")
            data_result = await self.recover_historical_data(
                symbols, years, force_update
            )
            logger.info("full_recovery_phase_1_completed", result=data_result)

            # 2단계: 기술적 분석 수행
            logger.info("full_recovery_phase_2_started", phase="technical_analysis")
            analysis_result = await self.recover_technical_analysis(
                symbols, ["signals", "patterns", "outcomes", "clusters"], years * 365
            )
            logger.info("full_recovery_phase_2_completed", result=analysis_result)

            logger.info(
                "full_recovery_completed",
                data_result=data_result,
                analysis_result=analysis_result,
            )

        except Exception as e:
            logger.error("full_recovery_failed", error=str(e))

    # =================================================================
    # 상태 확인 및 유틸리티
    # =================================================================

    async def get_recovery_status(self) -> Dict[str, Any]:
        """복구 작업 상태 확인"""
        session = self._get_session()

        try:
            # 각 테이블의 데이터 개수 조회
            daily_prices_count = session.query(DailyPrice).count()
            technical_signals_count = session.query(TechnicalSignal).count()
            signal_patterns_count = session.query(SignalPattern).count()
            signal_outcomes_count = session.query(SignalOutcome).count()
            pattern_clusters_count = session.query(PatternCluster).count()

            # 심볼별 데이터 개수
            symbol_counts = {}
            for symbol in ["^IXIC", "^GSPC"]:
                symbol_counts[symbol] = {
                    "daily_prices": session.query(DailyPrice)
                    .filter(DailyPrice.symbol == symbol)
                    .count(),
                    "technical_signals": session.query(TechnicalSignal)
                    .filter(TechnicalSignal.symbol == symbol)
                    .count(),
                    "signal_patterns": session.query(SignalPattern)
                    .filter(SignalPattern.symbol == symbol)
                    .count(),
                }

            return {
                "daily_prices_count": daily_prices_count,
                "technical_signals_count": technical_signals_count,
                "signal_patterns_count": signal_patterns_count,
                "signal_outcomes_count": signal_outcomes_count,
                "pattern_clusters_count": pattern_clusters_count,
                "symbol_breakdown": symbol_counts,
            }

        finally:
            session.close()

    async def get_data_summary(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """저장된 데이터 요약 정보"""
        session = self._get_session()

        try:
            summary = {}

            if symbol:
                # 특정 심볼 요약
                price_repo = DailyPriceRepository(session)
                date_range = price_repo.get_date_range_by_symbol(symbol)
                data_count = price_repo.get_data_count_by_symbol(symbol)

                summary[symbol] = {
                    "daily_prices_count": data_count,
                    "date_range": date_range,
                    "technical_signals_count": session.query(TechnicalSignal)
                    .filter(TechnicalSignal.symbol == symbol)
                    .count(),
                    "signal_patterns_count": session.query(SignalPattern)
                    .filter(SignalPattern.symbol == symbol)
                    .count(),
                }
            else:
                # 전체 요약
                for sym in ["^IXIC", "^GSPC"]:
                    price_repo = DailyPriceRepository(session)
                    date_range = price_repo.get_date_range_by_symbol(sym)
                    data_count = price_repo.get_data_count_by_symbol(sym)

                    summary[sym] = {
                        "daily_prices_count": data_count,
                        "date_range": date_range,
                        "technical_signals_count": session.query(TechnicalSignal)
                        .filter(TechnicalSignal.symbol == sym)
                        .count(),
                        "signal_patterns_count": session.query(SignalPattern)
                        .filter(SignalPattern.symbol == sym)
                        .count(),
                    }

            return summary

        finally:
            session.close()

    async def cleanup_test_data(self, data_types: List[str]) -> Dict[str, Any]:
        """테스트 데이터 정리"""
        session = self._get_session()

        try:
            cleanup_result = {}

            for data_type in data_types:
                if data_type == "test_signals":
                    # 테스트 신호 삭제 (signal_type에 'test'가 포함된 것들)
                    deleted = (
                        session.query(TechnicalSignal)
                        .filter(TechnicalSignal.signal_type.like("%test%"))
                        .delete(synchronize_session=False)
                    )
                    cleanup_result["test_signals"] = deleted

                elif data_type == "test_patterns":
                    # 테스트 패턴 삭제 (pattern_name에 'test'가 포함된 것들)
                    deleted = (
                        session.query(SignalPattern)
                        .filter(SignalPattern.pattern_name.like("%test%"))
                        .delete(synchronize_session=False)
                    )
                    cleanup_result["test_patterns"] = deleted

            session.commit()
            return cleanup_result

        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
