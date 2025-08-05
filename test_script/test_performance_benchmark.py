"""
성능 벤치마크 테스트

최적화 전후 성능 비교를 위한 벤치마크 테스트입니다.
"""

import asyncio
import time
import statistics
import psutil
import requests
from typing import Dict, Any, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.common.utils.logging_config import get_logger
from app.common.utils.memory_optimizer import memory_monitor

logger = get_logger(__name__)


class PerformanceBenchmark:
    """성능 벤치마크 테스트"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.benchmark_results = {}

    @memory_monitor
    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """모든 벤치마크 테스트 실행"""
        logger.info("performance_benchmark_started")

        benchmarks = [
            ("api_response_time", self.benchmark_api_response_time),
            ("concurrent_requests", self.benchmark_concurrent_requests),
            ("memory_usage", self.benchmark_memory_usage),
            ("cache_performance", self.benchmark_cache_performance),
            ("database_operations", self.benchmark_database_operations),
            ("technical_analysis_speed", self.benchmark_technical_analysis),
            ("websocket_throughput", self.benchmark_websocket_throughput),
            ("background_task_processing", self.benchmark_background_tasks),
        ]

        for benchmark_name, benchmark_func in benchmarks:
            try:
                logger.info(f"running_benchmark", benchmark=benchmark_name)
                start_time = time.time()

                result = await benchmark_func()

                execution_time = time.time() - start_time

                self.benchmark_results[benchmark_name] = {
                    "result": result,
                    "execution_time": execution_time,
                    "timestamp": datetime.now().isoformat(),
                }

                logger.info(
                    f"benchmark_completed",
                    benchmark=benchmark_name,
                    execution_time=execution_time,
                )

            except Exception as e:
                logger.error(
                    f"benchmark_failed", benchmark=benchmark_name, error=str(e)
                )

                self.benchmark_results[benchmark_name] = {
                    "error": str(e),
                    "execution_time": 0,
                    "timestamp": datetime.now().isoformat(),
                }

        # 종합 성능 점수 계산
        performance_score = self._calculate_performance_score()

        return {
            "performance_score": performance_score,
            "benchmark_results": self.benchmark_results,
            "system_info": self._get_system_info(),
            "completed_at": datetime.now().isoformat(),
        }

    async def benchmark_api_response_time(self) -> Dict[str, Any]:
        """API 응답 시간 벤치마크"""
        endpoints = [
            "/health",
            "/api/v2/technical-analysis/indicators",
            "/api/v2/price/current/AAPL",
            "/api/v2/news/latest",
            "/api/v2/performance/dashboard",
        ]

        results = {}

        for endpoint in endpoints:
            response_times = []

            for _ in range(10):  # 각 엔드포인트당 10회 테스트
                start_time = time.time()

                try:
                    if endpoint == "/api/v2/technical-analysis/indicators":
                        response = requests.post(
                            f"{self.base_url}{endpoint}",
                            json={
                                "symbol": "AAPL",
                                "indicators": ["sma"],
                                "period": 20,
                            },
                        )
                    else:
                        response = requests.get(f"{self.base_url}{endpoint}")

                    if response.status_code == 200:
                        response_time = (time.time() - start_time) * 1000  # ms
                        response_times.append(response_time)

                except Exception as e:
                    logger.warning(
                        f"api_request_failed", endpoint=endpoint, error=str(e)
                    )

                await asyncio.sleep(0.1)  # 요청 간 간격

            if response_times:
                results[endpoint] = {
                    "avg_response_time": statistics.mean(response_times),
                    "min_response_time": min(response_times),
                    "max_response_time": max(response_times),
                    "median_response_time": statistics.median(response_times),
                    "std_dev": (
                        statistics.stdev(response_times)
                        if len(response_times) > 1
                        else 0
                    ),
                    "success_rate": len(response_times) / 10 * 100,
                }

        return results

    async def benchmark_concurrent_requests(self) -> Dict[str, Any]:
        """동시 요청 처리 벤치마크"""
        concurrent_levels = [1, 5, 10, 20, 50]
        results = {}

        for concurrent_count in concurrent_levels:
            start_time = time.time()
            successful_requests = 0
            response_times = []

            with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
                futures = []

                for _ in range(concurrent_count):
                    future = executor.submit(self._make_test_request)
                    futures.append(future)

                for future in as_completed(futures):
                    try:
                        response_time = future.result()
                        if response_time is not None:
                            successful_requests += 1
                            response_times.append(response_time)
                    except Exception as e:
                        logger.warning("concurrent_request_failed", error=str(e))

            total_time = time.time() - start_time

            results[f"concurrent_{concurrent_count}"] = {
                "total_requests": concurrent_count,
                "successful_requests": successful_requests,
                "success_rate": (successful_requests / concurrent_count) * 100,
                "total_time": total_time,
                "requests_per_second": (
                    successful_requests / total_time if total_time > 0 else 0
                ),
                "avg_response_time": (
                    statistics.mean(response_times) if response_times else 0
                ),
            }

        return results

    def _make_test_request(self) -> float:
        """테스트 요청 실행"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/health")

            if response.status_code == 200:
                return (time.time() - start_time) * 1000  # ms
            else:
                return None
        except:
            return None

    async def benchmark_memory_usage(self) -> Dict[str, Any]:
        """메모리 사용량 벤치마크"""
        # 초기 메모리 상태
        initial_memory = psutil.virtual_memory()
        process = psutil.Process()
        initial_process_memory = process.memory_info()

        # 메모리 집약적 작업 실행
        memory_samples = []

        for i in range(10):
            # 기술적 분석 요청 (메모리 사용량이 높은 작업)
            try:
                response = requests.post(
                    f"{self.base_url}/api/v2/technical-analysis/indicators",
                    json={
                        "symbol": "AAPL",
                        "indicators": ["sma", "rsi", "macd", "bollinger"],
                        "period": 50,
                    },
                )

                # 메모리 사용량 측정
                current_memory = process.memory_info()
                memory_samples.append(
                    {
                        "rss": current_memory.rss / 1024 / 1024,  # MB
                        "vms": current_memory.vms / 1024 / 1024,  # MB
                        "timestamp": time.time(),
                    }
                )

            except Exception as e:
                logger.warning("memory_benchmark_request_failed", error=str(e))

            await asyncio.sleep(0.5)

        # 메모리 정리 후 측정
        try:
            requests.post(f"{self.base_url}/api/v2/memory/cleanup")
            await asyncio.sleep(2)
        except:
            pass

        final_memory = process.memory_info()

        return {
            "initial_memory_mb": initial_process_memory.rss / 1024 / 1024,
            "final_memory_mb": final_memory.rss / 1024 / 1024,
            "peak_memory_mb": (
                max(sample["rss"] for sample in memory_samples) if memory_samples else 0
            ),
            "avg_memory_mb": (
                statistics.mean(sample["rss"] for sample in memory_samples)
                if memory_samples
                else 0
            ),
            "memory_samples": memory_samples,
            "system_memory_percent": psutil.virtual_memory().percent,
        }

    async def benchmark_cache_performance(self) -> Dict[str, Any]:
        """캐시 성능 벤치마크"""
        # 캐시 미스 상황 (첫 번째 요청)
        cache_miss_times = []
        cache_hit_times = []

        test_symbol = "AAPL"

        # 캐시 클리어
        try:
            requests.post(f"{self.base_url}/api/v2/cache/clear")
            await asyncio.sleep(1)
        except:
            pass

        # 캐시 미스 테스트 (첫 번째 요청들)
        for _ in range(5):
            start_time = time.time()

            try:
                response = requests.post(
                    f"{self.base_url}/api/v2/technical-analysis/indicators",
                    json={"symbol": test_symbol, "indicators": ["sma"], "period": 20},
                )

                if response.status_code == 200:
                    response_time = (time.time() - start_time) * 1000
                    cache_miss_times.append(response_time)

            except Exception as e:
                logger.warning("cache_miss_test_failed", error=str(e))

            await asyncio.sleep(0.1)

        # 캐시 히트 테스트 (동일한 요청 반복)
        for _ in range(10):
            start_time = time.time()

            try:
                response = requests.post(
                    f"{self.base_url}/api/v2/technical-analysis/indicators",
                    json={"symbol": test_symbol, "indicators": ["sma"], "period": 20},
                )

                if response.status_code == 200:
                    response_time = (time.time() - start_time) * 1000
                    cache_hit_times.append(response_time)

            except Exception as e:
                logger.warning("cache_hit_test_failed", error=str(e))

            await asyncio.sleep(0.1)

        # 캐시 통계 조회
        cache_stats = {}
        try:
            response = requests.get(f"{self.base_url}/api/v2/cache/stats")
            if response.status_code == 200:
                cache_stats = response.json()
        except:
            pass

        return {
            "cache_miss_avg_time": (
                statistics.mean(cache_miss_times) if cache_miss_times else 0
            ),
            "cache_hit_avg_time": (
                statistics.mean(cache_hit_times) if cache_hit_times else 0
            ),
            "cache_improvement_ratio": (
                statistics.mean(cache_miss_times) / statistics.mean(cache_hit_times)
                if cache_miss_times
                and cache_hit_times
                and statistics.mean(cache_hit_times) > 0
                else 0
            ),
            "cache_stats": cache_stats,
        }

    async def benchmark_database_operations(self) -> Dict[str, Any]:
        """데이터베이스 작업 벤치마크"""
        # 가격 데이터 조회 성능
        price_query_times = []

        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]

        for symbol in symbols:
            start_time = time.time()

            try:
                response = requests.get(
                    f"{self.base_url}/api/v2/price/history/{symbol}?days=30"
                )

                if response.status_code == 200:
                    query_time = (time.time() - start_time) * 1000
                    price_query_times.append(query_time)

            except Exception as e:
                logger.warning("db_query_failed", symbol=symbol, error=str(e))

            await asyncio.sleep(0.1)

        # 뉴스 데이터 조회 성능
        news_query_times = []

        for _ in range(5):
            start_time = time.time()

            try:
                response = requests.get(f"{self.base_url}/api/v2/news/latest?limit=50")

                if response.status_code == 200:
                    query_time = (time.time() - start_time) * 1000
                    news_query_times.append(query_time)

            except Exception as e:
                logger.warning("news_query_failed", error=str(e))

            await asyncio.sleep(0.2)

        return {
            "price_query_avg_time": (
                statistics.mean(price_query_times) if price_query_times else 0
            ),
            "price_query_max_time": max(price_query_times) if price_query_times else 0,
            "news_query_avg_time": (
                statistics.mean(news_query_times) if news_query_times else 0
            ),
            "news_query_max_time": max(news_query_times) if news_query_times else 0,
            "total_db_operations": len(price_query_times) + len(news_query_times),
        }

    async def benchmark_technical_analysis(self) -> Dict[str, Any]:
        """기술적 분석 성능 벤치마크"""
        indicators = ["sma", "rsi", "macd", "bollinger", "stochastic"]
        periods = [10, 20, 50]
        symbols = ["AAPL", "GOOGL", "MSFT"]

        analysis_times = []

        for symbol in symbols:
            for period in periods:
                start_time = time.time()

                try:
                    response = requests.post(
                        f"{self.base_url}/api/v2/technical-analysis/indicators",
                        json={
                            "symbol": symbol,
                            "indicators": indicators,
                            "period": period,
                        },
                    )

                    if response.status_code == 200:
                        analysis_time = (time.time() - start_time) * 1000
                        analysis_times.append(analysis_time)

                except Exception as e:
                    logger.warning(
                        "technical_analysis_failed",
                        symbol=symbol,
                        period=period,
                        error=str(e),
                    )

                await asyncio.sleep(0.1)

        return {
            "avg_analysis_time": (
                statistics.mean(analysis_times) if analysis_times else 0
            ),
            "min_analysis_time": min(analysis_times) if analysis_times else 0,
            "max_analysis_time": max(analysis_times) if analysis_times else 0,
            "total_analyses": len(analysis_times),
            "analyses_per_second": (
                len(analysis_times) / (sum(analysis_times) / 1000)
                if analysis_times
                else 0
            ),
        }

    async def benchmark_websocket_throughput(self) -> Dict[str, Any]:
        """WebSocket 처리량 벤치마크"""
        try:
            # WebSocket 연결 상태 확인
            response = requests.get(f"{self.base_url}/api/v2/websocket/status")

            if response.status_code == 200:
                ws_status = response.json()

                return {
                    "websocket_available": True,
                    "active_connections": ws_status.get("active_connections", 0),
                    "total_messages_sent": ws_status.get("total_messages_sent", 0),
                    "avg_message_size": ws_status.get("avg_message_size", 0),
                }
            else:
                return {"websocket_available": False}

        except Exception as e:
            logger.warning("websocket_benchmark_failed", error=str(e))
            return {"websocket_available": False, "error": str(e)}

    async def benchmark_background_tasks(self) -> Dict[str, Any]:
        """백그라운드 작업 처리 벤치마크"""
        try:
            # 작업 큐 상태 확인
            response = requests.get(f"{self.base_url}/api/v2/tasks/status")

            if response.status_code != 200:
                return {"background_tasks_available": False}

            queue_status = response.json()

            # 테스트 작업 제출
            task_submission_times = []

            for i in range(5):
                start_time = time.time()

                try:
                    response = requests.post(
                        f"{self.base_url}/api/v2/tasks/submit",
                        json={
                            "task_type": "benchmark_test",
                            "parameters": {"test_id": i},
                        },
                    )

                    if response.status_code == 200:
                        submission_time = (time.time() - start_time) * 1000
                        task_submission_times.append(submission_time)

                except Exception as e:
                    logger.warning("task_submission_failed", error=str(e))

                await asyncio.sleep(0.1)

            return {
                "background_tasks_available": True,
                "queue_status": queue_status,
                "avg_submission_time": (
                    statistics.mean(task_submission_times)
                    if task_submission_times
                    else 0
                ),
                "successful_submissions": len(task_submission_times),
            }

        except Exception as e:
            logger.warning("background_tasks_benchmark_failed", error=str(e))
            return {"background_tasks_available": False, "error": str(e)}

    def _calculate_performance_score(self) -> Dict[str, Any]:
        """종합 성능 점수 계산"""
        scores = {}

        # API 응답 시간 점수 (낮을수록 좋음)
        api_results = self.benchmark_results.get("api_response_time", {}).get(
            "result", {}
        )
        if api_results:
            avg_response_times = [
                result.get("avg_response_time", 1000) for result in api_results.values()
            ]
            avg_response_time = statistics.mean(avg_response_times)
            # 100ms 이하면 100점, 1000ms 이상이면 0점
            api_score = max(0, min(100, 100 - (avg_response_time - 100) / 9))
            scores["api_response"] = api_score

        # 동시 요청 처리 점수
        concurrent_results = self.benchmark_results.get("concurrent_requests", {}).get(
            "result", {}
        )
        if concurrent_results:
            success_rates = [
                result.get("success_rate", 0) for result in concurrent_results.values()
            ]
            avg_success_rate = statistics.mean(success_rates)
            scores["concurrent_processing"] = avg_success_rate

        # 메모리 효율성 점수
        memory_results = self.benchmark_results.get("memory_usage", {}).get(
            "result", {}
        )
        if memory_results:
            initial_memory = memory_results.get("initial_memory_mb", 0)
            peak_memory = memory_results.get("peak_memory_mb", 0)

            if initial_memory > 0:
                memory_increase_ratio = (peak_memory - initial_memory) / initial_memory
                # 메모리 증가가 50% 이하면 100점, 200% 이상이면 0점
                memory_score = max(
                    0, min(100, 100 - (memory_increase_ratio - 0.5) * 66.67)
                )
                scores["memory_efficiency"] = memory_score

        # 캐시 효율성 점수
        cache_results = self.benchmark_results.get("cache_performance", {}).get(
            "result", {}
        )
        if cache_results:
            improvement_ratio = cache_results.get("cache_improvement_ratio", 1)
            # 2배 이상 개선되면 100점, 개선이 없으면 0점
            cache_score = min(100, max(0, (improvement_ratio - 1) * 50))
            scores["cache_efficiency"] = cache_score

        # 전체 점수 계산
        if scores:
            overall_score = statistics.mean(scores.values())
        else:
            overall_score = 0

        return {
            "overall_score": overall_score,
            "component_scores": scores,
            "grade": self._get_performance_grade(overall_score),
        }

    def _get_performance_grade(self, score: float) -> str:
        """성능 점수를 등급으로 변환"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _get_system_info(self) -> Dict[str, Any]:
        """시스템 정보 수집"""
        return {
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_total_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024,
            "memory_available_gb": psutil.virtual_memory().available
            / 1024
            / 1024
            / 1024,
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage("/").percent,
            "python_version": f"{psutil.version_info}",
            "timestamp": datetime.now().isoformat(),
        }

    def save_results(self, filename: str = None):
        """벤치마크 결과를 파일로 저장"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_benchmark_{timestamp}.json"

        results = {
            "performance_score": self._calculate_performance_score(),
            "benchmark_results": self.benchmark_results,
            "system_info": self._get_system_info(),
            "completed_at": datetime.now().isoformat(),
        }

        import json

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info("benchmark_results_saved", filename=filename)


