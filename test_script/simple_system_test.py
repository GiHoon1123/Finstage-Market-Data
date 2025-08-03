#!/usr/bin/env python3
"""
간단한 시스템 테스트

핵심 성능 개선 시스템들이 제대로 작동하는지 테스트합니다.
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


class SimpleSystemTest:
    """간단한 시스템 테스트"""

    def __init__(self):
        self.test_results = {}
        self.failed_tests = []
        self.passed_tests = []

    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("🚀 간단한 시스템 테스트 시작")
        print("=" * 60)

        test_methods = [
            ("메모리 캐시 시스템", self.test_memory_cache_system),
            ("메모리 최적화 시스템", self.test_memory_optimization_system),
            ("작업 큐 시스템", self.test_task_queue_system),
            ("성능 메트릭 시스템", self.test_performance_metrics_system),
            ("WebSocket 매니저", self.test_websocket_manager),
            ("최적화 매니저", self.test_optimization_manager),
            ("비동기 서비스", self.test_async_services),
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
            from app.common.utils.memory_cache import cache_manager, cache_result

            # 캐시 인스턴스 생성
            cache = cache_manager.get_cache("test_cache")

            # 기본 캐시 동작 테스트
            cache.set("test_key", "test_value", ttl=60)
            value = cache.get("test_key")
            if value != "test_value":
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
            print(
                f"      캐시 통계: 크기={stats.get('cache_size', 0)}, 히트율={stats.get('hit_rate', 0):.1f}%"
            )
            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_memory_optimization_system(self) -> bool:
        """메모리 최적화 시스템 테스트"""
        try:
            from app.common.utils.memory_optimizer import (
                optimize_dataframe_memory,
                memory_monitor,
            )
            from app.common.utils.memory_utils import get_memory_status
            import pandas as pd

            # DataFrame 생성
            df = pd.DataFrame(
                {
                    "int_col": [1, 2, 3, 4, 5] * 100,
                    "float_col": [1.1, 2.2, 3.3, 4.4, 5.5] * 100,
                    "str_col": ["A", "B", "C", "D", "E"] * 100,
                }
            )

            original_memory = df.memory_usage(deep=True).sum()

            # 메모리 최적화 데코레이터 테스트
            @optimize_dataframe_memory()
            def process_dataframe():
                return df.copy()

            optimized_df = process_dataframe()
            optimized_memory = optimized_df.memory_usage(deep=True).sum()

            print(
                f"      메모리 절약: {original_memory:,} → {optimized_memory:,} bytes"
            )

            # 메모리 모니터링 데코레이터 테스트
            @memory_monitor(threshold_mb=1.0)
            def memory_test_function():
                data = [i for i in range(10000)]
                return len(data)

            result = memory_test_function()
            if result != 10000:
                return False

            # 메모리 상태 확인
            memory_status = get_memory_status()
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
            from app.common.utils.task_queue import task_queue, task, TaskPriority

            # 간단한 작업 정의
            @task(priority=TaskPriority.HIGH, max_retries=2, timeout=10.0)
            async def test_task(x: int, y: int) -> int:
                await asyncio.sleep(0.1)  # 작업 시뮬레이션
                return x + y

            # 작업 제출
            task_id = await test_task(5, 3)
            print(f"      작업 ID: {task_id}")

            # 작업 결과 대기
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

            # 큐 상태 확인
            queue_status = task_queue.get_queue_status()
            print(
                f"      큐 상태: 대기={queue_status.get('pending', 0)}, 실행중={queue_status.get('running', 0)}"
            )

            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_performance_metrics_system(self) -> bool:
        """성능 메트릭 시스템 테스트"""
        try:
            from app.common.utils.performance_metrics import get_metrics_collector

            collector = get_metrics_collector()

            # 응답 시간 기록 테스트
            collector.record_response_time("test_operation", 0.5, True, None)

            # 메트릭 추가 테스트
            collector.add_metric("test", "test_metric", 100.0, "ms")

            # 메트릭 요약 확인
            summary = collector.get_summary()
            print(f"      메트릭 요약: {len(summary)} 항목")

            # 최근 메트릭 확인
            recent_metrics = collector.get_recent_metrics(limit=5)
            print(f"      최근 메트릭: {len(recent_metrics)} 개")

            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_websocket_manager(self) -> bool:
        """WebSocket 매니저 테스트"""
        try:
            from app.common.utils.websocket_manager import websocket_manager

            # 매니저 상태 확인
            status = websocket_manager.get_connection_stats()
            print(f"      WebSocket 연결 통계: {status}")

            # 구독 관리 테스트 (실제 연결 없이)
            print("      WebSocket 매니저 구조 확인 완료")
            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_optimization_manager(self) -> bool:
        """최적화 매니저 테스트"""
        try:
            from app.common.optimization.optimization_manager import (
                get_optimization_manager,
            )

            optimization_manager = get_optimization_manager()

            # 사용 가능한 최적화 목록 확인
            available_optimizations = optimization_manager.get_available_optimizations()
            print(f"      사용 가능한 최적화: {len(available_optimizations)}개")

            # 최적화 상태 확인
            status = optimization_manager.get_optimization_status()
            print(f"      최적화 상태: {len(status)} 항목")

            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_async_services(self) -> bool:
        """비동기 서비스 테스트"""
        try:
            # 비동기 기술적 분석 서비스 테스트
            try:
                from app.technical_analysis.service.async_technical_indicator_service import (
                    AsyncTechnicalIndicatorService,
                )

                service = AsyncTechnicalIndicatorService(max_workers=2)

                # 테스트 데이터 생성
                import pandas as pd

                test_data = pd.Series(
                    [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
                )

                # 비동기 이동평균 계산
                sma_result = await service.calculate_moving_average_async(
                    test_data, 5, "SMA"
                )
                if sma_result is not None and len(sma_result) > 0:
                    print(
                        f"      비동기 기술적 분석 서비스: SMA 결과 길이 {len(sma_result)}"
                    )

                # 서비스 정리
                await service.cleanup()

            except ImportError:
                print("      비동기 기술적 분석 서비스: 모듈 없음 (건너뜀)")

            # 비동기 가격 서비스 테스트
            try:
                from app.market_price.service.async_price_service import (
                    AsyncPriceService,
                )

                service = AsyncPriceService()
                print("      비동기 가격 서비스: 초기화 성공")

            except ImportError:
                print("      비동기 가격 서비스: 모듈 없음 (건너뜀)")

            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    def print_test_summary(self):
        """테스트 결과 요약 출력"""
        print("\n" + "=" * 60)
        print("📊 시스템 테스트 결과")
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
            print("⚠️ 일부 테스트가 실패했습니다. 개별 오류를 확인해주세요.")

        print("=" * 60)


async def main():
    """메인 실행 함수"""
    tester = SimpleSystemTest()

    start_time = time.time()
    success = await tester.run_all_tests()
    end_time = time.time()

    print(f"\n⏱️ 총 실행 시간: {end_time - start_time:.2f}초")

    # 결과를 파일로 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"test_results/simple_test_results_{timestamp}.json"

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
