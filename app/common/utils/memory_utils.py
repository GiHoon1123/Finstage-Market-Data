"""
통합 메모리 관리 유틸리티

메모리 캐시와 메모리 옵티마이저를 통합하여 
전체적인 메모리 관리 기능을 제공합니다.
"""

import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.common.utils.memory_cache import (
    cache_manager,
    cache_metrics,
    get_cache_health_report,
    LRUCache,
)
from app.common.utils.memory_optimizer import (
    MemoryOptimizer,
    memory_manager,
    memory_profiler,
)
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class IntegratedMemoryManager:
    """통합 메모리 관리 시스템"""

    def __init__(self):
        self.monitoring_active = False
        self.monitoring_task = None
        self.performance_history = []

    async def start_monitoring(self, interval_seconds: int = 300):
        """메모리 모니터링 시작"""
        if self.monitoring_active:
            logger.warning("memory_monitoring_already_active")
            return

        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )

        logger.info(
            "integrated_memory_monitoring_started", interval_seconds=interval_seconds
        )

    async def stop_monitoring(self):
        """메모리 모니터링 중지"""
        if not self.monitoring_active:
            return

        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("integrated_memory_monitoring_stopped")

    async def _monitoring_loop(self, interval_seconds: int):
        """메모리 모니터링 루프"""
        while self.monitoring_active:
            try:
                # 메모리 상태 확인
                health_report = self.get_comprehensive_report()

                # 성능 기록 저장
                self.performance_history.append(
                    {
                        "timestamp": time.time(),
                        "memory_usage_mb": health_report["system_memory"]["rss_mb"],
                        "memory_percent": health_report["system_memory"]["percent"],
                        "cache_hit_rate": health_report["cache_health"][
                            "average_hit_rate"
                        ],
                        "total_cached_items": health_report["cache_health"][
                            "total_cached_items"
                        ],
                    }
                )

                # 최근 24시간 기록만 유지
                cutoff_time = time.time() - (24 * 3600)
                self.performance_history = [
                    record
                    for record in self.performance_history
                    if record["timestamp"] > cutoff_time
                ]

                # 자동 최적화 조건 확인
                await self._check_auto_optimization(health_report)

                await asyncio.sleep(interval_seconds)

            except Exception as e:
                logger.error("memory_monitoring_loop_error", error=str(e))
                await asyncio.sleep(60)  # 에러 시 1분 후 재시도

    async def _check_auto_optimization(self, health_report: Dict[str, Any]):
        """자동 최적화 조건 확인 및 실행"""
        memory_percent = health_report["system_memory"]["percent"]
        cache_memory_mb = health_report["cache_health"]["total_memory_usage_mb"]

        # 메모리 사용률이 85% 이상이면 최적화 실행
        if memory_percent >= 85:
            logger.warning(
                "auto_optimization_triggered_high_memory", memory_percent=memory_percent
            )

            optimization_result = memory_manager.optimize_system_memory(
                aggressive=False
            )

            # 캐시 메모리가 100MB 이상이면 캐시도 정리
            if cache_memory_mb >= 100:
                expired_count = cache_manager.cleanup_all_expired()
                logger.info(
                    "auto_cache_cleanup_executed",
                    expired_items=sum(expired_count.values()),
                )

        # 캐시 히트율이 30% 미만이면 캐시 전략 재검토 알림
        elif health_report["cache_health"]["average_hit_rate"] < 30:
            logger.warning(
                "low_cache_hit_rate_detected",
                hit_rate=health_report["cache_health"]["average_hit_rate"],
            )

    def get_comprehensive_report(self) -> Dict[str, Any]:
        """종합 메모리 상태 보고서"""
        # 시스템 메모리 상태
        system_memory = MemoryOptimizer.get_memory_usage()
        memory_health = memory_manager.check_memory_health()

        # 캐시 상태
        cache_health = get_cache_health_report()

        # 객체 수 정보
        object_counts = MemoryOptimizer.get_object_counts()

        # 최근 성능 트렌드
        performance_trend = self._calculate_performance_trend()

        return {
            "timestamp": time.time(),
            "system_memory": system_memory,
            "memory_health": memory_health,
            "cache_health": cache_health,
            "object_counts": object_counts,
            "performance_trend": performance_trend,
            "recommendations": self._generate_recommendations(
                system_memory, cache_health, memory_health
            ),
        }

    def _calculate_performance_trend(self) -> Dict[str, Any]:
        """성능 트렌드 계산"""
        if len(self.performance_history) < 2:
            return {"status": "insufficient_data"}

        # 최근 1시간과 이전 1시간 비교
        now = time.time()
        recent_hour = [
            record
            for record in self.performance_history
            if now - record["timestamp"] <= 3600
        ]
        previous_hour = [
            record
            for record in self.performance_history
            if 3600 < now - record["timestamp"] <= 7200
        ]

        if not recent_hour or not previous_hour:
            return {"status": "insufficient_data"}

        # 평균값 계산
        recent_avg_memory = sum(r["memory_percent"] for r in recent_hour) / len(
            recent_hour
        )
        previous_avg_memory = sum(r["memory_percent"] for r in previous_hour) / len(
            previous_hour
        )

        recent_avg_hit_rate = sum(r["cache_hit_rate"] for r in recent_hour) / len(
            recent_hour
        )
        previous_avg_hit_rate = sum(r["cache_hit_rate"] for r in previous_hour) / len(
            previous_hour
        )

        memory_trend = (
            "increasing" if recent_avg_memory > previous_avg_memory else "decreasing"
        )
        cache_trend = (
            "improving" if recent_avg_hit_rate > previous_avg_hit_rate else "declining"
        )

        return {
            "status": "available",
            "memory_trend": memory_trend,
            "memory_change_percent": round(recent_avg_memory - previous_avg_memory, 2),
            "cache_trend": cache_trend,
            "cache_hit_rate_change": round(
                recent_avg_hit_rate - previous_avg_hit_rate, 2
            ),
            "data_points": {
                "recent_hour": len(recent_hour),
                "previous_hour": len(previous_hour),
            },
        }

    def _generate_recommendations(
        self,
        system_memory: Dict[str, Any],
        cache_health: Dict[str, Any],
        memory_health: Dict[str, Any],
    ) -> List[str]:
        """최적화 권장사항 생성"""
        recommendations = []

        # 시스템 메모리 권장사항
        if system_memory["percent"] > 90:
            recommendations.append(
                "🚨 메모리 사용률이 매우 높습니다. 즉시 최적화가 필요합니다."
            )
        elif system_memory["percent"] > 75:
            recommendations.append("⚠️ 메모리 사용률이 높습니다. 최적화를 고려하세요.")

        # 캐시 권장사항
        if cache_health["average_hit_rate"] < 50:
            recommendations.append(
                "📊 캐시 히트율이 낮습니다. 캐시 전략을 재검토하세요."
            )

        if cache_health["total_memory_usage_mb"] > 200:
            recommendations.append(
                "💾 캐시 메모리 사용량이 높습니다. 캐시 크기를 조정하세요."
            )

        # 객체 수 권장사항
        if memory_health["object_counts"]["total_objects"] > 100000:
            recommendations.append(
                "🔧 메모리 내 객체 수가 많습니다. 가비지 컬렉션을 실행하세요."
            )

        # 가용 메모리 권장사항
        if system_memory["available_mb"] < 500:
            recommendations.append(
                "💡 가용 메모리가 부족합니다. 불필요한 프로세스를 종료하세요."
            )

        return recommendations

    def optimize_all(self, aggressive: bool = False) -> Dict[str, Any]:
        """전체 메모리 최적화 실행"""
        start_time = time.time()

        logger.info("comprehensive_memory_optimization_started", aggressive=aggressive)

        # 1. 시스템 메모리 최적화
        system_optimization = memory_manager.optimize_system_memory(
            aggressive=aggressive
        )

        # 2. 캐시 정리
        cache_cleanup = cache_manager.cleanup_all_expired()

        # 3. 최종 상태 확인
        final_report = self.get_comprehensive_report()

        optimization_summary = {
            "timestamp": start_time,
            "execution_time_seconds": round(time.time() - start_time, 2),
            "system_optimization": system_optimization,
            "cache_cleanup": {
                "expired_items_removed": sum(cache_cleanup.values()),
                "details": cache_cleanup,
            },
            "final_state": {
                "memory_usage_mb": final_report["system_memory"]["rss_mb"],
                "memory_percent": final_report["system_memory"]["percent"],
                "cache_hit_rate": final_report["cache_health"]["average_hit_rate"],
            },
            "success": system_optimization["success"],
        }

        logger.info(
            "comprehensive_memory_optimization_completed",
            **{
                k: v
                for k, v in optimization_summary.items()
                if k not in ["system_optimization", "cache_cleanup"]
            }
        )

        return optimization_summary

    def get_performance_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """성능 기록 조회"""
        cutoff_time = time.time() - (hours * 3600)
        return [
            record
            for record in self.performance_history
            if record["timestamp"] > cutoff_time
        ]

    def export_diagnostics(self) -> Dict[str, Any]:
        """진단 정보 내보내기"""
        return {
            "timestamp": time.time(),
            "comprehensive_report": self.get_comprehensive_report(),
            "optimization_history": memory_manager.get_optimization_history(),
            "memory_alerts": memory_manager.get_memory_alerts(),
            "performance_history": self.get_performance_history(hours=6),  # 최근 6시간
            "cache_stats": cache_manager.get_all_stats(),
            "system_info": {
                "monitoring_active": self.monitoring_active,
                "performance_records": len(self.performance_history),
            },
        }


