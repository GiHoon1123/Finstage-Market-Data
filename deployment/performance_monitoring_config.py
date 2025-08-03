"""
배포 후 성능 모니터링 설정

성능 모니터링 시스템의 설정값들을 관리합니다.
"""

from dataclasses import dataclass
from typing import Dict, List
import os


@dataclass
class MonitoringConfig:
    """모니터링 설정"""

    # 기본 모니터링 설정
    monitoring_interval_seconds: int = 60
    max_history_size: int = 1440  # 24시간 (1분 간격)

    # 성능 임계값
    memory_usage_threshold: float = 80.0
    cpu_usage_threshold: float = 70.0
    response_time_threshold_ms: float = 1000.0
    error_rate_threshold: float = 5.0
    cache_hit_rate_threshold: float = 80.0

    # 자동 튜닝 설정
    auto_tuning_enabled: bool = True
    tuning_cooldown_minutes: int = 30
    performance_degradation_threshold: float = 20.0
    consecutive_poor_performance_limit: int = 5

    # 알림 설정
    alert_enabled: bool = True
    alert_channels: List[str] = None
    critical_alert_threshold: int = 3  # 3회 연속 임계값 초과 시 알림

    # 캐시 설정
    cache_adjustment_enabled: bool = True
    cache_warmup_enabled: bool = True
    emergency_cleanup_enabled: bool = True

    # 로깅 설정
    log_level: str = "INFO"
    performance_log_file: str = "logs/performance_monitoring.log"
    metrics_export_enabled: bool = True
    metrics_export_interval_minutes: int = 5

    def __post_init__(self):
        if self.alert_channels is None:
            self.alert_channels = ["console", "log"]


@dataclass
class OptimizationConfig:
    """최적화 설정"""

    # 메모리 최적화
    memory_optimization_levels: Dict[str, Dict] = None

    # 캐시 최적화
    cache_size_limits: Dict[str, int] = None
    cache_ttl_settings: Dict[str, int] = None

    # 작업 큐 최적화
    task_queue_priorities: Dict[str, int] = None

    def __post_init__(self):
        if self.memory_optimization_levels is None:
            self.memory_optimization_levels = {
                "basic": {
                    "dataframe_optimization": True,
                    "memory_monitoring": True,
                    "garbage_collection": False,
                },
                "aggressive": {
                    "dataframe_optimization": True,
                    "memory_monitoring": True,
                    "garbage_collection": True,
                    "cache_size_reduction": True,
                },
            }

        if self.cache_size_limits is None:
            self.cache_size_limits = {
                "technical_analysis": 1000,
                "price_data": 2000,
                "news_data": 500,
            }

        if self.cache_ttl_settings is None:
            self.cache_ttl_settings = {
                "technical_analysis": 300,  # 5분
                "price_data": 60,  # 1분
                "news_data": 300,  # 5분
            }

        if self.task_queue_priorities is None:
            self.task_queue_priorities = {
                "price_monitoring": 10,
                "technical_analysis": 8,
                "news_crawling": 6,
                "report_generation": 3,
                "batch_analysis": 2,
                "data_cleanup": 1,
            }


class ConfigManager:
    """설정 관리자"""

    def __init__(self):
        self.monitoring_config = self._load_monitoring_config()
        self.optimization_config = self._load_optimization_config()

    def _load_monitoring_config(self) -> MonitoringConfig:
        """모니터링 설정 로드"""
        config = MonitoringConfig()

        # 환경 변수에서 설정 오버라이드
        config.monitoring_interval_seconds = int(
            os.getenv("MONITORING_INTERVAL", config.monitoring_interval_seconds)
        )
        config.auto_tuning_enabled = (
            os.getenv("AUTO_TUNING_ENABLED", "true").lower() == "true"
        )
        config.memory_usage_threshold = float(
            os.getenv("MEMORY_THRESHOLD", config.memory_usage_threshold)
        )
        config.cpu_usage_threshold = float(
            os.getenv("CPU_THRESHOLD", config.cpu_usage_threshold)
        )
        config.response_time_threshold_ms = float(
            os.getenv("RESPONSE_TIME_THRESHOLD", config.response_time_threshold_ms)
        )

        return config

    def _load_optimization_config(self) -> OptimizationConfig:
        """최적화 설정 로드"""
        config = OptimizationConfig()

        # 환경 변수에서 캐시 크기 설정 오버라이드
        for cache_name in config.cache_size_limits.keys():
            env_key = f"CACHE_SIZE_{cache_name.upper()}"
            if os.getenv(env_key):
                config.cache_size_limits[cache_name] = int(os.getenv(env_key))

        return config

    def get_monitoring_config(self) -> MonitoringConfig:
        """모니터링 설정 반환"""
        return self.monitoring_config

    def get_optimization_config(self) -> OptimizationConfig:
        """최적화 설정 반환"""
        return self.optimization_config

    def update_monitoring_config(self, **kwargs):
        """모니터링 설정 업데이트"""
        for key, value in kwargs.items():
            if hasattr(self.monitoring_config, key):
                setattr(self.monitoring_config, key, value)

    def update_optimization_config(self, **kwargs):
        """최적화 설정 업데이트"""
        for key, value in kwargs.items():
            if hasattr(self.optimization_config, key):
                setattr(self.optimization_config, key, value)

    def save_config_to_file(self, filepath: str):
        """설정을 파일로 저장"""
        import json
        from dataclasses import asdict

        config_data = {
            "monitoring": asdict(self.monitoring_config),
            "optimization": asdict(self.optimization_config),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

    def load_config_from_file(self, filepath: str):
        """파일에서 설정 로드"""
        import json

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            # 모니터링 설정 업데이트
            if "monitoring" in config_data:
                for key, value in config_data["monitoring"].items():
                    if hasattr(self.monitoring_config, key):
                        setattr(self.monitoring_config, key, value)

            # 최적화 설정 업데이트
            if "optimization" in config_data:
                for key, value in config_data["optimization"].items():
                    if hasattr(self.optimization_config, key):
                        setattr(self.optimization_config, key, value)

        except Exception as e:
            print(f"설정 파일 로드 실패: {str(e)}")


# 전역 설정 관리자 인스턴스
_config_manager = None


def get_config_manager() -> ConfigManager:
    """설정 관리자 인스턴스 반환"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
