# ENV_MODE=dev uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload
# ENV_MODE=test uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload
# ENV_MODE=prod uvicorn app.main:app --host 0.0.0.0 --port 8081

import os
from dotenv import load_dotenv

# 실행환경 지정: export ENV_MODE=prod 처럼 외부에서 주입 가능
mode = os.getenv("ENV_MODE", "dev")
env_file = f".env.{mode}"
load_dotenv(dotenv_path=env_file)

from fastapi import FastAPI
from app.common.infra.database.config.database_config import Base, engine
from app.common.utils.logging_config import setup_logging, get_logger
from app.common.config.settings import validate_settings, settings

# 설정 검증 및 로깅 시스템 초기화
validate_settings()
setup_logging()
logger = get_logger("main")

from app.company.web.route.symbol_router import router as symbol_router
from app.company.web.route.financial_router import router as financial_router
from app.news_crawler.web.route.news_test_router import router as news_test_router
from app.message_notification.web.route.message_router import router as message_router
from app.technical_analysis.web.route.pattern_analysis_router import (
    router as pattern_analysis_router,
)
from app.technical_analysis.web.route.signal_analysis_router import (
    router as signal_analysis_router,
)
from app.technical_analysis.web.route.utility_router import router as utility_router
from app.technical_analysis.web.route.advanced_pattern_router import (
    router as advanced_pattern_router,
)
from app.technical_analysis.web.route.outcome_analysis_router import (
    router as outcome_analysis_router,
)
from app.technical_analysis.web.route.daily_report_router import (
    router as daily_report_router,
)

from app.scheduler.scheduler_runner import start_scheduler

# 성능 모니터링 관련 import (함수 내부에서 사용)
try:
    from app.common.utils.performance_monitor import stop_monitoring
except ImportError:
    stop_monitoring = None

# 모니터링 시스템 import
from app.common.monitoring.routes import monitoring_router, metrics_middleware
from app.common.monitoring.metrics import start_metrics_server, stop_metrics_server
from app.common.monitoring.alerts import auto_alert_monitor

# 데이터베이스 최적화 시스템 import
from app.common.infra.database.monitoring.query_monitor import query_monitor
from app.common.infra.database.optimization.connection_pool_manager import (
    initialize_pool_manager,
    monitor_connection_pool,
    ConnectionPoolConfig,
)

# 메모리 관리 시스템 import
from app.common.utils.memory_utils import (
    start_memory_monitoring,
    integrated_memory_manager,
)

app = FastAPI(
    title="Finstage Market Data API",
    version=settings.version,
    description="주가 및 재무데이터 수집/제공 서비스",
    debug=settings.debug,
)

# 모니터링 미들웨어 추가
app.middleware("http")(metrics_middleware)

# 라우터 등록
app.include_router(financial_router, prefix="/api/financials", tags=["Financial"])
app.include_router(symbol_router, prefix="/api/symbols", tags=["Symbol"])
app.include_router(news_test_router, prefix="/test/news", tags=["Test News Crawler"])
app.include_router(message_router, prefix="/api/messages", tags=["Messages"])
app.include_router(
    pattern_analysis_router,
    prefix="/api/technical-analysis/patterns",
    tags=["Pattern Analysis"],
)
app.include_router(
    signal_analysis_router,
    prefix="/api/technical-analysis/signals",
    tags=["Signal Analysis"],
)
app.include_router(
    utility_router,
    prefix="/api/technical-analysis/utils",
    tags=["Technical Analysis Utils"],
)
app.include_router(
    advanced_pattern_router,
    prefix="/api/technical-analysis/advanced",
    tags=["Advanced Pattern Analysis"],
)
app.include_router(
    outcome_analysis_router,
    prefix="/api/technical-analysis/outcomes",
    tags=["Outcome Analysis"],
)
app.include_router(
    daily_report_router,
    prefix="/api/daily-report",
    tags=["Daily Report"],
)

# 테스트 라우터 등록
from app.technical_analysis.web.route.test_router import router as test_router

app.include_router(
    test_router,
    prefix="/api/test",
    tags=["Test API"],
)

# 비동기 API 라우터 등록
from app.technical_analysis.web.route.async_api_router import router as async_api_router
from app.technical_analysis.web.route.async_technical_router import (
    router as async_technical_router,
)

app.include_router(
    async_api_router,
    prefix="/api/v2",
    tags=["Async API"],
)

app.include_router(
    async_technical_router,
    tags=["Async Technical Analysis V2"],
)

# 모니터링 라우터 등록
app.include_router(monitoring_router)

# 데이터베이스 최적화 라우터 등록
from app.common.infra.database.routes import db_router

app.include_router(db_router, prefix="/api")

# 메모리 관리 라우터 등록
from app.common.utils.memory_api_router import router as memory_router

app.include_router(memory_router)

# WebSocket 라우터 등록
from app.common.web.websocket_router import router as websocket_router

app.include_router(websocket_router)