# 전역 통합 메모리 매니저
integrated_memory_manager = IntegratedMemoryManager()


# 편의 함수들
def get_memory_status() -> Dict[str, Any]:
    """현재 메모리 상태 조회"""
    return integrated_memory_manager.get_comprehensive_report()


def optimize_memory(aggressive: bool = False) -> Dict[str, Any]:
    """메모리 최적화 실행"""
    return integrated_memory_manager.optimize_all(aggressive=aggressive)


def start_memory_monitoring(interval_minutes: int = 5):
    """메모리 모니터링 시작"""
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(
            integrated_memory_manager.start_monitoring(interval_minutes * 60)
        )
        logger.info("memory_monitoring_started_via_convenience_function")
    except Exception as e:
        logger.error("memory_monitoring_start_failed", error=str(e))


def get_memory_diagnostics() -> Dict[str, Any]:
    """메모리 진단 정보 조회"""
    return integrated_memory_manager.export_diagnostics()


# 메모리 상태 체크 함수 (API 엔드포인트용)
def check_memory_health() -> Dict[str, Any]:
    """메모리 건강 상태 간단 체크"""
    report = integrated_memory_manager.get_comprehensive_report()

    return {
        "status": report["memory_health"]["health_status"],
        "memory_usage_percent": report["system_memory"]["percent"],
        "available_memory_mb": report["system_memory"]["available_mb"],
        "cache_hit_rate": report["cache_health"]["average_hit_rate"],
        "recommendations_count": len(report["recommendations"]),
        "timestamp": report["timestamp"],
    }