async def main():
    """메인 실행 함수"""
    print("🚀 성능 벤치마크 시작...")

    benchmark = PerformanceBenchmark()
    results = await benchmark.run_all_benchmarks()

    # 결과 출력
    performance_score = results["performance_score"]
    print(f"\n📊 성능 벤치마크 결과:")
    print(
        f"   전체 점수: {performance_score['overall_score']:.1f}/100 (등급: {performance_score['grade']})"
    )

    if performance_score["component_scores"]:
        print(f"   세부 점수:")
        for component, score in performance_score["component_scores"].items():
            print(f"     - {component}: {score:.1f}/100")

    # 주요 성능 지표 출력
    api_results = (
        results["benchmark_results"].get("api_response_time", {}).get("result", {})
    )
    if api_results:
        avg_times = [r.get("avg_response_time", 0) for r in api_results.values()]
        if avg_times:
            print(f"   평균 API 응답 시간: {statistics.mean(avg_times):.1f}ms")

    memory_results = (
        results["benchmark_results"].get("memory_usage", {}).get("result", {})
    )
    if memory_results:
        print(f"   메모리 사용량: {memory_results.get('avg_memory_mb', 0):.1f}MB")

    # 결과 저장
    benchmark.save_results()

    print(f"\n✅ 성능 벤치마크 완료!")

    return performance_score["overall_score"] >= 70  # 70점 이상이면 통과


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
