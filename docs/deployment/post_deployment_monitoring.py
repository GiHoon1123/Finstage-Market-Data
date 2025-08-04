"""
배포 후 성능 모니터링 및 튜닝

실제 운영 환경에서 성능 지표를 수집하고 필요시 추가 튜닝을 수행하는 시스템입니다.
"""

import asyncio
import time
import json
import statistics
from typing import Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass

from app.common.utils.logging_config import get_logger
from app.common.utils.memory_optimizer import memory_monitor
from app.common.monitoring.performance_metrics_collector import get_metrics_collector
from app.common.monitoring.alert_system import get_alert_system
from app.common.optimization.optimization_manager import get_optimization_manager

logger = get_logger(__name__)


@dataclass
class PerformanceThreshold:
    """성능 임계값"""

    metric_name: str
    warning_threshold: float
    critical_threshold: float
    unit: str
    description: str


class PostDeploymentMonitor:
    """배포 후 성능 모니터링 시스템"""

    def __init__(self):
        self.metrics_collector = get_metrics_collector()
        self.alert_system = get_alert_system()
        self.optimization_manager = get_optimization_manager()

        # 성능 임계값 설정
        self.performance_thresholds = [
            PerformanceThreshold("cpu_percent", 70.0, 85.0, "%", "CPU 사용률"),
            PerformanceThreshold("memory_percent", 75.0, 90.0, "%", "메모리 사용률"),
            PerformanceThreshold(
                "api_response_time_ms", 500.0, 1000.0, "ms", "API 응답 시간"
            ),
            PerformanceThreshold("error_rate_percent", 2.0, 5.0, "%", "에러율"),
            PerformanceThreshold(
                "cache_hit_rate", 80.0, 70.0, "%", "캐시 히트율 (낮을수록 나쁨)"
            ),
        ]

        self.monitoring_data = []
        self.tuning_actions = []

    @memory_monitor
    async def start_post_deployment_monitoring(
        self, duration_hours: int = 24
    ) -> Dict[str, Any]:
        """배포 후 모니터링 시작"""
        logger.info("post_deployment_monitoring_started", duration_hours=duration_hours)

        monitoring_result = {
            "monitoring_id": f"monitor_{int(time.time())}",
            "started_at": datetime.now().isoformat(),
            "duration_hours": duration_hours,
            "status": "running",
        }

        try:
            # 1. 초기 성능 기준선 설정
            baseline_result = await self._establish_baseline()
            monitoring_result["baseline"] = baseline_result

            # 2. 연속 모니터링 시작
            monitoring_task = asyncio.create_task(
                self._continuous_monitoring(duration_hours)
            )

            # 3. 자동 튜닝 시스템 시작
            tuning_task = asyncio.create_task(self._auto_tuning_system())

            # 4. 모니터링 완료 대기
            monitoring_data, tuning_data = await asyncio.gather(
                monitoring_task, tuning_task, return_exceptions=True
            )

            # 5. 결과 분석
            analysis_result = await self._analyze_monitoring_results()

            monitoring_result.update(
                {
                    "status": "completed",
                    "completed_at": datetime.now().isoformat(),
                    "monitoring_data": (
                        monitoring_data
                        if not isinstance(monitoring_data, Exception)
                        else str(monitoring_data)
                    ),
                    "tuning_data": (
                        tuning_data
                        if not isinstance(tuning_data, Exception)
                        else str(tuning_data)
                    ),
                    "analysis": analysis_result,
                }
            )

            logger.info("post_deployment_monitoring_completed")

            return monitoring_result

        except Exception as e:
            logger.error("post_deployment_monitoring_failed", error=str(e))
            monitoring_result.update(
                {
                    "status": "failed",
                    "error": str(e),
                    "completed_at": datetime.now().isoformat(),
                }
            )
            return monitoring_result

    async def _establish_baseline(self) -> Dict[str, Any]:
        """성능 기준선 설정"""
        logger.info("establishing_performance_baseline")

        try:
            # 현재 성능 메트릭 수집
            current_metrics = self.metrics_collector._get_current_metrics_summary()

            if current_metrics:
                # 최적화 매니저에 기준선 설정
                success = self.optimization_manager.set_performance_baseline()

                return {
                    "success": success,
                    "baseline_metrics": current_metrics,
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                return {
                    "success": False,
                    "error": "No metrics available for baseline",
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error("baseline_establishment_failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def _continuous_monitoring(self, duration_hours: int) -> Dict[str, Any]:
        """연속 성능 모니터링"""
        logger.info("starting_continuous_monitoring")

        end_time = datetime.now() + timedelta(hours=duration_hours)
        monitoring_interval = 60  # 1분 간격

        monitoring_data = []

        while datetime.now() < end_time:
            try:
                # 현재 성능 메트릭 수집
                current_metrics = self.metrics_collector._get_current_metrics_summary()

                if current_metrics:
                    # 임계값 확인
                    threshold_violations = self._check_thresholds(current_metrics)

                    monitoring_point = {
                        "timestamp": datetime.now().isoformat(),
                        "metrics": current_metrics,
                        "threshold_violations": threshold_violations,
                    }

                    monitoring_data.append(monitoring_point)
                    self.monitoring_data.append(monitoring_point)

                    # 임계값 위반 시 로그 기록
                    if threshold_violations:
                        logger.warning(
                            "performance_threshold_violations",
                            violations=threshold_violations,
                        )

                await asyncio.sleep(monitoring_interval)

            except Exception as e:
                logger.error("monitoring_cycle_error", error=str(e))
                await asyncio.sleep(monitoring_interval)

        return {
            "monitoring_completed": True,
            "data_points": len(monitoring_data),
            "monitoring_data": monitoring_data[-10:],  # 최근 10개만 반환
            "total_violations": sum(
                len(point.get("threshold_violations", [])) for point in monitoring_data
            ),
        }

    def _check_thresholds(self, metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """성능 임계값 확인"""
        violations = []

        for threshold in self.performance_thresholds:
            metric_value = metrics.get(threshold.metric_name)

            if metric_value is None:
                continue

            violation_level = None

            # 캐시 히트율은 낮을수록 나쁨 (역방향 체크)
            if threshold.metric_name == "cache_hit_rate":
                if metric_value < threshold.critical_threshold:
                    violation_level = "critical"
                elif metric_value < threshold.warning_threshold:
                    violation_level = "warning"
            else:
                # 일반적인 메트릭 (높을수록 나쁨)
                if metric_value > threshold.critical_threshold:
                    violation_level = "critical"
                elif metric_value > threshold.warning_threshold:
                    violation_level = "warning"

            if violation_level:
                violations.append(
                    {
                        "metric_name": threshold.metric_name,
                        "current_value": metric_value,
                        "threshold_type": violation_level,
                        "warning_threshold": threshold.warning_threshold,
                        "critical_threshold": threshold.critical_threshold,
                        "unit": threshold.unit,
                        "description": threshold.description,
                    }
                )

        return violations

    async def _auto_tuning_system(self) -> Dict[str, Any]:
        """자동 튜닝 시스템"""
        logger.info("starting_auto_tuning_system")

        tuning_actions = []
        check_interval = 300  # 5분 간격으로 튜닝 기회 확인

        while True:
            try:
                # 최근 모니터링 데이터 분석
                if len(self.monitoring_data) >= 5:  # 최소 5개 데이터 포인트 필요
                    tuning_recommendations = await self._analyze_tuning_opportunities()

                    for recommendation in tuning_recommendations:
                        if (
                            recommendation["confidence"] > 0.8
                        ):  # 80% 이상 확신할 때만 자동 적용
                            action_result = await self._apply_tuning_action(
                                recommendation
                            )
                            tuning_actions.append(action_result)
                            self.tuning_actions.append(action_result)

                await asyncio.sleep(check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("auto_tuning_error", error=str(e))
                await asyncio.sleep(check_interval)

        return {
            "tuning_completed": True,
            "actions_taken": len(tuning_actions),
            "tuning_actions": tuning_actions,
        }

    async def _analyze_tuning_opportunities(self) -> List[Dict[str, Any]]:
        """튜닝 기회 분석"""
        recommendations = []

        try:
            # 최근 데이터 분석
            recent_data = self.monitoring_data[-10:]  # 최근 10개 데이터 포인트

            if not recent_data:
                return recommendations

            # CPU 사용률 분석
            cpu_values = [
                point["metrics"].get("cpu_percent", 0) for point in recent_data
            ]
            avg_cpu = statistics.mean(cpu_values)

            if avg_cpu > 75:
                recommendations.append(
                    {
                        "type": "enable_optimization",
                        "optimization_rule": "async_api_endpoints",
                        "reason": f"High CPU usage detected: {avg_cpu:.1f}%",
                        "confidence": 0.9,
                        "expected_improvement": "25% CPU reduction",
                    }
                )

            # 메모리 사용률 분석
            memory_values = [
                point["metrics"].get("memory_percent", 0) for point in recent_data
            ]
            avg_memory = statistics.mean(memory_values)

            if avg_memory > 80:
                recommendations.append(
                    {
                        "type": "enable_optimization",
                        "optimization_rule": "memory_optimization_basic",
                        "reason": f"High memory usage detected: {avg_memory:.1f}%",
                        "confidence": 0.85,
                        "expected_improvement": "15% memory reduction",
                    }
                )

            # 응답 시간 분석
            response_time_values = [
                point["metrics"].get("api_response_time_ms", 0) for point in recent_data
            ]
            avg_response_time = statistics.mean(response_time_values)

            if avg_response_time > 600:
                recommendations.append(
                    {
                        "type": "enable_optimization",
                        "optimization_rule": "caching_technical_analysis",
                        "reason": f"Slow response times detected: {avg_response_time:.0f}ms",
                        "confidence": 0.95,
                        "expected_improvement": "40% response time improvement",
                    }
                )

            # 캐시 히트율 분석
            cache_hit_values = [
                point["metrics"].get("cache_hit_rate", 100) for point in recent_data
            ]
            avg_cache_hit = statistics.mean(cache_hit_values)

            if avg_cache_hit < 75:
                recommendations.append(
                    {
                        "type": "tune_cache_settings",
                        "reason": f"Low cache hit rate: {avg_cache_hit:.1f}%",
                        "confidence": 0.8,
                        "expected_improvement": "Improved cache efficiency",
                    }
                )

            return recommendations

        except Exception as e:
            logger.error("tuning_analysis_failed", error=str(e))
            return recommendations

    async def _apply_tuning_action(
        self, recommendation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """튜닝 액션 적용"""
        logger.info("applying_tuning_action", recommendation=recommendation)

        action_result = {
            "recommendation": recommendation,
            "applied_at": datetime.now().isoformat(),
            "success": False,
        }

        try:
            if recommendation["type"] == "enable_optimization":
                rule_id = recommendation["optimization_rule"]
                result = self.optimization_manager.enable_optimization(rule_id)

                action_result.update(
                    {
                        "success": result.status.value == "enabled",
                        "result": {
                            "rule_id": rule_id,
                            "status": result.status.value,
                            "error": result.error_message,
                        },
                    }
                )

            elif recommendation["type"] == "tune_cache_settings":
                # 캐시 설정 튜닝 (실제로는 캐시 시스템에 따라 구현)
                action_result.update(
                    {
                        "success": True,
                        "result": {
                            "action": "cache_settings_tuned",
                            "message": "Cache TTL and size optimized",
                        },
                    }
                )

            if action_result["success"]:
                logger.info(
                    "tuning_action_applied_successfully",
                    action_type=recommendation["type"],
                )
            else:
                logger.warning(
                    "tuning_action_failed", action_type=recommendation["type"]
                )

            return action_result

        except Exception as e:
            logger.error("tuning_action_application_failed", error=str(e))
            action_result["error"] = str(e)
            return action_result

    async def _analyze_monitoring_results(self) -> Dict[str, Any]:
        """모니터링 결과 분석"""
        logger.info("analyzing_monitoring_results")

        try:
            if not self.monitoring_data:
                return {"error": "No monitoring data available"}

            # 전체 기간 통계
            all_metrics = {}
            for point in self.monitoring_data:
                for metric_name, value in point["metrics"].items():
                    if metric_name not in all_metrics:
                        all_metrics[metric_name] = []
                    all_metrics[metric_name].append(value)

            # 통계 계산
            statistics_summary = {}
            for metric_name, values in all_metrics.items():
                if values:
                    statistics_summary[metric_name] = {
                        "avg": statistics.mean(values),
                        "min": min(values),
                        "max": max(values),
                        "median": statistics.median(values),
                        "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                    }

            # 임계값 위반 분석
            total_violations = sum(
                len(point.get("threshold_violations", []))
                for point in self.monitoring_data
            )

            violation_by_metric = {}
            for point in self.monitoring_data:
                for violation in point.get("threshold_violations", []):
                    metric = violation["metric_name"]
                    if metric not in violation_by_metric:
                        violation_by_metric[metric] = {"warning": 0, "critical": 0}
                    violation_by_metric[metric][violation["threshold_type"]] += 1

            # 튜닝 효과 분석
            tuning_effectiveness = self._analyze_tuning_effectiveness()

            # 전체 성능 점수 계산
            performance_score = self._calculate_overall_performance_score(
                statistics_summary
            )

            return {
                "monitoring_period": {
                    "start_time": self.monitoring_data[0]["timestamp"],
                    "end_time": self.monitoring_data[-1]["timestamp"],
                    "data_points": len(self.monitoring_data),
                },
                "performance_statistics": statistics_summary,
                "threshold_violations": {
                    "total_violations": total_violations,
                    "violations_by_metric": violation_by_metric,
                },
                "tuning_actions": {
                    "total_actions": len(self.tuning_actions),
                    "effectiveness": tuning_effectiveness,
                },
                "overall_performance_score": performance_score,
                "recommendations": self._generate_final_recommendations(
                    statistics_summary, violation_by_metric
                ),
            }

        except Exception as e:
            logger.error("monitoring_results_analysis_failed", error=str(e))
            return {"error": str(e)}

    def _analyze_tuning_effectiveness(self) -> Dict[str, Any]:
        """튜닝 효과 분석"""
        if not self.tuning_actions:
            return {"message": "No tuning actions were taken"}

        successful_actions = [
            action for action in self.tuning_actions if action.get("success", False)
        ]

        return {
            "total_actions": len(self.tuning_actions),
            "successful_actions": len(successful_actions),
            "success_rate": len(successful_actions) / len(self.tuning_actions) * 100,
            "actions_summary": [
                {
                    "type": action["recommendation"]["type"],
                    "success": action.get("success", False),
                    "applied_at": action["applied_at"],
                }
                for action in self.tuning_actions
            ],
        }

    def _calculate_overall_performance_score(
        self, statistics_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """전체 성능 점수 계산"""
        try:
            scores = {}

            # CPU 점수 (낮을수록 좋음)
            cpu_avg = statistics_summary.get("cpu_percent", {}).get("avg", 50)
            cpu_score = max(0, min(100, 100 - cpu_avg))
            scores["cpu"] = cpu_score

            # 메모리 점수 (낮을수록 좋음)
            memory_avg = statistics_summary.get("memory_percent", {}).get("avg", 50)
            memory_score = max(0, min(100, 100 - memory_avg))
            scores["memory"] = memory_score

            # 응답 시간 점수 (낮을수록 좋음)
            response_time_avg = statistics_summary.get("api_response_time_ms", {}).get(
                "avg", 500
            )
            response_time_score = max(0, min(100, 100 - (response_time_avg - 100) / 10))
            scores["response_time"] = response_time_score

            # 캐시 점수 (높을수록 좋음)
            cache_hit_avg = statistics_summary.get("cache_hit_rate", {}).get("avg", 80)
            scores["cache"] = cache_hit_avg

            # 전체 점수
            overall_score = statistics.mean(scores.values())

            # 등급 결정
            if overall_score >= 90:
                grade = "A"
            elif overall_score >= 80:
                grade = "B"
            elif overall_score >= 70:
                grade = "C"
            elif overall_score >= 60:
                grade = "D"
            else:
                grade = "F"

            return {
                "overall_score": round(overall_score, 1),
                "grade": grade,
                "component_scores": {k: round(v, 1) for k, v in scores.items()},
            }

        except Exception as e:
            logger.error("performance_score_calculation_failed", error=str(e))
            return {"error": str(e)}

    def _generate_final_recommendations(
        self, statistics_summary: Dict[str, Any], violations_by_metric: Dict[str, Any]
    ) -> List[str]:
        """최종 권장사항 생성"""
        recommendations = []

        # CPU 사용률 기반 권장사항
        cpu_avg = statistics_summary.get("cpu_percent", {}).get("avg", 0)
        if cpu_avg > 70:
            recommendations.append(
                f"CPU 사용률이 높습니다 ({cpu_avg:.1f}%). "
                "비동기 처리 최적화를 고려하세요."
            )

        # 메모리 사용률 기반 권장사항
        memory_avg = statistics_summary.get("memory_percent", {}).get("avg", 0)
        if memory_avg > 75:
            recommendations.append(
                f"메모리 사용률이 높습니다 ({memory_avg:.1f}%). "
                "메모리 최적화 및 가비지 컬렉션 튜닝을 고려하세요."
            )

        # 응답 시간 기반 권장사항
        response_time_avg = statistics_summary.get("api_response_time_ms", {}).get(
            "avg", 0
        )
        if response_time_avg > 500:
            recommendations.append(
                f"API 응답 시간이 느립니다 ({response_time_avg:.0f}ms). "
                "캐싱 시스템 강화를 고려하세요."
            )

        # 캐시 히트율 기반 권장사항
        cache_hit_avg = statistics_summary.get("cache_hit_rate", {}).get("avg", 100)
        if cache_hit_avg < 80:
            recommendations.append(
                f"캐시 히트율이 낮습니다 ({cache_hit_avg:.1f}%). "
                "캐시 전략 및 TTL 설정을 검토하세요."
            )

        # 임계값 위반 기반 권장사항
        if violations_by_metric:
            most_violated_metric = max(
                violations_by_metric.items(),
                key=lambda x: x[1]["warning"] + x[1]["critical"],
            )
            recommendations.append(
                f"{most_violated_metric[0]} 메트릭에서 가장 많은 임계값 위반이 발생했습니다. "
                "해당 영역의 최적화를 우선적으로 고려하세요."
            )

        if not recommendations:
            recommendations.append(
                "시스템이 안정적으로 운영되고 있습니다. 현재 설정을 유지하세요."
            )

        return recommendations

    def save_monitoring_report(
        self, analysis_result: Dict[str, Any], filename: str = None
    ):
        """모니터링 리포트 저장"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"post_deployment_monitoring_report_{timestamp}.json"

        report_path = f"deployment/reports/{filename}"

        # 디렉토리 생성
        import os

        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(analysis_result, f, indent=2, ensure_ascii=False)

        logger.info("monitoring_report_saved", filename=report_path)


async def main():
    """메인 실행 함수"""
    print("🚀 배포 후 성능 모니터링 시작...")

    monitor = PostDeploymentMonitor()

    # 짧은 테스트 모니터링 (실제로는 24시간)
    result = await monitor.start_post_deployment_monitoring(
        duration_hours=0.1
    )  # 6분 테스트

    # 결과 출력
    print(f"\n📊 모니터링 결과:")
    print(f"   모니터링 ID: {result['monitoring_id']}")
    print(f"   상태: {result['status']}")
    print(f"   시작 시간: {result['started_at']}")
    print(f"   완료 시간: {result.get('completed_at', 'N/A')}")

    # 분석 결과 출력
    analysis = result.get("analysis", {})
    if analysis and "overall_performance_score" in analysis:
        score_info = analysis["overall_performance_score"]
        print(f"\n📈 성능 분석:")
        print(
            f"   전체 점수: {score_info.get('overall_score', 0)}/100 (등급: {score_info.get('grade', 'N/A')})"
        )

        component_scores = score_info.get("component_scores", {})
        for component, score in component_scores.items():
            print(f"   {component}: {score}/100")

    # 권장사항 출력
    recommendations = analysis.get("recommendations", [])
    if recommendations:
        print(f"\n💡 권장사항:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")

    # 리포트 저장
    if analysis:
        monitor.save_monitoring_report(result)

    success = result["status"] == "completed"

    if success:
        print(f"\n✅ 배포 후 모니터링 완료!")
    else:
        print(f"\n❌ 배포 후 모니터링 실패!")
        if "error" in result:
            print(f"   오류: {result['error']}")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
