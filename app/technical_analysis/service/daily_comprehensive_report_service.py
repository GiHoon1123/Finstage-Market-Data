"""
일일 종합 리포트 생성 서비스

기술적 분석, 가격 데이터, 뉴스 등을 종합한 일일 리포트를 생성합니다.
작업 큐를 통해 백그라운드에서 처리되도록 최적화되었습니다.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
import pandas as pd

from app.technical_analysis.service.technical_indicator_service import (
    TechnicalIndicatorService,
)
from app.technical_analysis.service.signal_generator_service import (
    SignalGeneratorService,
)
from app.technical_analysis.service.pattern_analysis_service import (
    PatternAnalysisService,
)
from app.market_price.service.price_monitor_service import PriceMonitorService
from app.market_price.service.price_snapshot_service import PriceSnapshotService
from app.market_price.service.price_high_record_service import PriceHighRecordService
from app.news_crawler.service.investing_news_crawler import InvestingNewsCrawler
from app.news_crawler.service.yahoo_news_crawler import YahooNewsCrawler
from app.common.utils.logging_config import get_logger
from app.common.utils.memory_optimizer import memory_monitor, optimize_dataframe_memory
from app.common.utils.memory_cache import cache_result

logger = get_logger(__name__)


class DailyComprehensiveReportService:
    """일일 종합 리포트 생성 서비스"""

    def __init__(self):
        # 서비스 인스턴스들
        self.technical_service = TechnicalIndicatorService()
        self.signal_service = SignalGeneratorService()
        self.pattern_service = PatternAnalysisService()
        self.price_monitor_service = PriceMonitorService()
        self.snapshot_service = PriceSnapshotService()
        self.high_record_service = PriceHighRecordService()

    @memory_monitor
    def generate_comprehensive_report(
        self, symbol: str, report_date: date = None
    ) -> Dict[str, Any]:
        """
        특정 심볼의 종합 리포트 생성

        Args:
            symbol: 분석할 심볼
            report_date: 리포트 날짜 (None이면 오늘)

        Returns:
            종합 리포트 데이터
        """
        if report_date is None:
            report_date = date.today()

        logger.info(
            "comprehensive_report_generation_started",
            symbol=symbol,
            date=str(report_date),
        )

        try:
            report = {
                "symbol": symbol,
                "report_date": report_date.isoformat(),
                "generated_at": datetime.now().isoformat(),
                "sections": {},
            }

            # 1. 가격 데이터 섹션
            report["sections"]["price_data"] = self._generate_price_section(symbol)

            # 2. 기술적 분석 섹션
            report["sections"]["technical_analysis"] = self._generate_technical_section(
                symbol
            )

            # 3. 신호 분석 섹션
            report["sections"]["signals"] = self._generate_signals_section(
                symbol, report_date
            )

            # 4. 패턴 분석 섹션
            report["sections"]["patterns"] = self._generate_patterns_section(symbol)

            # 5. 뉴스 섹션
            report["sections"]["news"] = self._generate_news_section(symbol)

            # 6. 종합 요약 섹션
            report["sections"]["summary"] = self._generate_summary_section(
                report["sections"]
            )

            logger.info("comprehensive_report_generation_completed", symbol=symbol)
            return report

        except Exception as e:
            logger.error(
                "comprehensive_report_generation_failed", symbol=symbol, error=str(e)
            )
            return {
                "symbol": symbol,
                "report_date": report_date.isoformat(),
                "error": str(e),
                "generated_at": datetime.now().isoformat(),
            }

    @memory_monitor
    def _generate_price_section(self, symbol: str) -> Dict[str, Any]:
        """가격 데이터 섹션 생성"""
        try:
            # 현재 가격 정보
            price_summary = self.price_monitor_service.get_price_summary(symbol)

            # 스냅샷 정보
            snapshot_summary = self.snapshot_service.get_snapshot_summary(symbol)

            # 최고가 기록 정보
            high_record_summary = self.high_record_service.get_high_record_summary(
                symbol
            )

            return {
                "current_price": price_summary,
                "snapshot": snapshot_summary,
                "high_record": high_record_summary,
                "status": "success",
            }

        except Exception as e:
            logger.error("price_section_generation_failed", symbol=symbol, error=str(e))
            return {"status": "error", "error": str(e)}

    @memory_monitor
    def _generate_technical_section(self, symbol: str) -> Dict[str, Any]:
        """기술적 분석 섹션 생성"""
        try:
            # 주요 기술적 지표들
            indicators = self.technical_service.get_all_indicators(symbol)

            # 지표별 신호 해석
            interpretations = {}

            if "rsi" in indicators:
                rsi_value = indicators["rsi"].get("current")
                if rsi_value:
                    if rsi_value > 70:
                        interpretations["rsi"] = {
                            "signal": "overbought",
                            "strength": "strong",
                        }
                    elif rsi_value < 30:
                        interpretations["rsi"] = {
                            "signal": "oversold",
                            "strength": "strong",
                        }
                    else:
                        interpretations["rsi"] = {
                            "signal": "neutral",
                            "strength": "weak",
                        }

            if "macd" in indicators:
                macd_data = indicators["macd"]
                if macd_data and "histogram" in macd_data:
                    histogram = macd_data["histogram"]
                    if histogram > 0:
                        interpretations["macd"] = {
                            "signal": "bullish",
                            "strength": "medium",
                        }
                    else:
                        interpretations["macd"] = {
                            "signal": "bearish",
                            "strength": "medium",
                        }

            return {
                "indicators": indicators,
                "interpretations": interpretations,
                "status": "success",
            }

        except Exception as e:
            logger.error(
                "technical_section_generation_failed", symbol=symbol, error=str(e)
            )
            return {"status": "error", "error": str(e)}

    @memory_monitor
    def _generate_signals_section(
        self, symbol: str, report_date: date
    ) -> Dict[str, Any]:
        """신호 분석 섹션 생성"""
        try:
            # 최근 30일간의 신호 생성
            end_date = report_date
            start_date = end_date - timedelta(days=30)

            signals_result = self.signal_service.generate_symbol_signals(
                symbol, start_date, end_date
            )

            # 신호 요약
            signal_summary = {
                "total_signals": signals_result.get("total_signals", 0),
                "saved_signals": signals_result.get("saved_signals", 0),
                "signal_breakdown": signals_result.get("signal_breakdown", {}),
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
            }

            return {
                "summary": signal_summary,
                "details": signals_result,
                "status": "success",
            }

        except Exception as e:
            logger.error(
                "signals_section_generation_failed", symbol=symbol, error=str(e)
            )
            return {"status": "error", "error": str(e)}

    @memory_monitor
    def _generate_patterns_section(self, symbol: str) -> Dict[str, Any]:
        """패턴 분석 섹션 생성"""
        try:
            # 패턴 발견
            pattern_discovery = self.pattern_service.discover_patterns(symbol, "1day")

            # 성공적인 패턴 조회
            successful_patterns = self.pattern_service.find_successful_patterns(
                symbol=symbol, success_threshold=0.6, min_occurrences=2
            )

            # 패턴 요약 정보
            pattern_summary = self.pattern_service.get_pattern_summary(symbol)

            return {
                "discovery": pattern_discovery,
                "successful_patterns": successful_patterns,
                "summary": pattern_summary,
                "status": "success",
            }

        except Exception as e:
            logger.error(
                "patterns_section_generation_failed", symbol=symbol, error=str(e)
            )
            return {"status": "error", "error": str(e)}

    @memory_monitor
    def _generate_news_section(self, symbol: str) -> Dict[str, Any]:
        """뉴스 섹션 생성"""
        try:
            news_data = {}

            # Investing.com 뉴스
            try:
                investing_crawler = InvestingNewsCrawler(symbol)
                investing_summary = investing_crawler.get_cached_news_summary(symbol)
                news_data["investing"] = investing_summary
            except Exception as e:
                news_data["investing"] = {"error": str(e)}

            # Yahoo 뉴스
            try:
                yahoo_crawler = YahooNewsCrawler(symbol)
                yahoo_summary = yahoo_crawler.get_cached_news_summary(symbol)
                news_data["yahoo"] = yahoo_summary
            except Exception as e:
                news_data["yahoo"] = {"error": str(e)}

            # 뉴스 요약
            total_news = 0
            for source_data in news_data.values():
                if isinstance(source_data, dict) and "total_news" in source_data:
                    total_news += source_data["total_news"]

            return {"sources": news_data, "total_news": total_news, "status": "success"}

        except Exception as e:
            logger.error("news_section_generation_failed", symbol=symbol, error=str(e))
            return {"status": "error", "error": str(e)}

    @memory_monitor
    def _generate_summary_section(self, sections: Dict[str, Any]) -> Dict[str, Any]:
        """종합 요약 섹션 생성"""
        try:
            summary = {
                "overall_sentiment": "neutral",
                "key_insights": [],
                "recommendations": [],
                "risk_factors": [],
                "data_quality": {},
            }

            # 기술적 분석 기반 sentiment 결정
            technical_section = sections.get("technical_analysis", {})
            interpretations = technical_section.get("interpretations", {})

            bullish_signals = 0
            bearish_signals = 0

            for indicator, interp in interpretations.items():
                signal = interp.get("signal", "neutral")
                if signal in ["bullish", "overbought"]:
                    bullish_signals += 1
                elif signal in ["bearish", "oversold"]:
                    bearish_signals += 1

            if bullish_signals > bearish_signals:
                summary["overall_sentiment"] = "bullish"
            elif bearish_signals > bullish_signals:
                summary["overall_sentiment"] = "bearish"

            # 주요 인사이트 생성
            if "rsi" in interpretations:
                rsi_signal = interpretations["rsi"]["signal"]
                if rsi_signal == "overbought":
                    summary["key_insights"].append(
                        "RSI 지표가 과매수 구간에 있어 단기 조정 가능성"
                    )
                elif rsi_signal == "oversold":
                    summary["key_insights"].append(
                        "RSI 지표가 과매도 구간에 있어 반등 가능성"
                    )

            # 신호 분석 기반 인사이트
            signals_section = sections.get("signals", {})
            signal_summary = signals_section.get("summary", {})
            total_signals = signal_summary.get("total_signals", 0)

            if total_signals > 10:
                summary["key_insights"].append(
                    f"최근 30일간 {total_signals}개의 기술적 신호 발생"
                )

            # 뉴스 기반 인사이트
            news_section = sections.get("news", {})
            total_news = news_section.get("total_news", 0)

            if total_news > 5:
                summary["key_insights"].append(f"최근 {total_news}개의 관련 뉴스 발생")

            # 데이터 품질 평가
            for section_name, section_data in sections.items():
                if isinstance(section_data, dict):
                    if section_data.get("status") == "success":
                        summary["data_quality"][section_name] = "good"
                    else:
                        summary["data_quality"][section_name] = "poor"

            return summary

        except Exception as e:
            logger.error("summary_section_generation_failed", error=str(e))
            return {"status": "error", "error": str(e)}

    @memory_monitor
    def generate_batch_reports(
        self, symbols: List[str], report_date: date = None
    ) -> Dict[str, Any]:
        """
        여러 심볼의 종합 리포트를 배치로 생성

        Args:
            symbols: 분석할 심볼 리스트
            report_date: 리포트 날짜

        Returns:
            배치 리포트 결과
        """
        if report_date is None:
            report_date = date.today()

        logger.info(
            "batch_comprehensive_reports_generation_started",
            symbol_count=len(symbols),
            date=str(report_date),
        )

        results = {}
        successful_count = 0

        for symbol in symbols:
            try:
                report = self.generate_comprehensive_report(symbol, report_date)
                results[symbol] = report

                if "error" not in report:
                    successful_count += 1

                logger.info("symbol_comprehensive_report_completed", symbol=symbol)

            except Exception as e:
                results[symbol] = {
                    "symbol": symbol,
                    "error": str(e),
                    "generated_at": datetime.now().isoformat(),
                }
                logger.error(
                    "symbol_comprehensive_report_failed", symbol=symbol, error=str(e)
                )

        batch_result = {
            "report_date": report_date.isoformat(),
            "total_symbols": len(symbols),
            "successful_count": successful_count,
            "failed_count": len(symbols) - successful_count,
            "reports": results,
            "generated_at": datetime.now().isoformat(),
        }

        logger.info(
            "batch_comprehensive_reports_generation_completed",
            total_symbols=len(symbols),
            successful_count=successful_count,
        )

        return batch_result

    @cache_result(cache_name="technical_analysis", ttl=3600)  # 1시간 캐싱
    @memory_monitor
    def get_report_template(self) -> Dict[str, Any]:
        """
        리포트 템플릿 조회 (캐싱 적용)

        Returns:
            리포트 템플릿 구조
        """
        return {
            "sections": {
                "price_data": {
                    "description": "현재 가격, 스냅샷, 최고가 기록 정보",
                    "fields": ["current_price", "snapshot", "high_record"],
                },
                "technical_analysis": {
                    "description": "기술적 지표 및 해석",
                    "fields": ["indicators", "interpretations"],
                },
                "signals": {
                    "description": "최근 30일간 기술적 신호 분석",
                    "fields": ["summary", "details"],
                },
                "patterns": {
                    "description": "패턴 발견 및 성공률 분석",
                    "fields": ["discovery", "successful_patterns", "summary"],
                },
                "news": {
                    "description": "관련 뉴스 요약",
                    "fields": ["sources", "total_news"],
                },
                "summary": {
                    "description": "종합 요약 및 추천",
                    "fields": ["overall_sentiment", "key_insights", "recommendations"],
                },
            },
            "metadata": {"version": "1.0", "last_updated": datetime.now().isoformat()},
        }
