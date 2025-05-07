from fastapi import FastAPI
from app.routes import financial_router
from app.infra.db.db import Base, engine
from app.models import *  # __init__.py가 잘 되어 있어야 함

app = FastAPI(
    title="Finstage Market Data API",
    version="1.0.0",
    description="주가 및 재무데이터 수집/제공 서비스"
)

# 라우터 등록
app.include_router(financial_router.router)

# ✅ DB 테이블 생성
Base.metadata.create_all(bind=engine)