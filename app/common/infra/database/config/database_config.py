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

# SQLAlchemy 엔진 생성 - 연결 풀링 최적화 (QueuePool limit 오류 해결)
# 성능 개선 Phase 1: 데이터베이스 연결 풀링 최적화
engine = create_engine(
    MYSQL_URL,
    echo=False,  # SQL 쿼리 로깅 비활성화 (성능 향상)
    # === 연결 풀링 설정 (성능 개선의 핵심) ===
    pool_size=50,  # 기본 연결 풀 크기 (20 → 50으로 증가)
    # 병렬 작업 증가에 대응하여 기본 연결 수 확대
    max_overflow=50,  # 추가 연결 허용 수 (30 → 50으로 증가)
    # 총 최대 연결 수 = pool_size + max_overflow = 100개
    pool_timeout=60,  # 연결 대기 시간 (30 → 60초로 증가)
    # 연결 풀이 가득 찼을 때 더 오래 대기
    pool_recycle=1800,  # 연결 재사용 시간 (3600 → 1800초로 감소, 30분)
    # 더 자주 연결을 재생성하여 연결 문제 방지
    pool_pre_ping=True,  # 연결 유효성 검사 - 사용 전 연결 상태 확인
    # 끊어진 연결 자동 감지 및 재연결로 안정성 향상
    max_identifier_length=64,  # 식별자 길이 제한 설정
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
