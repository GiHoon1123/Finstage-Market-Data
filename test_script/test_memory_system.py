"""
메모리 관리 시스템 테스트 및 사용 예시

실제 사용 시나리오를 통해 메모리 캐시와 최적화 시스템의 
효과를 확인할 수 있습니다.
"""

import time
import pandas as pd
import numpy as np
from typing import List, Dict, Any
import asyncio

from app.common.utils.memory_cache import cache_result, cache_technical_analysis
from app.common.utils.memory_optimizer import (
    optimize_dataframe_memory,
    memory_monitor,
    MemoryOptimizer,
)
from app.common.utils.memory_utils import (
    get_memory_status,
    optimize_memory,
    integrated_memory_manager,
)
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class MemorySystemTester:
    """메모리 시스템 테스트 클래스"""

    def __init__(self):
        self.test_results = []

    @cache_technical_analysis(ttl=300)
    def calculate_technical_indicators(
        self, symbol: str, period: int = 20
    ) -> Dict[str, Any]:
        """기술적 지표 계산 (캐싱 적용)"""
        print(f"🔄 {symbol}의 기술적 지표 계산 중... (period: {period})")

        # 실제 계산을 시뮬레이션 (시간 소모적인 작업)
        time.sleep(0.5)  # 실제로는 복잡한 계산

        # 가상의 기술적 지표 데이터 생성
        np.random.seed(hash(symbol) % 1000)  # 심볼별 일관된 데이터

        prices = np.random.normal(100, 10, 100)

        return {
            "symbol": symbol,
            "sma_20": np.mean(prices[-period:]),
            "ema_20": self._calculate_ema(prices, period),
            "rsi": np.random.uniform(30, 70),
            "macd": np.random.uniform(-2, 2),
            "bollinger_upper": np.mean(prices[-period:]) + 2 * np.std(prices[-period:]),
            "bollinger_lower": np.mean(prices[-period:]) - 2 * np.std(prices[-period:]),
            "calculated_at": time.time(),
        }

    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """지수이동평균 계산"""
        alpha = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        return ema

    @optimize_dataframe_memory(aggressive=False)
    def create_large_dataframe(self, rows: int = 10000) -> pd.DataFrame:
        """큰 DataFrame 생성 및 메모리 최적화"""
        print(f"📊 {rows:,}행의 DataFrame 생성 중...")

        # 메모리 비효율적인 데이터 타입으로 생성
        data = {
            "symbol": np.random.choice(["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"], rows),
            "price": np.random.uniform(50.0, 500.0, rows).astype(np.float64),
            "volume": np.random.randint(1000, 1000000, rows).astype(np.int64),
            "change_percent": np.random.uniform(-10.0, 10.0, rows).astype(np.float64),
            "market_cap": np.random.randint(1000000, 1000000000, rows).astype(np.int64),
            "sector": np.random.choice(
                ["Tech", "Finance", "Healthcare", "Energy"], rows
            ),
            "is_active": np.random.choice([True, False], rows),
            "rating": np.random.randint(1, 6, rows).astype(np.int64),
        }

        df = pd.DataFrame(data)
        print(f"✅ DataFrame 생성 완료: {df.shape[0]:,} 행, {df.shape[1]} 열")

        return df

    @memory_monitor(threshold_mb=100.0)
    def memory_intensive_operation(self, iterations: int = 5) -> List[Dict[str, Any]]:
        """메모리 집약적 작업 (모니터링 적용)"""
        print(f"🔥 메모리 집약적 작업 시작 ({iterations}회 반복)")

        results = []

        for i in range(iterations):
            # 큰 DataFrame 생성
            df = self.create_large_dataframe(rows=5000)

            # 기술적 지표 계산 (캐싱 효과 확인)
            symbols = ["AAPL", "GOOGL", "MSFT"]
            indicators = {}

            for symbol in symbols:
                indicators[symbol] = self.calculate_technical_indicators(symbol)

            # 결과 저장
            results.append(
                {
                    "iteration": i + 1,
                    "dataframe_shape": df.shape,
                    "dataframe_memory_mb": df.memory_usage(deep=True).sum()
                    / 1024
                    / 1024,
                    "indicators_calculated": len(indicators),
                    "timestamp": time.time(),
                }
            )

            print(f"  ✅ 반복 {i + 1}/{iterations} 완료")

        return results

    def test_cache_performance(self) -> Dict[str, Any]:
        """캐시 성능 테스트"""
        print("\n🧪 캐시 성능 테스트 시작")

        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]

        # 첫 번째 실행 (캐시 미스)
        start_time = time.time()
        first_results = {}
        for symbol in symbols:
            first_results[symbol] = self.calculate_technical_indicators(symbol)
        first_duration = time.time() - start_time

        print(f"  첫 번째 실행 (캐시 미스): {first_duration:.2f}초")

        # 두 번째 실행 (캐시 히트)
        start_time = time.time()
        second_results = {}
        for symbol in symbols:
            second_results[symbol] = self.calculate_technical_indicators(symbol)
        second_duration = time.time() - start_time

        print(f"  두 번째 실행 (캐시 히트): {second_duration:.2f}초")

        # 성능 개선 계산
        improvement = ((first_duration - second_duration) / first_duration) * 100

        return {
            "first_execution_seconds": first_duration,
            "second_execution_seconds": second_duration,
            "performance_improvement_percent": round(improvement, 1),
            "cache_effectiveness": (
                "excellent"
                if improvement > 80
                else "good" if improvement > 50 else "moderate"
            ),
        }

    def test_dataframe_optimization(self) -> Dict[str, Any]:
        """DataFrame 메모리 최적화 테스트"""
        print("\n🧪 DataFrame 메모리 최적화 테스트 시작")

        # 최적화 전 DataFrame 생성
        original_df = pd.DataFrame(
            {
                "symbol": np.random.choice(["AAPL", "GOOGL", "MSFT"], 10000),
                "price": np.random.uniform(50.0, 500.0, 10000).astype(np.float64),
                "volume": np.random.randint(1000, 1000000, 10000).astype(np.int64),
                "change": np.random.uniform(-10.0, 10.0, 10000).astype(np.float64),
            }
        )

        original_memory = original_df.memory_usage(deep=True).sum()

        # 최적화 실행
        optimized_df = MemoryOptimizer.optimize_dataframe(original_df)
        optimized_memory = optimized_df.memory_usage(deep=True).sum()

        memory_saved = original_memory - optimized_memory
        reduction_percent = (memory_saved / original_memory) * 100

        print(f"  원본 메모리: {original_memory / 1024 / 1024:.2f} MB")
        print(f"  최적화 후: {optimized_memory / 1024 / 1024:.2f} MB")
        print(
            f"  절약된 메모리: {memory_saved / 1024 / 1024:.2f} MB ({reduction_percent:.1f}%)"
        )

        return {
            "original_memory_mb": round(original_memory / 1024 / 1024, 2),
            "optimized_memory_mb": round(optimized_memory / 1024 / 1024, 2),
            "memory_saved_mb": round(memory_saved / 1024 / 1024, 2),
            "reduction_percent": round(reduction_percent, 1),
            "optimization_effectiveness": (
                "excellent"
                if reduction_percent > 30
                else "good" if reduction_percent > 15 else "moderate"
            ),
        }

    async def test_integrated_monitoring(
        self, duration_minutes: int = 2
    ) -> Dict[str, Any]:
        """통합 메모리 모니터링 테스트"""
        print(f"\n🧪 통합 메모리 모니터링 테스트 시작 ({duration_minutes}분)")

        # 모니터링 시작
        await integrated_memory_manager.start_monitoring(interval_seconds=30)

        try:
            # 테스트 작업 실행
            for i in range(duration_minutes):
                print(f"  테스트 작업 {i + 1}/{duration_minutes} 실행 중...")

                # 메모리 집약적 작업
                self.memory_intensive_operation(iterations=2)

                # 잠시 대기
                await asyncio.sleep(60)  # 1분 대기

            # 최종 보고서 생성
            final_report = integrated_memory_manager.get_comprehensive_report()

            return {
                "test_duration_minutes": duration_minutes,
                "final_memory_percent": final_report["system_memory"]["percent"],
                "cache_hit_rate": final_report["cache_health"]["average_hit_rate"],
                "recommendations_count": len(final_report["recommendations"]),
                "monitoring_success": True,
            }

        finally:
            # 모니터링 중지
            await integrated_memory_manager.stop_monitoring()

    def run_comprehensive_test(self) -> Dict[str, Any]:
        """종합 테스트 실행"""
        print("🚀 메모리 시스템 종합 테스트 시작\n")

        # 초기 메모리 상태
        initial_status = get_memory_status()
        print(f"초기 메모리 사용률: {initial_status['system_memory']['percent']:.1f}%")

        test_results = {}

        # 1. 캐시 성능 테스트
        test_results["cache_performance"] = self.test_cache_performance()

        # 2. DataFrame 최적화 테스트
        test_results["dataframe_optimization"] = self.test_dataframe_optimization()

        # 3. 메모리 집약적 작업 테스트
        print("\n🧪 메모리 집약적 작업 테스트 시작")
        intensive_results = self.memory_intensive_operation(iterations=3)
        test_results["memory_intensive_operation"] = {
            "iterations_completed": len(intensive_results),
            "total_dataframes_created": len(intensive_results),
            "avg_dataframe_memory_mb": sum(
                r["dataframe_memory_mb"] for r in intensive_results
            )
            / len(intensive_results),
        }

        # 4. 메모리 최적화 실행
        print("\n🧪 시스템 메모리 최적화 테스트")
        optimization_result = optimize_memory(aggressive=False)
        test_results["system_optimization"] = {
            "memory_freed_mb": optimization_result["memory_freed_mb"],
            "optimization_success": optimization_result["success"],
        }

        # 최종 메모리 상태
        final_status = get_memory_status()
        test_results["final_memory_status"] = {
            "memory_percent": final_status["system_memory"]["percent"],
            "available_memory_mb": final_status["system_memory"]["available_mb"],
            "cache_hit_rate": final_status["cache_health"]["average_hit_rate"],
        }

        print(f"\n✅ 종합 테스트 완료!")
        print(f"최종 메모리 사용률: {final_status['system_memory']['percent']:.1f}%")
        print(f"캐시 히트율: {final_status['cache_health']['average_hit_rate']:.1f}%")

        return test_results