# 작업 큐 라우터 등록
from app.common.web.task_queue_router import router as task_queue_router

app.include_router(task_queue_router)

# DB 테이블 생성
Base.metadata.create_all(bind=engine)


@app.on_event("startup")
async def startup_event():
    # 데이터베이스 최적화 시스템 초기화
    try:
        # 쿼리 모니터링 설정
        query_monitor.setup_monitoring(engine)
        logger.info("database_query_monitoring_enabled")

        # 연결 풀 관리자 초기화
        pool_config = ConnectionPoolConfig(
            min_pool_size=5,
            max_pool_size=20,
            max_overflow=30,
            utilization_threshold_high=0.8,
            utilization_threshold_low=0.3,
        )
        initialize_pool_manager(engine, pool_config)
        logger.info("database_connection_pool_manager_initialized")

    except Exception as e:
        logger.error("database_optimization_setup_failed", error=str(e))

    # 병렬 처리 스케줄러 사용
    from app.scheduler.parallel_scheduler import start_parallel_scheduler

    start_parallel_scheduler()  # 서버 시작 시 병렬 스케줄러 동작 시작

    # 성능 모니터링 시스템 시작
    from app.common.utils.performance_monitor import start_monitoring

    start_monitoring()
    logger.info("performance_monitoring_started")

    # Prometheus 메트릭 서버 시작
    try:
        start_metrics_server(port=8001)
        logger.info("prometheus_metrics_server_started", port=8001)
    except Exception as e:
        logger.error("prometheus_metrics_server_start_failed", error=str(e))

    # 자동 알림 모니터링 시작
    import asyncio

    asyncio.create_task(auto_alert_monitor.start_monitoring())
    logger.info("auto_alert_monitoring_started")

    # 연결 풀 모니터링 시작 (5분마다)
    async def pool_monitoring_task():
        while True:
            try:
                await monitor_connection_pool()
                await asyncio.sleep(300)  # 5분 대기
            except Exception as e:
                logger.error("connection_pool_monitoring_error", error=str(e))
                await asyncio.sleep(300)

    asyncio.create_task(pool_monitoring_task())
    logger.info("database_connection_pool_monitoring_started")

    # 메모리 모니터링 시작 (5분 간격)
    try:
        start_memory_monitoring(interval_minutes=5)
        logger.info("memory_monitoring_started", interval_minutes=5)
    except Exception as e:
        logger.error("memory_monitoring_start_failed", error=str(e))

    # 실시간 가격 스트리밍 시작
    try:
        from app.market_price.service.realtime_price_streamer import (
            realtime_price_streamer,
        )

        # 주요 심볼들만 모니터링 (리소스 절약)
        major_symbols = [
            "^IXIC",
            "^GSPC",
            "^DJI",
            "AAPL",
            "GOOGL",
            "MSFT",
            "TSLA",
            "AMZN",
        ]

        asyncio.create_task(realtime_price_streamer.start_streaming(major_symbols))
        logger.info("realtime_price_streaming_started", symbol_count=len(major_symbols))
    except Exception as e:
        logger.error("realtime_price_streaming_start_failed", error=str(e))

    # 분산 작업 큐 시스템 시작
    try:
        from app.common.utils.task_queue import task_queue

        asyncio.create_task(task_queue.start())
        logger.info("task_queue_system_started", max_workers=task_queue.max_workers)
    except Exception as e:
        logger.error("task_queue_system_start_failed", error=str(e))


@app.on_event("shutdown")
def shutdown_event():
    # 성능 모니터링 시스템 종료
    if stop_monitoring:
        stop_monitoring()
        logger.info("performance_monitoring_stopped")

    # Prometheus 메트릭 서버 종료
    try:
        stop_metrics_server()
        logger.info("prometheus_metrics_server_stopped")
    except Exception as e:
        logger.error("prometheus_metrics_server_stop_failed", error=str(e))

    # 자동 알림 모니터링 종료
    auto_alert_monitor.stop_monitoring()
    logger.info("auto_alert_monitoring_stopped")

    # 메모리 모니터링 종료
    try:
        import asyncio

        asyncio.create_task(integrated_memory_manager.stop_monitoring())
        logger.info("memory_monitoring_stopped")
    except Exception as e:
        logger.error("memory_monitoring_stop_failed", error=str(e))

    # 실시간 가격 스트리밍 종료
    try:
        from app.market_price.service.realtime_price_streamer import (
            realtime_price_streamer,
        )
        import asyncio

        asyncio.create_task(realtime_price_streamer.stop_streaming())
        logger.info("realtime_price_streaming_stopped")
    except Exception as e:
        logger.error("realtime_price_streaming_stop_failed", error=str(e))

    # 분산 작업 큐 시스템 종료
    try:
        from app.common.utils.task_queue import task_queue
        import asyncio

        asyncio.create_task(task_queue.stop())
        logger.info("task_queue_system_stopped")
    except Exception as e:
        logger.error("task_queue_system_stop_failed", error=str(e))
