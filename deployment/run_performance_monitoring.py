#!/usr/bin/env python3
"""
배포 후 성능 모니터링 실행 스크립트

성능 모니터링 시스템을 쉽게 시작하고 관리할 수 있는 스크립트입니다.
"""

import asyncio
import argparse
import signal
import sys
import os
from datetime import datetime
from typing import Optional

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deployment.post_deployment_performance_monitor import (
    PostDeploymentMonitor,
    PerformanceTuningRecommendations,
)
from deployment.performance_monitoring_config import get_config_manager
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class MonitoringService:
    """모니터링 서비스 관리자"""

    def __init__(self, config_file: Optional[str] = None):
        self.config_manager = get_config_manager()

        # 설정 파일이 제공된 경우 로드
        if config_file and os.path.exists(config_file):
            self.config_manager.load_config_from_file(config_file)

        self.monitoring_config = self.config_manager.get_monitoring_config()
        self.monitor: Optional[PostDeploymentMonitor] = None
        self.is_running = False

    async def start(self):
        """모니터링 서비스 시작"""
        if self.is_running:
            print("⚠️ 모니터링이 이미 실행 중입니다.")
            return

        print("🚀 성능 모니터링 서비스 시작")
        print("=" * 50)
        print(
            f"📊 모니터링 간격: {self.monitoring_config.monitoring_interval_seconds}초"
        )
        print(
            f"🎯 자동 튜닝: {'활성화' if self.monitoring_config.auto_tuning_enabled else '비활성화'}"
        )
        print(
            f"🔔 알림: {'활성화' if self.monitoring_config.alert_enabled else '비활성화'}"
        )
        print("=" * 50)

        try:
            # 모니터 초기화
            self.monitor = PostDeploymentMonitor(
                monitoring_interval=self.monitoring_config.monitoring_interval_seconds
            )

            # 설정 적용
            self.monitor.auto_tuning_enabled = (
                self.monitoring_config.auto_tuning_enabled
            )
            self.monitor.thresholds.memory_usage_percent = (
                self.monitoring_config.memory_usage_threshold
            )
            self.monitor.thresholds.cpu_usage_percent = (
                self.monitoring_config.cpu_usage_threshold
            )
            self.monitor.thresholds.response_time_ms = (
                self.monitoring_config.response_time_threshold_ms
            )
            self.monitor.thresholds.error_rate_percent = (
                self.monitoring_config.error_rate_threshold
            )
            self.monitor.thresholds.cache_hit_rate_percent = (
                self.monitoring_config.cache_hit_rate_threshold
            )

            self.is_running = True

            # 모니터링 시작
            await self.monitor.start_monitoring()

        except Exception as e:
            logger.error("monitoring_service_start_failed", error=str(e))
            print(f"❌ 모니터링 서비스 시작 실패: {str(e)}")
            self.is_running = False

    def stop(self):
        """모니터링 서비스 중지"""
        if not self.is_running or not self.monitor:
            return

        print("\n⏹️ 모니터링 서비스 중지 중...")

        try:
            self.monitor.stop_monitoring()
            self.is_running = False

            # 성능 히스토리 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            history_file = f"logs/performance_history_{timestamp}.json"

            # logs 디렉토리 생성
            os.makedirs("logs", exist_ok=True)

            self.monitor.save_performance_history(history_file)
            print(f"📁 성능 히스토리 저장: {history_file}")

            # 성능 요약 출력
            self._print_final_summary()

        except Exception as e:
            logger.error("monitoring_service_stop_failed", error=str(e))
            print(f"❌ 모니터링 서비스 중지 중 오류: {str(e)}")

    def _print_final_summary(self):
        """최종 성능 요약 출력"""
        if not self.monitor or not self.monitor.performance_history:
            return

        try:
            print("\n" + "=" * 60)
            print("📊 최종 성능 요약")
            print("=" * 60)

            # 성능 요약 정보
            summary = self.monitor.get_performance_summary(hours=24)

            if "error" not in summary:
                print(f"📈 총 측정 횟수: {summary['total_measurements']}")
                print(f"💾 평균 메모리 사용률: {summary['memory_usage']['avg']:.1f}%")
                print(f"🖥️ 평균 CPU 사용률: {summary['cpu_usage']['avg']:.1f}%")
                print(f"⏱️ 평균 응답 시간: {summary['response_time']['avg']:.1f}ms")
                print(f"🎯 평균 캐시 히트율: {summary['cache_hit_rate']['avg']:.1f}%")

                print("\n📊 성능 상태 분포:")
                for status, count in summary["status_distribution"].items():
                    if count > 0:
                        percentage = (count / summary["total_measurements"]) * 100
                        print(f"   {status.upper()}: {count}회 ({percentage:.1f}%)")

            # 튜닝 권장사항
            self._print_tuning_recommendations()

        except Exception as e:
            logger.error("final_summary_failed", error=str(e))

    def _print_tuning_recommendations(self):
        """튜닝 권장사항 출력"""
        try:
            recommender = PerformanceTuningRecommendations()
            recommendations = recommender.generate_recommendations(
                self.monitor.performance_history
            )

            if recommendations:
                print("\n💡 성능 튜닝 권장사항:")
                print("-" * 40)

                for i, rec in enumerate(recommendations, 1):
                    priority_emoji = {
                        "critical": "🔴",
                        "high": "🟠",
                        "medium": "🟡",
                        "low": "🟢",
                    }

                    emoji = priority_emoji.get(rec["priority"], "⚪")
                    print(f"\n{emoji} {i}. {rec['title']} ({rec['priority']} 우선순위)")
                    print(f"   📝 {rec['description']}")
                    print("   💡 권장사항:")
                    for suggestion in rec["recommendations"]:
                        print(f"      • {suggestion}")
            else:
                print("\n✅ 현재 성능 상태가 양호하여 특별한 튜닝이 필요하지 않습니다.")

        except Exception as e:
            logger.error("tuning_recommendations_failed", error=str(e))


