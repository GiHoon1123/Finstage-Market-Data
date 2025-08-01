"""
로깅 시스템 설정

structlog 기반의 구조화된 로깅 시스템
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any
import structlog
from datetime import datetime


class LoggingConfig:
    """로깅 설정 관리 클래스"""

    def __init__(self):
        from app.common.config.settings import settings

        self.settings = settings
        self.environment = settings.environment
        self.log_level = self._get_log_level()
        self.log_dir = Path(settings.logging.file_path).parent
        self.log_dir.mkdir(exist_ok=True)

    def _get_log_level(self) -> int:
        """환경별 로그 레벨 반환"""
        level_map = {
            "development": logging.DEBUG,
            "test": logging.INFO,
            "production": logging.WARNING,
        }

        # 설정에서 직접 지정된 경우 우선 적용
        if hasattr(self, "settings"):
            return getattr(logging, self.settings.logging.level, logging.INFO)

        return level_map.get(self.environment, logging.INFO)

    def configure_logging(self) -> None:
        """로깅 시스템 초기화"""

        # 기존 로거 설정 초기화
        logging.root.handlers = []

        # structlog 설정
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                self._add_common_context,
                (
                    structlog.processors.JSONRenderer()
                    if self.environment == "prod"
                    else structlog.dev.ConsoleRenderer(colors=True)
                ),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(self.log_level),
            logger_factory=structlog.WriteLoggerFactory(),
            cache_logger_on_first_use=True,
        )

        # 파일 핸들러 설정
        if self.environment in ["test", "prod"]:
            self._setup_file_handlers()

        # 콘솔 핸들러 설정 (개발환경)
        if self.environment == "dev":
            self._setup_console_handler()

    def _add_common_context(self, logger, method_name, event_dict):
        """모든 로그에 공통 컨텍스트 추가"""
        event_dict["service"] = "finstage-market-data"
        event_dict["environment"] = self.environment
        event_dict["timestamp"] = datetime.utcnow().isoformat()
        return event_dict

    def _setup_file_handlers(self) -> None:
        """파일 핸들러 설정"""

        # 일반 로그 파일
        app_handler = logging.handlers.RotatingFileHandler(
            filename=self.log_dir / "app.log",
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=10,
            encoding="utf-8",
        )
        app_handler.setLevel(self.log_level)

        # 에러 전용 로그 파일
        error_handler = logging.handlers.RotatingFileHandler(
            filename=self.log_dir / "error.log",
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=5,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)

        # 포맷터 설정
        if self.environment == "prod":
            formatter = logging.Formatter("%(message)s")
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

        app_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)

        # 루트 로거에 핸들러 추가
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        root_logger.addHandler(app_handler)
        root_logger.addHandler(error_handler)

    def _setup_console_handler(self) -> None:
        """콘솔 핸들러 설정 (개발환경용)"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        root_logger.addHandler(console_handler)


def get_logger(name: str) -> structlog.BoundLogger:
    """구조화된 로거 인스턴스 반환"""
    return structlog.get_logger(name)


def setup_logging() -> None:
    """로깅 시스템 초기화 (애플리케이션 시작 시 호출)"""
    config = LoggingConfig()
    config.configure_logging()

    # 초기화 완료 로그
    logger = get_logger("logging_config")
    logger.info(
        "logging_system_initialized",
        environment=config.environment,
        log_level=logging.getLevelName(config.log_level),
        log_dir=str(config.log_dir),
    )


# 편의 함수들
def log_news_crawling(
    source: str,
    symbol: str,
    success_count: int,
    total_count: int,
    execution_time: float,
):
    """뉴스 크롤링 로그"""
    logger = get_logger("news_crawler")
    logger.info(
        "news_crawling_completed",
        source=source,
        symbol=symbol,
        success_count=success_count,
        total_count=total_count,
        success_rate=success_count / total_count if total_count > 0 else 0,
        execution_time=execution_time,
    )


def log_analysis_result(
    symbol: str, strategy: str, signal_type: str, confidence: float
):
    """기술적 분석 결과 로그"""
    logger = get_logger("technical_analysis")
    logger.info(
        "analysis_completed",
        symbol=symbol,
        strategy=strategy,
        signal_type=signal_type,
        confidence=confidence,
    )


def log_error(module: str, function: str, error: Exception, **context):
    """에러 로그"""
    logger = get_logger(module)
    logger.error(
        "error_occurred",
        function=function,
        error_type=type(error).__name__,
        error_message=str(error),
        **context
    )


def log_performance(function_name: str, execution_time: float, **context):
    """성능 로그"""
    logger = get_logger("performance")
    logger.debug(
        "performance_measured",
        function=function_name,
        execution_time=execution_time,
        **context
    )
