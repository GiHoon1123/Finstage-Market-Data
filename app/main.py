# ENV_MODE=dev uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload
# ENV_MODE=test uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload
# ENV_MODE=prod uvicorn app.main:app --host 0.0.0.0 --port 8081
from fastapi import FastAPI
from app.common.infra.database.config.database_config import Base, engine
from app.company.web.route.symbol_router import router as symbol_router
from app.company.web.route.financial_router import router as financial_router
from app.news_crawler.web.route.news_test_router import router as news_test_router
from app.message_notification.web.route.message_router import router as message_router
from app.technical_analysis.web.route.technical_analysis_router import (
    router as technical_analysis_router,
)


import os
from dotenv import load_dotenv
from app.scheduler.scheduler_runner import start_scheduler

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
    technical_analysis_router,
    prefix="/api/technical-analysis",
    tags=["Technical Analysis"],
)  # 🆕 기술적 분석 API


# DB 테이블 생성
Base.metadata.create_all(bind=engine)


@app.on_event("startup")
def startup_event():
    start_scheduler()  # 서버 시작 시 스케줄러 동작 시작
