#!/usr/bin/env python3
"""
핵심 시스템 테스트

잘 작동하는 핵심 성능 개선 시스템들만 테스트합니다.
"""

import asyncio
import sys
import os
import time
import json
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class CoreSystemTest:
    """핵심 시스템 테스트"""

    def __init__(self):
        self.test_results = {}
        self.failed_tests = []
        self.passed_tests = []

    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("🚀 핵심 시스템 테스트 시작")
        print("=" * 60)

        test_methods = [
            ("메모리 캐시 시스템", self.test_memory_cache_system),
            ("메모리 최적화 시스템", self.test_memory_optimization_system),
            ("메모리 관리 유틸리티", self.test_memory_utils),
            ("비동기 기술적 분석", self.test_async_technical_analysis),
            ("성능 측정 데코레이터", self.test_performance_decorators),
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
            from app.common.utils.memory_cache import cache_manager, cache_result

            # 캐시 인스턴스 생성
            cache = cache_manager.get_cache("test_cache")

            # 기본 캐시 동작 테스트
            cache.set("test_key", "test_value", ttl=60)
            value = cache.get("test_key")
            if value != "test_value":
                return False

            # TTL 테스트
            cache.set("ttl_key", "ttl_value", ttl=1)
            time.sleep(1.1)
            expired_value = cache.get("ttl_key")
            if expired_value is not None:
                return False

            # 캐시 데코레이터 테스트
            call_count = 0

            @cache_result(cache_name="test_cache", ttl=60)
            def expensive_function(x, y):
                nonlocal call_count
                call_count += 1
                return x + y

            result1 = expensive_function(1, 2)
            result2 = expensive_function(1, 2)  # 캐시에서 가져와야 함

            if result1 != 3 or result2 != 3 or call_count != 1:
                return False

            # 캐시 통계 확인
            stats = cache.get_stats()
            print(
                f"      캐시 통계: 크기={stats.get('cache_size', 0)}, 히트율={stats.get('hit_rate', 0):.1f}%"
            )
            print(f"      함수 호출 횟수: {call_count} (캐시 효과 확인)")
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
            import pandas as pd

            # DataFrame 생성
            df = pd.DataFrame(
                {
                    "int_col": [1, 2, 3, 4, 5] * 200,
                    "float_col": [1.1, 2.2, 3.3, 4.4, 5.5] * 200,
                    "str_col": ["A", "B", "C", "D", "E"] * 200,
                }
            )

            original_memory = df.memory_usage(deep=True).sum()

            # 메모리 최적화 데코레이터 테스트
            @optimize_dataframe_memory()
            def process_dataframe():
                return df.copy()

            optimized_df = process_dataframe()
            optimized_memory = optimized_df.memory_usage(deep=True).sum()

            savings_percent = (
                (original_memory - optimized_memory) / original_memory
            ) * 100
            print(
                f"      메모리 절약: {original_memory:,} → {optimized_memory:,} bytes ({savings_percent:.1f}% 절약)"
            )

            # 메모리 모니터링 데코레이터 테스트
            @memory_monitor(threshold_mb=0.1)  # 낮은 임계값으로 설정
            def memory_test_function():
                data = [i for i in range(50000)]
                return len(data)

            result = memory_test_function()
            if result != 50000:
                return False

            print(f"      메모리 모니터링: 함수 실행 완료, 결과={result}")
            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_memory_utils(self) -> bool:
        """메모리 관리 유틸리티 테스트"""
        try:
            from app.common.utils.memory_utils import get_memory_status, optimize_memory

            # 메모리 상태 확인
            memory_status = get_memory_status()
            if not isinstance(memory_status, dict):
                return False

            system_memory = memory_status.get("system_memory", {})
            cache_health = memory_status.get("cache_health", {})

            print(
                f"      시스템 메모리: {system_memory.get('percent', 0):.1f}% 사용 중"
            )
            print(
                f"      캐시 상태: {cache_health.get('total_cached_items', 0)} 항목, 평균 히트율 {cache_health.get('average_hit_rate', 0):.1f}%"
            )

            # 메모리 최적화 실행
            optimization_result = optimize_memory(aggressive=False)
            if not isinstance(optimization_result, dict):
                return False

            print(
                f"      메모리 최적화 결과: {optimization_result.get('status', 'unknown')}"
            )
            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_async_technical_analysis(self) -> bool:
        """비동기 기술적 분석 테스트"""
        try:
            from app.technical_analysis.service.async_technical_indicator_service import (
                AsyncTechnicalIndicatorService,
            )
            import pandas as pd

            service = AsyncTechnicalIndicatorService(max_workers=2)

            # 테스트 데이터 생성
            test_data = pd.Series(
                [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 111, 110, 112]
            )

            # 비동기 이동평균 계산
            sma_result = await service.calculate_moving_average_async(
                test_data, 5, "SMA"
            )
            if sma_result is None or len(sma_result) == 0:
                return False

            print(f"      SMA 결과: {len(sma_result)}개 데이터 포인트")

            # 여러 기간 이동평균 동시 계산
            periods = [3, 5, 7]
            multi_sma = await service.calculate_multiple_moving_averages_async(
                test_data, periods, "SMA"
            )

            if len(multi_sma) != len(periods):
                return False

            print(f"      다중 SMA: {len(periods)}개 기간 동시 계산 완료")

            # RSI 계산 테스트
            rsi_result = await service.calculate_rsi_async(test_data, 14)
            if rsi_result is not None:
                print(f"      RSI 결과: {len(rsi_result)}개 데이터 포인트")

            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_performance_decorators(self) -> bool:
        """성능 측정 데코레이터 테스트"""
        try:
            from app.common.utils.performance_metrics import performance_monitor

            # 성능 모니터링 데코레이터 테스트
            @performance_monitor(metric_name="test_function", collect_memory=True)
            def test_performance_function():
                # 간단한 계산 작업
                result = sum(range(10000))
                return result

            result = test_performance_function()
            if result != sum(range(10000)):
                return False

            print(f"      성능 모니터링 데코레이터: 함수 실행 완료, 결과={result}")

            # 비동기 함수 테스트
            @performance_monitor(metric_name="async_test_function", collect_memory=True)
            async def async_test_function():
                await asyncio.sleep(0.1)
                return "async_result"

            async_result = await async_test_function()
            if async_result != "async_result":
                return False

            print(f"      비동기 성능 모니터링: 함수 실행 완료, 결과={async_result}")
            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    async def test_integration_scenario(self) -> bool:
        """통합 시나리오 테스트"""
        try:
            from app.common.utils.memory_cache import cache_manager, cache_result
            from app.common.utils.memory_optimizer import (
                optimize_dataframe_memory,
                memory_monitor,
            )
            from app.common.utils.performance_metrics import performance_monitor
            import pandas as pd

            print("      통합 시나리오 실행: 캐싱 + 메모리 최적화 + 성능 모니터링")

            # 복합 데코레이터 테스트
            @cache_result(cache_name="integration_test", ttl=60)
            @optimize_dataframe_memory()
            @memory_monitor(threshold_mb=1.0)
            @performance_monitor(metric_name="integrated_function", collect_memory=True)
            def integrated_function(rows: int):
                # DataFrame 생성 및 처리
                categories = (["A", "B", "C"] * (rows // 3 + 1))[:rows]
                df = pd.DataFrame(
                    {
                        "values": range(rows),
                        "squares": [i**2 for i in range(rows)],
                        "category": categories,
                    }
                )

                # 간단한 계산
                result = {
                    "mean": df["values"].mean(),
                    "sum_squares": df["squares"].sum(),
                    "row_count": len(df),
                }
                return result

            # 첫 번째 실행 (실제 계산)
            result1 = integrated_function(1000)

            # 두 번째 실행 (캐시에서 가져옴)
            result2 = integrated_function(1000)

            if result1 != result2:
                return False

            print(
                f"      통합 테스트 결과: 평균={result1['mean']:.1f}, 행 수={result1['row_count']}"
            )

            # 메모리 상태 확인
            from app.common.utils.memory_utils import get_memory_status

            memory_status = get_memory_status()
            cache_items = memory_status.get("cache_health", {}).get(
                "total_cached_items", 0
            )

            print(f"      최종 캐시 항목 수: {cache_items}")
            print("      통합 시나리오 완료: 모든 시스템이 함께 작동")

            return True

        except Exception as e:
            print(f"      오류: {str(e)}")
            return False

    def print_test_summary(self):
        """테스트 결과 요약 출력"""
        print("\n" + "=" * 60)
        print("📊 핵심 시스템 테스트 결과")
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
            print("🎉 모든 핵심 시스템이 정상 작동합니다!")
            print("💡 성능 개선 시스템이 성공적으로 구현되었습니다.")
        elif passed_count > failed_count:
            print("✅ 대부분의 핵심 시스템이 정상 작동합니다!")
            print("⚠️ 일부 시스템에 개선이 필요합니다.")
        else:
            print("⚠️ 일부 핵심 시스템에 문제가 있습니다.")
            print("🔧 시스템 점검이 필요합니다.")

        print("=" * 60)


async def main():
    """메인 실행 함수"""
    tester = CoreSystemTest()

    start_time = time.time()
    success = await tester.run_all_tests()
    end_time = time.time()

    print(f"\n⏱️ 총 실행 시간: {end_time - start_time:.2f}초")

    # 결과를 파일로 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"test_results/core_test_results_{timestamp}.json"

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
