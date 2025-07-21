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

# SQLAlchemy 엔진 생성 - 연결 풀링 최적화
# 성능 개선 Phase 1: 데이터베이스 연결 풀링 최적화
engine = create_engine(
    MYSQL_URL,
    echo=False,  # SQL 쿼리 로깅 비활성화 (성능 향상)
    # === 연결 풀링 설정 (성능 개선의 핵심) ===
    pool_size=20,  # 기본 연결 풀 크기 - 동시 처리 가능한 기본 연결 수
    # 스케줄러 작업들이 병렬로 실행될 때 충분한 연결 확보
    max_overflow=30,  # 추가 연결 허용 수 - 피크 시간대 추가 연결 생성 가능
    # 총 최대 연결 수 = pool_size + max_overflow = 50개
    pool_timeout=30,  # 연결 대기 시간 (초) - 연결 풀이 가득 찰 때 대기 시간
    # 30초 후에도 연결을 얻지 못하면 TimeoutError 발생
    pool_recycle=3600,  # 연결 재사용 시간 (초) - 1시간 후 연결 재생성
    # MySQL의 wait_timeout 설정보다 짧게 설정하여 연결 끊김 방지
    pool_pre_ping=True,  # 연결 유효성 검사 - 사용 전 연결 상태 확인
    # 끊어진 연결 자동 감지 및 재연결로 안정성 향상
)

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
