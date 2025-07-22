from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import MYSQL_URL

# SQLAlchemy 엔진 생성 - 연결 풀링 최적화 (QueuePool limit 오류 해결)
# 성능 개선 Phase 1: 데이터베이스 연결 풀링 최적화
engine = create_engine(
    MYSQL_URL,
    echo=False,  # SQL 쿼리 로깅 비활성화 (성능 향상)
    # === 연결 풀링 설정 (성능 개선의 핵심) ===
    pool_size=20,  # 기본 연결 풀 크기를 다시 줄임 (100 → 20)
    # 너무 많은 연결이 문제일 수 있음
    max_overflow=30,  # 추가 연결 허용 수 (100 → 30으로 감소)
    # 총 최대 연결 수 = pool_size + max_overflow = 50개
    pool_timeout=300,  # 연결 대기 시간 (120 → 300초로 증가)
    # 연결 풀이 가득 찼을 때 더 오래 대기
    pool_recycle=600,  # 연결 재사용 시간 (900 → 600초로 감소, 10분)
    # 더 자주 연결을 재생성하여 연결 문제 방지
    pool_pre_ping=True,  # 연결 유효성 검사 - 사용 전 연결 상태 확인
    # 끊어진 연결 자동 감지 및 재연결로 안정성 향상
    max_identifier_length=64,  # 식별자 길이 제한 설정
    # === 추가 최적화 설정 ===
    connect_args={
        "charset": "utf8mb4",
        "autocommit": False,
        "connect_timeout": 60,  # 연결 타임아웃
        "read_timeout": 60,  # 읽기 타임아웃
        "write_timeout": 60,  # 쓰기 타임아웃
    },
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
