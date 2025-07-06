# uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload
from fastapi import FastAPI
from app.common.infra.database.config.database_config import Base, engine
from app.company.web.route.symbol_router import router as symbol_router
from app.company.web.route.financial_router import router as financial_router




app = FastAPI(
    title="Finstage Market Data API",
    version="1.0.0",
    description="주가 및 재무데이터 수집/제공 서비스"
)

# 라우터 등록
app.include_router(financial_router, prefix="/api/financials", tags=["Financial"])
app.include_router(symbol_router, prefix="/api/symbols", tags=["Symbol"])

# 다른 라우터도 여기에 추가 가능
# app.include_router(symbol_router, prefix="/api/symbols", tags=["Symbol"])

# DB 테이블 생성
Base.metadata.create_all(bind=engine)