def run_memory_system_demo():
    """메모리 시스템 데모 실행"""
    tester = MemorySystemTester()

    print("=" * 60)
    print("🎯 메모리 관리 시스템 데모")
    print("=" * 60)

    # 종합 테스트 실행
    results = tester.run_comprehensive_test()

    # 결과 요약 출력
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)

    print(
        f"🚀 캐시 성능 개선: {results['cache_performance']['performance_improvement_percent']}%"
    )
    print(
        f"💾 DataFrame 메모리 절약: {results['dataframe_optimization']['reduction_percent']}%"
    )
    print(
        f"🔧 시스템 메모리 해제: {results['system_optimization']['memory_freed_mb']} MB"
    )
    print(
        f"📈 최종 캐시 히트율: {results['final_memory_status']['cache_hit_rate']:.1f}%"
    )

    return results


async def run_monitoring_demo():
    """모니터링 시스템 데모 실행"""
    tester = MemorySystemTester()

    print("=" * 60)
    print("📊 메모리 모니터링 시스템 데모")
    print("=" * 60)

    # 모니터링 테스트 실행 (2분간)
    results = await tester.test_integrated_monitoring(duration_minutes=2)

    print("\n" + "=" * 60)
    print("📊 모니터링 결과")
    print("=" * 60)

    print(f"✅ 모니터링 성공: {results['monitoring_success']}")
    print(f"📊 최종 메모리 사용률: {results['final_memory_percent']:.1f}%")
    print(f"🎯 캐시 히트율: {results['cache_hit_rate']:.1f}%")
    print(f"💡 권장사항 수: {results['recommendations_count']}개")

    return results


if __name__ == "__main__":
    # 기본 데모 실행
    demo_results = run_memory_system_demo()

    # 비동기 모니터링 데모 실행 (선택사항)
    print("\n모니터링 데모를 실행하시겠습니까? (y/n): ", end="")
    if input().lower() == "y":
        asyncio.run(run_monitoring_demo())
