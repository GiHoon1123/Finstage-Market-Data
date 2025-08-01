#!/usr/bin/env python3
"""
로깅 시스템 테스트 스크립트
"""

import os
import sys

sys.path.append(".")

from app.common.utils.logging_config import setup_logging, get_logger


def test_logging_system():
    """로깅 시스템 테스트"""

    # 환경 설정
    os.environ["ENV_MODE"] = "dev"

    # 로깅 시스템 초기화
    setup_logging()

    # 로거 생성
    logger = get_logger("test")

    # 다양한 로그 레벨 테스트
    logger.debug("debug_message", test_data="debug_value")
    logger.info("info_message", test_data="info_value", count=42)
    logger.warning("warning_message", test_data="warning_value")
    logger.error("error_message", test_data="error_value", error_type="TestError")

    # 뉴스 크롤링 로그 테스트
    logger.info(
        "news_crawling_completed",
        source="test_source",
        symbol="TEST",
        success_count=15,
        total_count=20,
        success_rate=0.75,
        execution_time=2.34,
    )

    # 에러 로그 테스트
    try:
        raise ValueError("테스트 에러입니다")
    except Exception as e:
        logger.error(
            "test_error_occurred",
            function="test_logging_system",
            error_type=type(e).__name__,
            error_message=str(e),
        )

    print("로깅 테스트 완료! logs/ 디렉토리를 확인해보세요.")


if __name__ == "__main__":
    test_logging_system()
