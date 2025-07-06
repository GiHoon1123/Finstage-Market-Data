from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


# MySQL 접속 설정
MYSQL_USER = "root"
MYSQL_PASSWORD = "1234"
MYSQL_HOST = "localhost"
MYSQL_PORT = "3306"
MYSQL_DB = "finstage_market_data"

# SQLAlchemy용 접속 URL 생성
MYSQL_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

# SQLAlchemy 엔진 생성
engine = create_engine(MYSQL_URL, echo=True)

# 세션 생성기
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 모델 베이스 클래스
Base = declarative_base()

# FastAPI 등에서 의존성 주입용 세션 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
