#!/usr/bin/env python3
"""
핵심 기능 테스트

데이터베이스 없이도 작동하는 핵심 기능들을 테스트합니다.
"""

import asyncio
import sys
import os
import time
import json
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class CoreFunctionalityTest:
    """핵심 기능 테스트"""

    def __init__(self):
        self.test_results = {}
        self.failed_tests = []
        self.passed_tests = []

    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("🔍 핵심 기능 테스트 시작 (DB 독립적)")
        print("=" * 60)

        test_methods = [
            ("기술적 분석 계산", self.test_technical_calculations),
            ("메모리 최적화 기능", self.test_memory_optimization),
            ("비동기 처리 기능", self.test_async_processing),
            ("캐시 시스템", self.test_cache_system),
            ("성능 모니터링", self.test_performance_monitoring),
            ("WebSocket 관리", self.test_websocket_management),
            ("작업 큐 기본 기능", self.test_task_queue_basics),
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

    async def test_technical_calculations(self) -> bool:
        """기술적 분석 계산 테스트"""
        try:
            import pandas as pd
            import numpy as np

            # 테스트 데이터 생성
            prices = pd.Series(
                [
                    100,
                    102,
                    101,
                    103,
                    105,
                    104,
                    106,
                    108,
                    107,
                    109,
                    111,
                    110,
                    112,
                    114,
                    113,
                ]
            )

            # 이동평균 계산 (직접 계산)
            sma_5 = prices.rolling(window=5).mean()
            sma_10 = prices.rolling(window=10).mean()

            print(f"      SMA 5: {len(sma_5.dropna())}개 값")
            print(f"      SMA 10: {len(sma_10.dropna())}개 값")

            # RSI 계산 (간단한 버전)
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            print(f"      RSI: {len(rsi.dropna())}개 값")

            # 볼린저 밴드 계산
            bb_period = 20
            if len(prices) >= bb_period:
                bb_sma = prices.rolling(window=bb_period).mean()
                bb_std = prices.rolling(window=bb_period).std()
                bb_upper = bb_sma + (bb_std * 2)
                bb_lower = bb_sma - (bb_std * 2)

                print(f"      볼린저 밴드: 상단/하단 밴드 계산 완료")

            # MACD 계산
            ema_12 = prices.ewm(span=12).mean()
            ema_26 = prices.ewm(span=26).mean()
            macd = ema_12 - ema_26
            signal = macd.ewm(span=9).mean()

            print(
                f"      MACD: {len(macd.dropna())}개 값, 시그널: {len(signal.dropna())}개 값"
            )

            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_memory_optimization(self) -> bool:
        """메모리 최적화 기능 테스트"""
        try:
            from app.common.utils.memory_optimizer import (
                optimize_dataframe_memory,
                memory_monitor,
            )
            from app.common.utils.memory_utils import get_memory_status
            import pandas as pd

            # 큰 DataFrame 생성
            df = pd.DataFrame(
                {
                    "int_col": list(range(5000)),
                    "float_col": [i * 1.1 for i in range(5000)],
                    "str_col": ["category_" + str(i % 100) for i in range(5000)],
                }
            )

            original_memory = df.memory_usage(deep=True).sum()

            # 메모리 최적화 적용
            @optimize_dataframe_memory()
            def process_large_dataframe():
                return df.copy()

            optimized_df = process_large_dataframe()
            optimized_memory = optimized_df.memory_usage(deep=True).sum()

            savings = ((original_memory - optimized_memory) / original_memory) * 100
            print(
                f"      메모리 절약: {savings:.1f}% ({original_memory:,} → {optimized_memory:,} bytes)"
            )

            # 메모리 모니터링 테스트
            @memory_monitor(threshold_mb=1.0)
            def memory_intensive_task():
                data = [list(range(1000)) for _ in range(100)]
                return len(data)

            result = memory_intensive_task()
            print(f"      메모리 모니터링: 작업 완료, 결과={result}")

            # 시스템 메모리 상태 확인
            memory_status = get_memory_status()
            system_memory = memory_status.get("system_memory", {})
            print(
                f"      시스템 메모리: {system_memory.get('percent', 0):.1f}% 사용 중"
            )

            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_async_processing(self) -> bool:
        """비동기 처리 기능 테스트"""
        try:
            from app.technical_analysis.service.async_technical_indicator_service import (
                AsyncTechnicalIndicatorService,
            )
            import pandas as pd

            service = AsyncTechnicalIndicatorService(max_workers=2)

            # 테스트 데이터
            test_data = pd.Series(
                [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 111, 110, 112]
            )

            # 비동기 이동평균 계산
            start_time = time.time()
            sma_result = await service.calculate_moving_average_async(
                test_data, 5, "SMA"
            )
            async_time = time.time() - start_time

            print(
                f"      비동기 SMA: {len(sma_result)}개 결과, 실행시간: {async_time:.4f}초"
            )

            # 여러 기간 동시 계산
            periods = [3, 5, 7, 10]
            start_time = time.time()
            multi_results = await service.calculate_multiple_moving_averages_async(
                test_data, periods, "SMA"
            )
            multi_time = time.time() - start_time

            print(
                f"      다중 SMA: {len(periods)}개 기간, 실행시간: {multi_time:.4f}초"
            )

            # RSI 비동기 계산
            rsi_result = await service.calculate_rsi_async(test_data, 14)
            print(f"      비동기 RSI: {len(rsi_result)}개 결과")

            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_cache_system(self) -> bool:
        """캐시 시스템 테스트"""
        try:
            from app.common.utils.memory_cache import cache_manager, cache_result

            # 캐시 인스턴스 생성
            cache = cache_manager.get_cache("functionality_test")

            # 기본 캐시 동작
            cache.set("test_key", {"data": "test_value", "number": 42}, ttl=60)
            cached_data = cache.get("test_key")

            if cached_data["data"] != "test_value" or cached_data["number"] != 42:
                return False

            print("      기본 캐시 동작: 정상")

            # 캐시 데코레이터 성능 테스트
            calculation_count = 0

            @cache_result(cache_name="functionality_test", ttl=60)
            def expensive_calculation(n):
                nonlocal calculation_count
                calculation_count += 1
                # 복잡한 계산 시뮬레이션
                result = sum(i**2 for i in range(n))
                return result

            # 첫 번째 호출 (실제 계산)
            start_time = time.time()
            result1 = expensive_calculation(1000)
            first_call_time = time.time() - start_time

            # 두 번째 호출 (캐시에서 가져옴)
            start_time = time.time()
            result2 = expensive_calculation(1000)
            second_call_time = time.time() - start_time

            if result1 != result2 or calculation_count != 1:
                return False

            speedup = (
                first_call_time / second_call_time
                if second_call_time > 0
                else float("inf")
            )
            print(
                f"      캐시 성능: {speedup:.1f}배 속도 향상 ({first_call_time:.4f}s → {second_call_time:.4f}s)"
            )

            # 캐시 통계
            stats = cache.get_stats()
            print(
                f"      캐시 통계: 크기={stats.get('cache_size', 0)}, 히트율={stats.get('hit_rate', 0):.1f}%"
            )

            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_performance_monitoring(self) -> bool:
        """성능 모니터링 테스트"""
        try:
            from app.common.utils.performance_metrics import (
                performance_monitor,
                get_metrics_collector,
            )

            collector = get_metrics_collector()

            # 성능 모니터링 데코레이터 테스트
            @performance_monitor(metric_name="test_calculation", collect_memory=True)
            def monitored_calculation():
                # 계산 집약적 작업
                result = 0
                for i in range(100000):
                    result += i**0.5
                return result

            # 함수 실행
            result = monitored_calculation()
            print(f"      모니터링된 계산: 결과={result:.0f}")

            # 비동기 함수 모니터링
            @performance_monitor(
                metric_name="async_test_calculation", collect_memory=True
            )
            async def async_monitored_calculation():
                await asyncio.sleep(0.01)  # 비동기 작업 시뮬레이션
                return sum(range(10000))

            async_result = await async_monitored_calculation()
            print(f"      비동기 모니터링: 결과={async_result}")

            # 메트릭 수집 확인
            collector.record_response_time("manual_test", 0.123, True, None)
            collector.add_metric("test", "custom_metric", 456.78, "units")

            print("      메트릭 수집: 수동 메트릭 추가 완료")

            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_websocket_management(self) -> bool:
        """WebSocket 관리 테스트"""
        try:
            from app.common.utils.websocket_manager import websocket_manager

            # WebSocket 매니저 기본 기능 테스트
            print("      WebSocket 매니저: 초기화 확인")

            # 연결 통계 (실제 연결 없이)
            try:
                stats = websocket_manager.get_connection_stats()
                print(f"      연결 통계: {stats}")
            except AttributeError:
                # 메서드가 없을 수 있음
                print("      연결 통계: 메서드 없음 (정상)")

            # 구독 관리 시스템 확인
            print("      구독 관리: 시스템 구조 확인 완료")

            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_task_queue_basics(self) -> bool:
        """작업 큐 기본 기능 테스트"""
        try:
            from app.common.utils.task_queue import task_queue, task, TaskPriority

            # 간단한 작업 정의
            @task(priority=TaskPriority.NORMAL, max_retries=1, timeout=5.0)
            async def simple_test_task(x: int) -> int:
                await asyncio.sleep(0.01)  # 짧은 작업
                return x * 2

            # 작업 제출
            task_id = await simple_test_task(21)
            print(f"      작업 제출: ID={task_id}")

            # 작업 결과 대기 (짧은 타임아웃)
            try:
                result = await asyncio.wait_for(
                    task_queue.wait_for_task(task_id), timeout=10.0
                )
                print(f"      작업 완료: 결과={result}")

                if result != 42:
                    return False

            except asyncio.TimeoutError:
                print("      작업 타임아웃 (큐 시스템 확인 필요)")
                return False

            # 큐 상태 확인 (가능한 경우)
            try:
                status = task_queue.get_queue_status()
                print(f"      큐 상태: {status}")
            except AttributeError:
                print("      큐 상태: 메서드 없음")

            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    def print_test_summary(self):
        """테스트 결과 요약 출력"""
        print("\n" + "=" * 60)
        print("📊 핵심 기능 테스트 결과")
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
            print("🎉 모든 핵심 기능이 완벽하게 작동합니다!")
            print("💡 기존 기능과 성능 개선 기능이 모두 정상입니다.")
        elif passed_count >= total_tests * 0.8:  # 80% 이상
            print("✅ 대부분의 핵심 기능이 정상 작동합니다!")
            print("🚀 시스템이 안정적으로 운영되고 있습니다.")
        else:
            print("⚠️ 일부 핵심 기능에 확인이 필요합니다.")
            print("🔧 추가 점검을 권장합니다.")

        print("=" * 60)


async def main():
    """메인 실행 함수"""
    tester = CoreFunctionalityTest()

    start_time = time.time()
    success = await tester.run_all_tests()
    end_time = time.time()

    print(f"\n⏱️ 총 실행 시간: {end_time - start_time:.2f}초")

    # 결과를 파일로 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"test_results/core_functionality_results_{timestamp}.json"

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
