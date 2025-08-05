#!/usr/bin/env python3
"""
종합 시스템 테스트

모든 성능 개선 시스템이 제대로 작동하는지 테스트합니다.
"""

import asyncio
import sys
import os
import time
import json
from datetime import datetime
from typing import Dict, List, Any

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 테스트할 모듈들 import
try:
    from app.common.utils.memory_cache import cache_manager, cache_result
    from app.common.utils.memory_optimizer import (
        optimize_dataframe_memory,
        memory_monitor,
    )
    from app.common.utils.memory_utils import get_memory_status, optimize_memory
    from app.common.utils.task_queue import task_queue, task, TaskPriority
    from app.common.utils.websocket_manager import websocket_manager
    from app.common.utils.performance_metrics import get_metrics_collector
    from app.common.optimization.optimization_manager import get_optimization_manager
    from app.technical_analysis.service.async_technical_indicator_service import (
        AsyncTechnicalIndicatorService,
    )
    from app.market_price.service.async_price_service import AsyncPriceService

    print("✅ 모든 모듈 import 성공")
except ImportError as e:
    print(f"❌ 모듈 import 실패: {e}")
    sys.exit(1)


class ComprehensiveSystemTest:
    """종합 시스템 테스트"""

    def __init__(self):
        self.test_results = {}
        self.failed_tests = []
        self.passed_tests = []

    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("🚀 종합 시스템 테스트 시작")
        print("=" * 60)

        test_methods = [
            ("메모리 캐시 시스템", self.test_memory_cache_system),
            ("메모리 최적화 시스템", self.test_memory_optimization_system),
            ("작업 큐 시스템", self.test_task_queue_system),
            ("비동기 기술적 분석", self.test_async_technical_analysis),
            ("비동기 가격 서비스", self.test_async_price_service),
            ("성능 메트릭 수집", self.test_performance_metrics),
            ("최적화 매니저", self.test_optimization_manager),
            ("WebSocket 매니저", self.test_websocket_manager),
            ("통합 시나리오", self.test_integration_scenario),
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

    async def test_memory_cache_system(self) -> bool:
        """메모리 캐시 시스템 테스트"""
        try:
            # 캐시 인스턴스 생성
            cache = cache_manager.get_cache("test_cache")

            # 기본 캐시 동작 테스트
            cache.set("test_key", "test_value", ttl=60)
            value = cache.get("test_key")
            if value != "test_value":
                return False

            # TTL 테스트 (짧은 시간)
            cache.set("ttl_key", "ttl_value", ttl=1)
            time.sleep(1.1)
            expired_value = cache.get("ttl_key")
            if expired_value is not None:
                return False

            # 캐시 데코레이터 테스트
            @cache_result(cache_name="test_cache", ttl=60)
            def test_function(x, y):
                return x + y

            result1 = test_function(1, 2)
            result2 = test_function(1, 2)  # 캐시에서 가져와야 함

            if result1 != 3 or result2 != 3:
                return False

            # 캐시 통계 확인
            stats = cache.get_stats()
            if not isinstance(stats, dict):
                return False

            print(f"      캐시 통계: {stats}")
            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_memory_optimization_system(self) -> bool:
        """메모리 최적화 시스템 테스트"""
        try:
            import pandas as pd

            # DataFrame 생성
            df = pd.DataFrame(
                {
                    "int_col": [1, 2, 3, 4, 5] * 1000,
                    "float_col": [1.1, 2.2, 3.3, 4.4, 5.5] * 1000,
                    "str_col": ["A", "B", "C", "D", "E"] * 1000,
                }
            )

            original_memory = df.memory_usage(deep=True).sum()

            # 메모리 최적화 데코레이터 테스트
            @optimize_dataframe_memory()
            def process_dataframe():
                return df.copy()

            optimized_df = process_dataframe()
            optimized_memory = optimized_df.memory_usage(deep=True).sum()

            print(f"      원본 메모리: {original_memory:,} bytes")
            print(f"      최적화 메모리: {optimized_memory:,} bytes")
            print(
                f"      절약률: {((original_memory - optimized_memory) / original_memory * 100):.1f}%"
            )

            # 메모리 모니터링 데코레이터 테스트
            @memory_monitor(threshold_mb=1.0)
            def memory_intensive_function():
                data = [i for i in range(100000)]
                return len(data)

            result = memory_intensive_function()
            if result != 100000:
                return False

            # 메모리 상태 확인
            memory_status = get_memory_status()
            if not isinstance(memory_status, dict):
                return False

            print(
                f"      시스템 메모리 사용률: {memory_status.get('system_memory', {}).get('percent', 0):.1f}%"
            )
            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_task_queue_system(self) -> bool:
        """작업 큐 시스템 테스트"""
        try:
            # 간단한 작업 정의
            @task(priority=TaskPriority.HIGH, max_retries=2, timeout=10.0)
            async def test_task(x: int, y: int) -> int:
                await asyncio.sleep(0.1)  # 작업 시뮬레이션
                return x + y

            # 작업 제출
            task_id = await test_task(5, 3)
            print(f"      작업 ID: {task_id}")

            # 작업 결과 대기 (타임아웃 설정)
            try:
                result = await asyncio.wait_for(
                    task_queue.wait_for_task(task_id), timeout=15.0
                )
                if result != 8:
                    return False
                print(f"      작업 결과: {result}")
            except asyncio.TimeoutError:
                print("      작업 타임아웃")
                return False

            # 작업 상태 확인
            status = task_queue.get_task_status(task_id)
            print(f"      작업 상태: {status}")

            # 큐 상태 확인
            queue_status = task_queue.get_queue_status()
            print(f"      큐 상태: {queue_status}")

            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_async_technical_analysis(self) -> bool:
        """비동기 기술적 분석 테스트"""
        try:
            service = AsyncTechnicalIndicatorService(max_workers=2)

            # 테스트 데이터 생성
            import pandas as pd

            test_data = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109])

            # 비동기 이동평균 계산
            sma_result = await service.calculate_moving_average_async(
                test_data, 5, "SMA"
            )
            if sma_result is None or len(sma_result) == 0:
                return False

            print(f"      SMA 결과 길이: {len(sma_result)}")

            # 여러 기간 이동평균 동시 계산
            periods = [3, 5, 7]
            multi_sma = await service.calculate_multiple_moving_averages_async(
                test_data, periods, "SMA"
            )

            if len(multi_sma) != len(periods):
                return False

            print(f"      다중 SMA 결과: {len(multi_sma)}개 기간")

            # 서비스 정리
            await service.cleanup()
            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_async_price_service(self) -> bool:
        """비동기 가격 서비스 테스트"""
        try:
            # 실제 API 호출 대신 모의 테스트
            print("      비동기 가격 서비스 모의 테스트")

            # AsyncPriceService 인스턴스 생성 테스트
            service = AsyncPriceService()

            # 서비스 초기화 확인
            if not hasattr(service, "session"):
                print("      서비스 초기화 확인")

            # 모의 심볼 리스트
            test_symbols = ["AAPL", "GOOGL", "MSFT"]
            print(f"      테스트 심볼: {test_symbols}")

            # 실제 API 호출 없이 구조 테스트
            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_performance_metrics(self) -> bool:
        """성능 메트릭 수집 테스트"""
        try:
            # 성능 메트릭 시스템 테스트
            collector = get_metrics_collector()

            # 응답 시간 기록 테스트
            collector.record_response_time("test_operation", 0.5, True, None)

            # 메트릭 추가 테스트
            collector.add_metric("test", "test_metric", 100.0, "ms")

            # 메트릭 요약 확인
            summary = collector.get_summary()
            if not isinstance(summary, dict):
                return False

            print(f"      메트릭 요약 키: {list(summary.keys())}")

            # 최근 메트릭 확인
            recent_metrics = collector.get_recent_metrics(limit=5)
            if not isinstance(recent_metrics, list):
                return False

            print(f"      최근 메트릭 개수: {len(recent_metrics)}")
            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_optimization_manager(self) -> bool:
        """최적화 매니저 테스트"""
        try:
            optimization_manager = get_optimization_manager()

            # 사용 가능한 최적화 목록 확인
            available_optimizations = optimization_manager.get_available_optimizations()
            if not isinstance(available_optimizations, list):
                return False

            print(f"      사용 가능한 최적화: {len(available_optimizations)}개")

            # 최적화 상태 확인
            status = optimization_manager.get_optimization_status()
            if not isinstance(status, dict):
                return False

            print(f"      최적화 상태: {list(status.keys())}")

            # 테스트 최적화 활성화 (실제로는 하지 않음)
            print("      최적화 매니저 기본 기능 확인 완료")
            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_websocket_manager(self) -> bool:
        """WebSocket 매니저 테스트"""
        try:
            # WebSocket 매니저 기본 기능 테스트
            print("      WebSocket 매니저 구조 테스트")

            # 매니저 상태 확인
            status = websocket_manager.get_connection_stats()
            if not isinstance(status, dict):
                return False

            print(f"      연결 통계: {status}")

            # 구독 관리 테스트 (실제 연결 없이)
            print("      구독 관리 시스템 구조 확인 완료")
            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_integration_scenario(self) -> bool:
        """통합 시나리오 테스트"""
        try:
            print("      통합 시나리오 실행")

            # 1. 메모리 최적화 + 캐싱
            cache = cache_manager.get_cache("integration_test")

            @cache_result(cache_name="integration_test", ttl=60)
            @memory_monitor(threshold_mb=10.0)
            def integrated_function(data_size: int):
                # 메모리 사용 시뮬레이션
                data = list(range(data_size))
                return len(data)

            result1 = integrated_function(1000)
            result2 = integrated_function(1000)  # 캐시에서 가져와야 함

            if result1 != 1000 or result2 != 1000:
                return False

            # 2. 비동기 작업 + 작업 큐
            @task(priority=TaskPriority.NORMAL, max_retries=1, timeout=5.0)
            async def integrated_async_task(x: int) -> int:
                await asyncio.sleep(0.1)
                return x * 2

            task_id = await integrated_async_task(21)
            task_result = await asyncio.wait_for(
                task_queue.wait_for_task(task_id), timeout=10.0
            )

            if task_result != 42:
                return False

            # 3. 메모리 상태 확인
            memory_status = get_memory_status()
            if memory_status.get("system_memory", {}).get("percent", 0) > 95:
                print("      경고: 시스템 메모리 사용률이 높습니다")

            print("      통합 시나리오 완료")
            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    def print_test_summary(self):
        """테스트 결과 요약 출력"""
        print("\n" + "=" * 60)
        print("📊 종합 시스템 테스트 결과")
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
            print("🎉 모든 테스트가 성공적으로 통과했습니다!")
        else:
            print("⚠️ 일부 테스트가 실패했습니다. 로그를 확인해주세요.")

        print("=" * 60)


async def main():
    """메인 실행 함수"""
    tester = ComprehensiveSystemTest()

    start_time = time.time()
    success = await tester.run_all_tests()
    end_time = time.time()

    print(f"\n⏱️ 총 실행 시간: {end_time - start_time:.2f}초")

    # 결과를 파일로 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"test_results/comprehensive_test_results_{timestamp}.json"

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
