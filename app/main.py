# ENV_MODE=dev uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload
# ENV_MODE=test uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload
# ENV_MODE=prod uvicorn app.main:app --host 0.0.0.0 --port 8081
from fastapi import FastAPI
from app.common.infra.database.config.database_config import Base, engine
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


import os
from dotenv import load_dotenv
from app.scheduler.scheduler_runner import start_scheduler

# 성능 모니터링 관련 import (함수 내부에서 사용)
try:
    from app.common.utils.performance_monitor import stop_monitoring
except ImportError:
    stop_monitoring = None

# 실행환경 지정: export ENV_MODE=prod 처럼 외부에서 주입 가능
mode = os.getenv("ENV_MODE", "dev")
env_file = f".env.{mode}"
load_dotenv(dotenv_path=env_file)


app = FastAPI(
    title="Finstage Market Data API",
    version="1.0.0",
    description="주가 및 재무데이터 수집/제공 서비스",
)

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

# 테스트 라우터 등록
from app.technical_analysis.web.route.test_router import router as test_router

app.include_router(
    test_router,
    prefix="/api/test",
    tags=["Test API"],
)

# 비동기 API 라우터 등록
from app.technical_analysis.web.route.async_api_router import router as async_api_router

app.include_router(
    async_api_router,
    prefix="/api/v2",
    tags=["Async API"],
)


# DB 테이블 생성
Base.metadata.create_all(bind=engine)


@app.on_event("startup")
def startup_event():
    # 병렬 처리 스케줄러 사용
    from app.scheduler.parallel_scheduler import start_parallel_scheduler

    start_parallel_scheduler()  # 서버 시작 시 병렬 스케줄러 동작 시작

    # 성능 모니터링 시스템 시작
    from app.common.utils.performance_monitor import start_monitoring

    start_monitoring()
    print("✅ 성능 모니터링 시스템 시작됨")


@app.on_event("shutdown")
def shutdown_event():
    # 성능 모니터링 시스템 종료
    if stop_monitoring:
        stop_monitoring()
        print("✅ 성능 모니터링 시스템 종료됨")

    # 성능 모니터링 시스템 시작
    from app.common.utils.performance_monitor import start_monitoring

    start_monitoring()


@app.on_event("shutdown")
def shutdown_event():
    # 성능 모니터링 시스템 종료
    from app.common.utils.performance_monitor import stop_monitoring

    stop_monitoring()


@app.on_event("shutdown")
def shutdown_event():
    # 성능 모니터링 시스템 종료
    from app.common.utils.performance_monitor import stop_monitoring

    stop_monitoring()
    print("✅ 성능 모니터링 시스템 종료됨")
