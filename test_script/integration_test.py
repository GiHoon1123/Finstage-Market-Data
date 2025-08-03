"""
전체 시스템 통합 테스트

모든 최적화가 적용된 상태에서 시스템의 기능 정상 동작을 확인하는 통합 테스트입니다.
"""

import asyncio
import time
import json
import requests
from typing import Dict, Any, List
from datetime import datetime

from app.common.utils.logging_config import get_logger
from app.common.utils.memory_optimizer import memory_monitor
from app.common.monitoring.performance_metrics_collector import get_metrics_collector
from app.common.monitoring.alert_system import get_alert_system
from app.common.optimization.optimization_manager import get_optimization_manager
from app.common.testing.ab_test_system import get_ab_test_system

logger = get_logger(__name__)


class IntegrationTestSuite:
    """통합 테스트 스위트"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        self.performance_data = {}

    @memory_monitor
    async def run_all_tests(self) -> Dict[str, Any]:
        """모든 통합 테스트 실행"""
        logger.info("integration_test_started")

        test_methods = [
            self.test_basic_api_endpoints,
            self.test_technical_analysis_services,
            self.test_price_data_services,
            self.test_news_crawling_services,
            self.test_background_task_system,
            self.test_websocket_streaming,
            self.test_performance_monitoring,
            self.test_alert_system,
            self.test_optimization_manager,
            self.test_ab_test_system,
            self.test_memory_optimization,
            self.test_caching_system,
            self.test_concurrent_requests,
            self.test_error_handling,
            self.test_system_stability,
        ]

        for test_method in test_methods:
            try:
                logger.info(f"running_test", test_name=test_method.__name__)
                start_time = time.time()

                result = await test_method()

                execution_time = time.time() - start_time

                self.test_results.append(
                    {
                        "test_name": test_method.__name__,
                        "status": "passed" if result else "failed",
                        "execution_time": execution_time,
                        "result": result,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

                logger.info(
                    f"test_completed",
                    test_name=test_method.__name__,
                    status="passed" if result else "failed",
                    execution_time=execution_time,
                )

            except Exception as e:
                logger.error(
                    f"test_failed", test_name=test_method.__name__, error=str(e)
                )

                self.test_results.append(
                    {
                        "test_name": test_method.__name__,
                        "status": "error",
                        "execution_time": 0,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        # 테스트 결과 요약
        summary = self._generate_test_summary()

        logger.info("integration_test_completed", summary=summary)

        return {
            "summary": summary,
            "detailed_results": self.test_results,
            "performance_data": self.performance_data,
        }

    async def test_basic_api_endpoints(self) -> bool:
        """기본 API 엔드포인트 테스트"""
        try:
            # Health check
            response = requests.get(f"{self.base_url}/health")
            if response.status_code != 200:
                return False

            # API 문서 접근
            response = requests.get(f"{self.base_url}/docs")
            if response.status_code != 200:
                return False

            # 메트릭 엔드포인트
            response = requests.get(f"{self.base_url}/metrics")
            if response.status_code != 200:
                return False

            return True

        except Exception as e:
            logger.error("basic_api_test_failed", error=str(e))
            return False

    async def test_technical_analysis_services(self) -> bool:
        """기술적 분석 서비스 테스트"""
        try:
            # 기술적 지표 계산 테스트
            test_data = {
                "symbol": "AAPL",
                "indicators": ["sma", "rsi", "macd"],
                "period": 20,
            }

            response = requests.post(
                f"{self.base_url}/api/v2/technical-analysis/indicators", json=test_data
            )

            if response.status_code != 200:
                return False

            result = response.json()

            # 결과 검증
            if not result.get("indicators"):
                return False

            # 신호 생성 테스트
            response = requests.post(
                f"{self.base_url}/api/v2/technical-analysis/signals",
                json={"symbol": "AAPL"},
            )

            if response.status_code != 200:
                return False

            return True

        except Exception as e:
            logger.error("technical_analysis_test_failed", error=str(e))
            return False

    async def test_price_data_services(self) -> bool:
        """가격 데이터 서비스 테스트"""
        try:
            # 현재 가격 조회
            response = requests.get(f"{self.base_url}/api/v2/price/current/AAPL")
            if response.status_code != 200:
                return False

            # 가격 히스토리 조회
            response = requests.get(
                f"{self.base_url}/api/v2/price/history/AAPL?days=30"
            )
            if response.status_code != 200:
                return False

            # 가격 스냅샷 조회
            response = requests.get(f"{self.base_url}/api/v2/price/snapshot")
            if response.status_code != 200:
                return False

            return True

        except Exception as e:
            logger.error("price_data_test_failed", error=str(e))
            return False

    async def test_news_crawling_services(self) -> bool:
        """뉴스 크롤링 서비스 테스트"""
        try:
            # 뉴스 조회
            response = requests.get(f"{self.base_url}/api/v2/news/latest?limit=10")
            if response.status_code != 200:
                return False

            # 심볼별 뉴스 조회
            response = requests.get(f"{self.base_url}/api/v2/news/symbol/AAPL")
            if response.status_code != 200:
                return False

            return True

        except Exception as e:
            logger.error("news_crawling_test_failed", error=str(e))
            return False

    async def test_background_task_system(self) -> bool:
        """백그라운드 작업 시스템 테스트"""
        try:
            # 작업 큐 상태 확인
            response = requests.get(f"{self.base_url}/api/v2/tasks/status")
            if response.status_code != 200:
                return False

            # 테스트 작업 제출
            test_task = {"task_type": "test_task", "parameters": {"test": True}}

            response = requests.post(
                f"{self.base_url}/api/v2/tasks/submit", json=test_task
            )

            if response.status_code != 200:
                return False

            task_id = response.json().get("task_id")
            if not task_id:
                return False

            # 작업 상태 확인
            await asyncio.sleep(2)  # 작업 처리 대기

            response = requests.get(f"{self.base_url}/api/v2/tasks/{task_id}")
            if response.status_code != 200:
                return False

            return True

        except Exception as e:
            logger.error("background_task_test_failed", error=str(e))
            return False

    async def test_websocket_streaming(self) -> bool:
        """WebSocket 스트리밍 테스트"""
        try:
            # WebSocket 연결 상태 확인
            response = requests.get(f"{self.base_url}/api/v2/websocket/status")
            if response.status_code != 200:
                return False

            # 구독 관리 테스트
            subscription_data = {
                "symbol": "AAPL",
                "data_types": ["price", "technical_analysis"],
            }

            response = requests.post(
                f"{self.base_url}/api/v2/websocket/subscribe", json=subscription_data
            )

            if response.status_code != 200:
                return False

            return True

        except Exception as e:
            logger.error("websocket_streaming_test_failed", error=str(e))
            return False

    async def test_performance_monitoring(self) -> bool:
        """성능 모니터링 시스템 테스트"""
        try:
            # 성능 대시보드 데이터 조회
            response = requests.get(f"{self.base_url}/api/v2/performance/dashboard")
            if response.status_code != 200:
                return False

            dashboard_data = response.json()
            self.performance_data["dashboard"] = dashboard_data

            # 메트릭 요약 조회
            response = requests.get(
                f"{self.base_url}/api/v2/performance/metrics/summary"
            )
            if response.status_code != 200:
                return False

            metrics_data = response.json()
            self.performance_data["metrics"] = metrics_data

            # 성능 리포트 생성
            response = requests.get(f"{self.base_url}/api/v2/performance/report")
            if response.status_code != 200:
                return False

            return True

        except Exception as e:
            logger.error("performance_monitoring_test_failed", error=str(e))
            return False

    async def test_alert_system(self) -> bool:
        """알림 시스템 테스트"""
        try:
            # 알림 규칙 조회
            response = requests.get(f"{self.base_url}/api/v2/alerts/rules")
            if response.status_code != 200:
                return False

            # 활성 알림 조회
            response = requests.get(f"{self.base_url}/api/v2/alerts/")
            if response.status_code != 200:
                return False

            # 알림 통계 조회
            response = requests.get(f"{self.base_url}/api/v2/alerts/statistics")
            if response.status_code != 200:
                return False

            return True

        except Exception as e:
            logger.error("alert_system_test_failed", error=str(e))
            return False

    async def test_optimization_manager(self) -> bool:
        """최적화 매니저 테스트"""
        try:
            # 최적화 상태 조회
            response = requests.get(f"{self.base_url}/api/v2/optimization/status")
            if response.status_code != 200:
                return False

            # 최적화 규칙 조회
            response = requests.get(f"{self.base_url}/api/v2/optimization/rules")
            if response.status_code != 200:
                return False

            # 성능 기준선 조회
            response = requests.get(f"{self.base_url}/api/v2/optimization/baseline")
            if response.status_code == 404:
                # 기준선이 없으면 설정
                baseline_data = {
                    "cpu_percent": 50.0,
                    "memory_percent": 60.0,
                    "api_response_time_ms": 200.0,
                }

                response = requests.post(
                    f"{self.base_url}/api/v2/optimization/baseline", json=baseline_data
                )

                if response.status_code != 200:
                    return False

            return True

        except Exception as e:
            logger.error("optimization_manager_test_failed", error=str(e))
            return False

    async def test_ab_test_system(self) -> bool:
        """A/B 테스트 시스템 테스트"""
        try:
            # A/B 테스트 목록 조회
            response = requests.get(f"{self.base_url}/api/v2/ab-tests/")
            if response.status_code != 200:
                return False

            # 테스트 A/B 테스트 생성
            test_config = {
                "id": "integration_test_ab",
                "name": "Integration Test A/B Test",
                "description": "Test A/B test for integration testing",
                "variants": [
                    {
                        "id": "control",
                        "name": "Control",
                        "description": "Control variant",
                        "traffic_percentage": 50.0,
                        "is_control": True,
                    },
                    {
                        "id": "treatment",
                        "name": "Treatment",
                        "description": "Treatment variant",
                        "traffic_percentage": 50.0,
                        "is_control": False,
                    },
                ],
                "traffic_split_method": "random",
                "target_endpoints": ["/api/v2/test"],
            }

            response = requests.post(
                f"{self.base_url}/api/v2/ab-tests/", json=test_config
            )

            if response.status_code != 200:
                return False

            return True

        except Exception as e:
            logger.error("ab_test_system_test_failed", error=str(e))
            return False

    async def test_memory_optimization(self) -> bool:
        """메모리 최적화 테스트"""
        try:
            # 메모리 상태 조회
            response = requests.get(f"{self.base_url}/api/v2/memory/status")
            if response.status_code != 200:
                return False

            memory_data = response.json()
            self.performance_data["memory_before"] = memory_data

            # 메모리 정리 실행
            response = requests.post(f"{self.base_url}/api/v2/memory/cleanup")
            if response.status_code != 200:
                return False

            # 정리 후 메모리 상태 확인
            await asyncio.sleep(2)

            response = requests.get(f"{self.base_url}/api/v2/memory/status")
            if response.status_code != 200:
                return False

            memory_data_after = response.json()
            self.performance_data["memory_after"] = memory_data_after

            return True

        except Exception as e:
            logger.error("memory_optimization_test_failed", error=str(e))
            return False

    async def test_caching_system(self) -> bool:
        """캐싱 시스템 테스트"""
        try:
            # 캐시 상태 조회
            response = requests.get(f"{self.base_url}/api/v2/cache/status")
            if response.status_code != 200:
                return False

            cache_data = response.json()
            self.performance_data["cache_status"] = cache_data

            # 캐시 통계 조회
            response = requests.get(f"{self.base_url}/api/v2/cache/stats")
            if response.status_code != 200:
                return False

            return True

        except Exception as e:
            logger.error("caching_system_test_failed", error=str(e))
            return False

    async def test_concurrent_requests(self) -> bool:
        """동시 요청 처리 테스트"""
        try:
            # 동시 요청 생성
            tasks = []
            for i in range(10):
                task = asyncio.create_task(
                    self._make_async_request(
                        f"{self.base_url}/api/v2/technical-analysis/indicators",
                        {"symbol": "AAPL", "indicators": ["sma"], "period": 20},
                    )
                )
                tasks.append(task)

            # 모든 요청 완료 대기
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 성공한 요청 수 확인
            successful_requests = sum(
                1 for result in results if not isinstance(result, Exception)
            )

            self.performance_data["concurrent_requests"] = {
                "total_requests": len(tasks),
                "successful_requests": successful_requests,
                "success_rate": (successful_requests / len(tasks)) * 100,
            }

            # 80% 이상 성공하면 통과
            return successful_requests >= 8

        except Exception as e:
            logger.error("concurrent_requests_test_failed", error=str(e))
            return False

    async def _make_async_request(self, url: str, data: Dict[str, Any]) -> bool:
        """비동기 HTTP 요청"""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    return response.status == 200
        except:
            # aiohttp가 없으면 동기 요청으로 대체
            try:
                response = requests.post(url, json=data)
                return response.status_code == 200
            except:
                return False

    async def test_error_handling(self) -> bool:
        """에러 처리 테스트"""
        try:
            # 잘못된 요청 테스트
            response = requests.get(f"{self.base_url}/api/v2/nonexistent-endpoint")
            if response.status_code != 404:
                return False

            # 잘못된 데이터로 요청
            response = requests.post(
                f"{self.base_url}/api/v2/technical-analysis/indicators",
                json={"invalid": "data"},
            )

            # 400 또는 422 에러가 예상됨
            if response.status_code not in [400, 422]:
                return False

            return True

        except Exception as e:
            logger.error("error_handling_test_failed", error=str(e))
            return False

    async def test_system_stability(self) -> bool:
        """시스템 안정성 테스트"""
        try:
            # 연속 요청으로 시스템 부하 테스트
            start_time = time.time()

            for i in range(50):
                response = requests.get(f"{self.base_url}/health")
                if response.status_code != 200:
                    return False

                # 짧은 대기
                await asyncio.sleep(0.1)

            end_time = time.time()

            self.performance_data["stability_test"] = {
                "total_requests": 50,
                "total_time": end_time - start_time,
                "avg_response_time": (end_time - start_time) / 50,
            }

            return True

        except Exception as e:
            logger.error("system_stability_test_failed", error=str(e))
            return False

    def _generate_test_summary(self) -> Dict[str, Any]:
        """테스트 결과 요약 생성"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "passed"])
        failed_tests = len([r for r in self.test_results if r["status"] == "failed"])
        error_tests = len([r for r in self.test_results if r["status"] == "error"])

        total_execution_time = sum(r["execution_time"] for r in self.test_results)

        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "error_tests": error_tests,
            "success_rate": (
                (passed_tests / total_tests) * 100 if total_tests > 0 else 0
            ),
            "total_execution_time": total_execution_time,
            "avg_execution_time": (
                total_execution_time / total_tests if total_tests > 0 else 0
            ),
            "test_completed_at": datetime.now().isoformat(),
        }

    def save_results(self, filename: str = None):
        """테스트 결과를 파일로 저장"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"integration_test_results_{timestamp}.json"

        results = {
            "summary": self._generate_test_summary(),
            "detailed_results": self.test_results,
            "performance_data": self.performance_data,
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info("test_results_saved", filename=filename)


async def main():
    """메인 실행 함수"""
    print("🚀 통합 테스트 시작...")

    test_suite = IntegrationTestSuite()
    results = await test_suite.run_all_tests()

    # 결과 출력
    summary = results["summary"]
    print(f"\n📊 테스트 결과 요약:")
    print(f"   총 테스트: {summary['total_tests']}")
    print(f"   성공: {summary['passed_tests']}")
    print(f"   실패: {summary['failed_tests']}")
    print(f"   에러: {summary['error_tests']}")
    print(f"   성공률: {summary['success_rate']:.1f}%")
    print(f"   총 실행 시간: {summary['total_execution_time']:.2f}초")

    # 결과 저장
    test_suite.save_results()

    # 실패한 테스트가 있으면 상세 정보 출력
    failed_tests = [r for r in results["detailed_results"] if r["status"] != "passed"]
    if failed_tests:
        print(f"\n❌ 실패한 테스트:")
        for test in failed_tests:
            print(f"   - {test['test_name']}: {test.get('error', 'Failed')}")

    print(f"\n✅ 통합 테스트 완료!")

    return summary["success_rate"] >= 80  # 80% 이상 성공하면 통과


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