def setup_signal_handlers(service: MonitoringService):
    """시그널 핸들러 설정"""

    def signal_handler(signum, frame):
        print(f"\n📡 시그널 {signum} 수신")
        service.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="배포 후 성능 모니터링 시스템")

    parser.add_argument("--config", "-c", type=str, help="설정 파일 경로")

    parser.add_argument(
        "--interval", "-i", type=int, default=60, help="모니터링 간격 (초, 기본값: 60)"
    )

    parser.add_argument(
        "--no-auto-tuning", action="store_true", help="자동 튜닝 비활성화"
    )

    parser.add_argument(
        "--memory-threshold",
        type=float,
        default=80.0,
        help="메모리 사용률 임계값 (%, 기본값: 80)",
    )

    parser.add_argument(
        "--cpu-threshold",
        type=float,
        default=70.0,
        help="CPU 사용률 임계값 (%, 기본값: 70)",
    )

    parser.add_argument(
        "--response-threshold",
        type=float,
        default=1000.0,
        help="응답 시간 임계값 (ms, 기본값: 1000)",
    )

    parser.add_argument("--save-config", type=str, help="현재 설정을 파일로 저장")

    args = parser.parse_args()

    try:
        # 모니터링 서비스 초기화
        service = MonitoringService(config_file=args.config)

        # 명령행 인수로 설정 오버라이드
        service.config_manager.update_monitoring_config(
            monitoring_interval_seconds=args.interval,
            auto_tuning_enabled=not args.no_auto_tuning,
            memory_usage_threshold=args.memory_threshold,
            cpu_usage_threshold=args.cpu_threshold,
            response_time_threshold_ms=args.response_threshold,
        )

        # 설정 저장 (요청된 경우)
        if args.save_config:
            service.config_manager.save_config_to_file(args.save_config)
            print(f"💾 설정 저장 완료: {args.save_config}")
            return

        # 시그널 핸들러 설정
        setup_signal_handlers(service)

        # 모니터링 시작
        asyncio.run(service.start())

    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {str(e)}")
        logger.error("main_execution_failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
