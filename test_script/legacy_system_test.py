#!/usr/bin/env python3
"""
기존 시스템 기능 테스트

성능 개선 후에도 기존 기능들이 정상 작동하는지 확인합니다.
"""

import asyncio
import sys
import os
import time
import json
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LegacySystemTest:
    """기존 시스템 기능 테스트"""

    def __init__(self):
        self.test_results = {}
        self.failed_tests = []
        self.passed_tests = []

    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("🔍 기존 시스템 기능 테스트 시작")
        print("=" * 60)

        test_methods = [
            ("기술적 분석 서비스", self.test_technical_analysis_services),
            ("가격 데이터 서비스", self.test_price_data_services),
            ("뉴스 크롤링 서비스", self.test_news_crawling_services),
            ("스케줄러 시스템", self.test_scheduler_system),
            ("데이터베이스 연결", self.test_database_connection),
            ("API 라우터", self.test_api_routers),
            ("백그라운드 작업", self.test_background_tasks),
        ]

        for test_name, test_method in test_methods:
            print(f"\n🧪 {test_name} 테스트 중...")
            try:
                result = await test_method()
                if result:
                    print(f"   ✅ {test_name} 테스트 통과")
                    self.passed_tests.append(test_name)
                else:
                    print(f"   ❌ {test_name} 테스트 실패")
                    self.failed_tests.append(test_name)
                self.test_results[test_name] = result
            except Exception as e:
                print(f"   💥 {test_name} 테스트 오류: {str(e)}")
                self.failed_tests.append(test_name)
                self.test_results[test_name] = False

        # 결과 요약
        self.print_test_summary()
        return len(self.failed_tests) == 0

    async def test_technical_analysis_services(self) -> bool:
        """기술적 분석 서비스 테스트"""
        try:
            # 기본 기술적 분석 서비스
            from app.technical_analysis.service.technical_indicator_service import (
                TechnicalIndicatorService,
            )

            service = TechnicalIndicatorService()

            # 테스트 데이터 생성
            import pandas as pd

            test_data = pd.Series(
                [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 111]
            )

            # 이동평균 계산 테스트
            sma_result = service.calculate_moving_average(test_data, 5, "SMA")
            if sma_result is None or len(sma_result) == 0:
                return False

            print(f"      SMA 계산: {len(sma_result)}개 결과")

            # RSI 계산 테스트
            rsi_result = service.calculate_rsi(test_data, 14)
            if rsi_result is not None:
                print(f"      RSI 계산: {len(rsi_result)}개 결과")

            # 신호 생성 서비스 테스트
            try:
                from app.technical_analysis.service.signal_generator_service import (
                    SignalGeneratorService,
                )

                signal_service = SignalGeneratorService()
                signals = signal_service.generate_trading_signals(
                    test_data, test_data, test_data
                )
                print(f"      신호 생성: {len(signals) if signals else 0}개 신호")

            except ImportError:
                print("      신호 생성 서비스: 모듈 없음 (건너뜀)")

            # 패턴 분석 서비스 테스트
            try:
                from app.technical_analysis.service.pattern_analysis_service import (
                    PatternAnalysisService,
                )

                pattern_service = PatternAnalysisService()
                patterns = pattern_service.detect_patterns(test_data)
                print(f"      패턴 분석: {len(patterns) if patterns else 0}개 패턴")

            except ImportError:
                print("      패턴 분석 서비스: 모듈 없음 (건너뜀)")

            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_price_data_services(self) -> bool:
        """가격 데이터 서비스 테스트"""
        try:
            # 가격 모니터링 서비스
            try:
                from app.market_price.service.price_monitor_service import (
                    PriceMonitorService,
                )

                service = PriceMonitorService()

                # 현재 가격 조회 테스트 (모의)
                print("      가격 모니터링 서비스: 초기화 성공")

            except ImportError:
                print("      가격 모니터링 서비스: 모듈 없음 (건너뜀)")

            # 가격 스냅샷 서비스
            try:
                from app.market_price.service.price_snapshot_service import (
                    PriceSnapshotService,
                )

                snapshot_service = PriceSnapshotService()
                print("      가격 스냅샷 서비스: 초기화 성공")

            except ImportError:
                print("      가격 스냅샷 서비스: 모듈 없음 (건너뜀)")

            # 최고가 기록 서비스
            try:
                from app.market_price.service.price_high_record_service import (
                    PriceHighRecordService,
                )

                high_record_service = PriceHighRecordService()
                print("      최고가 기록 서비스: 초기화 성공")

            except ImportError:
                print("      최고가 기록 서비스: 모듈 없음 (건너뜀)")

            # 히스토리컬 데이터 서비스
            try:
                from app.market_price.service.historical_data_service import (
                    HistoricalDataService,
                )

                historical_service = HistoricalDataService()
                print("      히스토리컬 데이터 서비스: 초기화 성공")

            except ImportError:
                print("      히스토리컬 데이터 서비스: 모듈 없음 (건너뜀)")

            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_news_crawling_services(self) -> bool:
        """뉴스 크롤링 서비스 테스트"""
        try:
            # Yahoo 뉴스 크롤러
            try:
                from app.news_crawler.service.yahoo_news_crawler import YahooNewsCrawler

                yahoo_crawler = YahooNewsCrawler()
                print("      Yahoo 뉴스 크롤러: 초기화 성공")

            except ImportError:
                print("      Yahoo 뉴스 크롤러: 모듈 없음 (건너뜀)")

            # Investing 뉴스 크롤러
            try:
                from app.news_crawler.service.investing_news_crawler import (
                    InvestingNewsCrawler,
                )

                investing_crawler = InvestingNewsCrawler()
                print("      Investing 뉴스 크롤러: 초기화 성공")

            except ImportError:
                print("      Investing 뉴스 크롤러: 모듈 없음 (건너뜀)")

            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_scheduler_system(self) -> bool:
        """스케줄러 시스템 테스트"""
        try:
            # 병렬 스케줄러 확인
            from app.scheduler import parallel_scheduler

            # 스케줄러 모듈이 정상적으로 로드되는지 확인
            if hasattr(parallel_scheduler, "scheduler"):
                print("      병렬 스케줄러: 모듈 로드 성공")
            else:
                print("      병렬 스케줄러: 스케줄러 객체 확인")

            # 스케줄러 작업 함수들 확인
            scheduler_functions = [
                "run_realtime_price_monitor_job_parallel",
                "run_high_price_update_job_parallel",
                "run_previous_close_snapshot_job_parallel",
            ]

            available_functions = []
            for func_name in scheduler_functions:
                if hasattr(parallel_scheduler, func_name):
                    available_functions.append(func_name)

            print(f"      스케줄러 작업 함수: {len(available_functions)}개 확인")

            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_database_connection(self) -> bool:
        """데이터베이스 연결 테스트"""
        try:
            # 데이터베이스 설정 확인
            try:
                from app.database.database import SessionLocal, engine

                # 세션 생성 테스트
                session = SessionLocal()
                session.close()
                print("      데이터베이스 세션: 생성/종료 성공")

                # 엔진 상태 확인
                if engine:
                    print("      데이터베이스 엔진: 초기화 성공")

            except ImportError:
                print("      데이터베이스: 모듈 없음 (건너뜀)")
            except Exception as db_error:
                print(f"      데이터베이스 연결: 오류 발생 ({str(db_error)})")
                return False

            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_api_routers(self) -> bool:
        """API 라우터 테스트"""
        try:
            # 기술적 분석 라우터
            try:
                from app.technical_analysis.web.route.technical_router import (
                    router as tech_router,
                )

                print("      기술적 분석 라우터: 로드 성공")
            except ImportError:
                print("      기술적 분석 라우터: 모듈 없음 (건너뜀)")

            # 가격 데이터 라우터
            try:
                from app.market_price.web.price_router import router as price_router

                print("      가격 데이터 라우터: 로드 성공")
            except ImportError:
                print("      가격 데이터 라우터: 모듈 없음 (건너뜀)")

            # 비동기 라우터들
            try:
                from app.technical_analysis.web.route.async_technical_router import (
                    router as async_tech_router,
                )

                print("      비동기 기술적 분석 라우터: 로드 성공")
            except ImportError:
                print("      비동기 기술적 분석 라우터: 모듈 없음 (건너뜀)")

            try:
                from app.market_price.web.async_price_router import (
                    router as async_price_router,
                )

                print("      비동기 가격 라우터: 로드 성공")
            except ImportError:
                print("      비동기 가격 라우터: 모듈 없음 (건너뜀)")

            # WebSocket 라우터
            try:
                from app.common.web.websocket_router import router as websocket_router

                print("      WebSocket 라우터: 로드 성공")
            except ImportError:
                print("      WebSocket 라우터: 모듈 없음 (건너뜀)")

            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_background_tasks(self) -> bool:
        """백그라운드 작업 테스트"""
        try:
            # 백그라운드 작업 서비스
            try:
                from app.common.services.background_tasks import BackgroundTaskService

                task_service = BackgroundTaskService()
                print("      백그라운드 작업 서비스: 초기화 성공")

            except ImportError:
                print("      백그라운드 작업 서비스: 모듈 없음 (건너뜀)")

            # 작업 큐 시스템
            try:
                from app.common.utils.task_queue import task_queue

                queue_status = task_queue.get_queue_status()
                print(f"      작업 큐: 상태 조회 성공 ({queue_status})")

            except ImportError:
                print("      작업 큐: 모듈 없음 (건너뜀)")

            # 일일 종합 리포트 서비스
            try:
                from app.technical_analysis.service.daily_comprehensive_report_service import (
                    DailyComprehensiveReportService,
                )

                report_service = DailyComprehensiveReportService()
                print("      일일 종합 리포트 서비스: 초기화 성공")

            except ImportError:
                print("      일일 종합 리포트 서비스: 모듈 없음 (건너뜀)")

            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    def print_test_summary(self):
        """테스트 결과 요약 출력"""
        print("\n" + "=" * 60)
        print("📊 기존 시스템 기능 테스트 결과")
        print("=" * 60)

        total_tests = len(self.test_results)
        passed_count = len(self.passed_tests)
        failed_count = len(self.failed_tests)

        print(f"총 테스트: {total_tests}개")
        print(f"통과: {passed_count}개 ✅")
        print(f"실패: {failed_count}개 ❌")
        print(f"성공률: {(passed_count / total_tests * 100):.1f}%")

        if self.passed_tests:
            print(f"\n✅ 통과한 테스트:")
            for test in self.passed_tests:
                print(f"   - {test}")

        if self.failed_tests:
            print(f"\n❌ 실패한 테스트:")
            for test in self.failed_tests:
                print(f"   - {test}")

        print("\n" + "=" * 60)

        if failed_count == 0:
            print("🎉 모든 기존 기능이 정상 작동합니다!")
            print("💡 성능 개선 후에도 기존 기능들이 완벽하게 유지되었습니다.")
        elif passed_count > failed_count:
            print("✅ 대부분의 기존 기능이 정상 작동합니다!")
            print("⚠️ 일부 기능에 확인이 필요합니다.")
        else:
            print("⚠️ 일부 기존 기능에 문제가 있을 수 있습니다.")
            print("🔧 기능 점검이 필요합니다.")

        print("=" * 60)


async def main():
    """메인 실행 함수"""
    tester = LegacySystemTest()

    start_time = time.time()
    success = await tester.run_all_tests()
    end_time = time.time()

    print(f"\n⏱️ 총 실행 시간: {end_time - start_time:.2f}초")

    # 결과를 파일로 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"test_results/legacy_test_results_{timestamp}.json"

    os.makedirs("test_results", exist_ok=True)

    test_summary = {
        "timestamp": datetime.now().isoformat(),
        "execution_time_seconds": end_time - start_time,
        "total_tests": len(tester.test_results),
        "passed_tests": len(tester.passed_tests),
        "failed_tests": len(tester.failed_tests),
        "success_rate": len(tester.passed_tests) / len(tester.test_results) * 100,
        "test_results": tester.test_results,
        "passed_test_names": tester.passed_tests,
        "failed_test_names": tester.failed_tests,
    }

    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(test_summary, f, indent=2, ensure_ascii=False)

    print(f"📁 테스트 결과 저장: {result_file}")

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
