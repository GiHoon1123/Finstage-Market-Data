from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app import config
from contextlib import contextmanager

# SQLAlchemy 설정
engine = create_engine(config.MYSQL_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 모든 모델이 상속받을 Base 클래스
Base = declarative_base()

# FastAPI에서 의존성으로 사용할 DB 세션 제공 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
