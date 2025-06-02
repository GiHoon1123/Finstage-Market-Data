# uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload
from fastapi import FastAPI
from app.routes import financial_router, symbol_router 
from app.infra.db.db import Base, engine
from app.models import *  # company 포함되도록 __init__.py 구성되어 있어야 함
import threading
from app.infra.kafka.consumer import consume_financial_requests

app = FastAPI(
    title="Finstage Market Data API",
    version="1.0.0",
    description="주가 및 재무데이터 수집/제공 서비스"
)

# 라우터 등록
app.include_router(financial_router.router)
app.include_router(symbol_router.router)  # ← 회사 목록 라우터 등록

# DB 테이블 생성
Base.metadata.create_all(bind=engine)

# Kafka Consumer 자동 실행 (백그라운드 스레드)
@app.on_event("startup")
def start_kafka_consumer():
    thread = threading.Thread(target=consume_financial_requests)
    thread.daemon = True
    thread.start()
