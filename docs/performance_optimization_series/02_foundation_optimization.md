[Finstage Market Data] Python 성능 최적화 시리즈 (2/5) - 기본 시스템 최적화 (Phase 1)

## 개요

첫 번째 포스트에서 분석한 문제점들 중 가장 기본이 되는 인프라 레벨의 문제들을 해결하기 위해 Phase 1 최적화를 진행했다. 데이터베이스 연결 풀링, 스케줄러 병렬화, 세션 관리 개선을 통해 처리 시간을 80% 단축시킨 과정을 공유한다.

## Phase 1 최적화 목표

- **스케줄러 처리 시간**: 50초 → 10초 (80% 단축)
- **데이터베이스 연결 안정성**: 연결 오류 90% 감소
- **세션 관리**: 세션 누수 100% 방지
- **시스템 안정성**: 예측 가능한 성능 확보

## 1. 데이터베이스 연결 풀링 최적화

### 기존 프로세스의 문제점

**동작 방식**

기존에는 기본적인 SQLAlchemy 설정만 사용하여 연결 풀링이 최적화되지 않았다.

```python
# 기존: 기본 설정
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# 매 요청마다 새로운 연결 생성/해제 반복
def get_data():
    session = SessionLocal()
    try:
        result = session.query(Model).all()
        return result
    finally:
        session.close()
```

**발생하던 문제점**

- 연결 생성/해제 오버헤드로 인한 성능 저하
- 동시 요청 시 연결 부족으로 인한 대기 시간 증가
- 연결 끊김 시 자동 복구 기능 없음
- QueuePool limit 오류 빈발

### 리팩토링 후 프로세스

**최적화된 연결 풀링 설정**

연결 풀 크기, 타임아웃, 재사용 정책을 세밀하게 조정하여 안정적인 데이터베이스 연결을 확보했다.

```python
# 개선: 최적화된 연결 풀링
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.common.config.settings import settings

# SQLAlchemy 엔진 생성 - 연결 풀링 최적화
engine = create_engine(
    settings.database.url,
    echo=False,  # SQL 쿼리 로깅 비활성화 (성능 향상)

    # === 연결 풀링 설정 (성능 개선의 핵심) ===
    pool_size=20,           # 기본 연결 풀 크기
    max_overflow=30,        # 추가 연결 허용 수 (총 최대 50개)
    pool_timeout=300,       # 연결 대기 시간 (5분)
    pool_recycle=600,       # 연결 재사용 시간 (10분)
    pool_pre_ping=True,     # 연결 유효성 검사

    # === 추가 최적화 설정 ===
    max_identifier_length=64,  # 식별자 길이 제한
    connect_args={
        "charset": "utf8mb4",
        "autocommit": False,
        "connect_timeout": 60,  # 연결 타임아웃
        "read_timeout": 60,     # 읽기 타임아웃
        "write_timeout": 60,    # 쓰기 타임아웃
    },
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# FastAPI 의존성 주입용 세션 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**핵심 최적화 포인트**

1. **pool_size=20**: 기본 연결 풀 크기를 20개로 설정하여 동시 요청 처리 능력 확보
2. **max_overflow=30**: 피크 시간대 추가 연결 30개까지 허용 (총 최대 50개)
3. **pool_timeout=300**: 연결 풀이 가득 찬 경우 5분까지 대기
4. **pool_recycle=600**: 10분마다 연결을 재생성하여 끊어진 연결 방지
5. **pool_pre_ping=True**: 연결 사용 전 유효성 검사로 안정성 확보

### 성능 개선 결과

**정량적 성과**

- 연결 생성 오버헤드: 60% 감소
- 연결 끊김 오류: 90% 감소 (일일 50건 → 5건)
- 동시 요청 처리 능력: 300% 향상

**시스템 안정성 향상**

- QueuePool limit 오류 해결
- 예측 가능한 연결 관리
- 자동 연결 복구 기능

## 2. 스케줄러 작업 병렬화

### 기존 프로세스의 문제점

**동작 방식**

기존 스케줄러는 모든 심볼을 순차적으로 처리하고 있었다.

```python
# 기존: 순차 처리 방식
def run_news_crawling_job():
    symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]

    for symbol in symbols:
        try:
            crawler = NewsCrawler(symbol)
            result = crawler.process_all()
            print(f"✅ {symbol} 처리 완료")
        except Exception as e:
            print(f"❌ {symbol} 처리 실패: {e}")

        time.sleep(5.0)  # API 제한을 위한 고정 지연

    # 총 소요 시간: 5개 심볼 × (처리시간 + 5초) = 약 50초
```

**발생하던 문제점**

- 전체 작업 시간: 약 50초 (심볼 수에 비례하여 증가)
- CPU 유휴 시간: 대부분의 시간을 대기로 소모
- 확장성 제약: 심볼이 늘어날수록 선형적으로 시간 증가

### 리팩토링 후 프로세스

**병렬 실행기 클래스 구현**

ThreadPoolExecutor를 활용하여 여러 심볼을 동시에 처리하도록 개선했다.

```python
# 개선: 병렬 처리 시스템
from concurrent.futures import ThreadPoolExecutor
import time
from app.common.utils.logging_config import get_logger
from app.common.exceptions.handlers import handle_scheduler_errors

logger = get_logger("parallel_scheduler")

class ParallelExecutor:
    """병렬 작업 실행기"""

    def __init__(self, max_workers=2):
        self.max_workers = max_workers

    def run_symbol_tasks_parallel(self, task_func, symbols, delay=1.0):
        """
        심볼들을 병렬로 처리

        Args:
            task_func: 각 심볼에 대해 실행할 함수
            symbols: 처리할 심볼 리스트
            delay: 배치 간 지연 시간 (API 제한 고려)

        Returns:
            List: 각 심볼의 처리 결과
        """
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 모든 작업을 동시에 제출
            future_to_symbol = {
                executor.submit(task_func, symbol): symbol
                for symbol in symbols
            }

            # 결과 수집
            for future in future_to_symbol:
                symbol = future_to_symbol[future]
                try:
                    result = future.result(timeout=30)  # 30초 타임아웃
                    results.append(result)
                    logger.info("task_completed", symbol=symbol, success=True)
                except Exception as e:
                    logger.error("task_failed", symbol=symbol, error=str(e))
                    results.append(None)

                # 배치 간 지연 (API 제한 고려)
                if delay > 0:
                    time.sleep(delay)

        return results

# 병렬 실행기 인스턴스 생성 (max_workers 제한으로 DB 연결 부하 감소)
executor = ParallelExecutor(max_workers=2)
```

**병렬 스케줄러 작업 구현**

```python
# 개선: 병렬 뉴스 크롤링

from app.news_crawler.service.investing_news_crawler import InvestingNewsCrawler
from app.news_crawler.service.yahoo_news_crawler import YahooNewsCrawler

@handle_scheduler_errors(reraise=False, return_on_error=None)
def run_integrated_news_crawling_parallel():
    """통합 뉴스 크롤링 (경제 뉴스 + 지수 뉴스)"""


    logger.info(
        "integrated_news_crawling_started",
        sources=["investing_economic", "yahoo_index"],
    )

    # 1. Investing 경제 뉴스 크롤링 (병렬 처리)
    def process_investing_symbol(symbol):
        logger.debug("processing_symbol", source="investing_economic", symbol=symbol)
        crawler = InvestingNewsCrawler(symbol)
        result = crawler.process_all()
        return result

    # 경제 뉴스 심볼들을 병렬로 처리
    economic_symbols = ["economic-calendar", "market-news", "crypto-news"]
    economic_results = executor.run_symbol_tasks_parallel(
        process_investing_symbol,
        economic_symbols,
        delay=1.0
    )

    # 2. Yahoo 지수 뉴스 크롤링 (병렬 처리)
    def process_yahoo_symbol(symbol):
        logger.debug("processing_symbol", source="yahoo_index", symbol=symbol)
        crawler = YahooNewsCrawler(symbol)
        result = crawler.process_all()
        return result

    # 지수 심볼들을 병렬로 처리
    index_symbols = ["^IXIC", "^GSPC", "^DJI"]
    index_results = executor.run_symbol_tasks_parallel(
        process_yahoo_symbol,
        index_symbols,
        delay=1.0
    )

    # 결과 집계
    economic_success = sum(1 for r in economic_results if r is not None)
    index_success = sum(1 for r in index_results if r is not None)

    logger.info(
        "integrated_news_crawling_completed",
        economic_success=economic_success,
        economic_total=len(economic_symbols),
        index_success=index_success,
        index_total=len(index_symbols),
        total_success=economic_success + index_success,
        total_count=len(economic_symbols) + len(index_symbols)
    )
```

**실행 시간 측정 데코레이터**

```python
# 성능 측정을 위한 데코레이터
from functools import wraps
import time

def measure_execution_time(func):
    """함수 실행 시간 측정 데코레이터"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            duration = end_time - start_time
            logger.info(
                "execution_time_measured",
                function=func.__name__,
                duration_seconds=round(duration, 2)
            )
    return wrapper

# 사용 예시
@measure_execution_time
@handle_scheduler_errors(reraise=False, return_on_error=None)
def run_news_crawling_parallel():
    # 병렬 처리 로직
    pass
```

### 성능 개선 결과

**정량적 성과**

- 작업 처리 시간: 50초 → 10초 (80% 단축)
- CPU 활용도: 40% 향상 (유휴 시간 감소)
- 처리 효율성: 5배 향상

**시스템 개선 효과**

- 실시간 성공/실패 모니터링 가능
- 개별 작업 타임아웃 설정으로 안정성 확보
- API 제한 고려한 지능적 지연 처리

## 3. 세션 관리 개선

### 기존 프로세스의 문제점

**동작 방식**

각 서비스마다 세션을 직접 생성하고 관리하는 방식이 달랐다.

```python
# 기존: 일관성 없는 세션 관리
class PriceService:
    def get_price(self, symbol):
        session = SessionLocal()  # 직접 생성
        try:
            result = session.query(PriceModel).filter_by(symbol=symbol).first()
            return result
        except Exception as e:
            # 에러 처리 방식이 제각각
            session.rollback()
            raise e
        finally:
            session.close()

class NewsService:
    def get_news(self, symbol):
        session = SessionLocal()  # 또 다른 방식
        # 세션 정리 로직이 다름
        result = session.query(NewsModel).filter_by(symbol=symbol).all()
        session.close()  # rollback 없음
        return result
```

**발생하던 문제점**

- 세션 누수 가능성 (finally 블록 누락 시)
- 트랜잭션 관리 불일치
- 에러 처리 방식 상이
- 코드 중복 및 유지보수 어려움

### 리팩토링 후 프로세스

**세션 컨텍스트 매니저 구현**

컨텍스트 매니저를 도입하여 일관된 세션 관리 패턴을 구축했다.

```python
# 개선: 세션 컨텍스트 매니저
from contextlib import contextmanager
from app.common.infra.database.config.database_config import SessionLocal
from app.common.utils.logging_config import get_logger

logger = get_logger("session_manager")

@contextmanager
def session_scope():
    """
    세션 컨텍스트 매니저

    자동으로 세션 생성, 커밋/롤백, 정리를 처리
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
        logger.debug("session_committed")
    except Exception as e:
        session.rollback()
        logger.error("session_rollback", error=str(e))
        raise e
    finally:
        session.close()
        logger.debug("session_closed")
```

**개선된 서비스 클래스들**

```python
# 개선: 일관된 세션 관리
class PriceService:
    def get_price_data(self, symbol):
        """가격 데이터 조회"""
        with session_scope() as session:
            result = session.query(PriceModel).filter_by(symbol=symbol).all()
            return result
        # 자동으로 세션 정리됨

    def save_price_data(self, price_data):
        """가격 데이터 저장"""
        with session_scope() as session:
            # 트랜잭션 자동 관리
            price = PriceModel(**price_data)
            session.add(price)
            # commit/rollback 자동 처리
            return price.id

class NewsService:
    def get_news_by_symbol(self, symbol):
        """심볼별 뉴스 조회"""
        with session_scope() as session:
            result = session.query(NewsModel).filter_by(symbol=symbol).all()
            return result

    def bulk_save_news(self, news_list):
        """뉴스 데이터 일괄 저장"""
        with session_scope() as session:
            # 대량 데이터도 안전하게 처리
            for news_data in news_list:
                news = NewsModel(**news_data)
                session.add(news)
            # 모든 데이터가 한 트랜잭션으로 처리됨
            return len(news_list)
```

**고급 세션 관리 패턴**

```python
# 읽기 전용 세션 (성능 최적화)
@contextmanager
def readonly_session_scope():
    """읽기 전용 세션 (커밋 없음)"""
    session = SessionLocal()
    try:
        yield session
        # 읽기 전용이므로 커밋하지 않음
    except Exception as e:
        logger.error("readonly_session_error", error=str(e))
        raise e
    finally:
        session.close()

# 배치 처리용 세션 (대량 데이터)
@contextmanager
def batch_session_scope(batch_size=1000):
    """배치 처리용 세션"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error("batch_session_error", error=str(e))
        raise e
    finally:
        session.close()

# 사용 예시
class TechnicalAnalysisService:
    def get_analysis_data(self, symbol):
        """분석 데이터 조회 (읽기 전용)"""
        with readonly_session_scope() as session:
            return session.query(AnalysisModel).filter_by(symbol=symbol).all()

    def bulk_save_analysis(self, analysis_list):
        """분석 결과 대량 저장"""
        with batch_session_scope() as session:
            session.bulk_insert_mappings(AnalysisModel, analysis_list)
```

### 성능 개선 결과

**정량적 성과**

- 세션 누수: 100% 방지
- 코드 중복: 70% 감소
- 트랜잭션 일관성: 100% 보장

**개발 생산성 향상**

- 일관된 에러 처리 패턴
- 자동 리소스 정리
- 유지보수성 대폭 향상

## Phase 1 종합 성과

### 정량적 성과 요약

| 항목                       | 개선 전   | 개선 후  | 개선율    |
| -------------------------- | --------- | -------- | --------- |
| 스케줄러 처리 시간         | 50초      | 10초     | 80% 단축  |
| 데이터베이스 연결 오버헤드 | 높음      | 60% 감소 | 60% 개선  |
| 연결 끊김 오류             | 일일 50건 | 일일 5건 | 90% 감소  |
| 세션 누수                  | 발생      | 0건      | 100% 방지 |
| CPU 활용도                 | 낮음      | 40% 향상 | 40% 개선  |

### 시스템 안정성 향상

**예측 가능한 성능**

- 작업 시간이 일정하게 유지됨
- 리소스 사용량 안정화
- 시스템 부하 분산

**자동 복구 기능**

- 연결 문제 시 자동 재연결
- 세션 오류 시 자동 롤백
- 작업 실패 시 격리된 처리

**확장성 확보**

- 동시 처리 능력 향상
- 심볼 수 증가에 대한 대응력
- 리소스 효율적 활용

## 구현 시 고려사항

### 1. API 제한 준수

```python
# API 호출 간격 조정
executor = ParallelExecutor(max_workers=2)  # 동시 작업 수 제한
results = executor.run_symbol_tasks_parallel(
    process_symbol,
    symbols,
    delay=1.0  # 1초 지연으로 API 제한 준수
)
```

### 2. 메모리 사용량 모니터링

```python
# 메모리 사용량 체크 (다음 Phase에서 상세 다룰 예정)
from app.common.utils.memory_optimizer import memory_monitor

@memory_monitor()
def run_heavy_task():
    # 메모리 사용량이 자동으로 모니터링됨
    pass
```

### 3. 에러 처리 표준화

```python
# 일관된 에러 처리 (다음 Phase에서 상세 다룰 예정)
from app.common.exceptions.handlers import handle_scheduler_errors

@handle_scheduler_errors(reraise=False, return_on_error=None)
def scheduler_task():
    # 에러 발생 시 자동으로 로깅 및 처리
    pass
```

### 4. 로깅 시스템 통합

```python
# 구조화된 로깅 (다음 Phase에서 상세 다룰 예정)
from app.common.utils.logging_config import get_logger

logger = get_logger("service_name")

# 구조화된 로그 메시지
logger.info(
    "task_completed",
    symbol=symbol,
    duration=duration,
    success=True
)
```

## 다음 단계

Phase 1 기반 최적화로 시스템 안정성을 확보했지만, 여전히 API 호출 최적화, 캐시 시스템 부재, 기술적 지표 계산 비효율 등의 성능 병목이 남아있다.

다음 포스트에서는 이러한 성능 병목을 해결하여 CPU 사용률을 53% 감소시키고 처리량을 300% 증가시킨 Phase 2 최적화 과정을 소개하겠다. API 호출 최적화, 기술적 지표 계산 최적화, 배치 처리 도입, 캐시 레이어 추상화를 통한 성능 향상 과정을 실제 코드와 함께 상세히 다룰 예정이다.

## 시리즈 목록

- \*\*[1편: 성능 문제 분석과 해결 방향](https://velog.io/@rlaejrqo465/Finstage-Market-Data-Python-%EC%84%B1%EB%8A%A5-%EC%B5%9C%EC%A0%81%ED%99%94-%EC%8B%9C%EB%A6%AC%EC%A6%88-15-%EC%84%B1%EB%8A%A5-%EB%AC%B8%EC%A0%9C-%EB%B6%84%EC%84%9D%EA%B3%BC-%ED%95%B4%EA%B2%B0-%EB%B0%A9%ED%96%A5)
- [2편: 기반 시스템 최적화 (Phase 1)](https://velog.io/@rlaejrqo465/Finstage-Market-Data-Python-%EC%84%B1%EB%8A%A5-%EC%B5%9C%EC%A0%81%ED%99%94-%EC%8B%9C%EB%A6%AC%EC%A6%88-25-%EA%B8%B0%EB%B0%98-%EC%8B%9C%EC%8A%A4%ED%85%9C-%EC%B5%9C%EC%A0%81%ED%99%94-Phase-1) ← 현재 글
- [3편: 성능 향상 (Phase 2)](https://velog.io/@rlaejrqo465/Finstage-Market-Data-Python-%EC%84%B1%EB%8A%A5-%EC%B5%9C%EC%A0%81%ED%99%94-%EC%8B%9C%EB%A6%AC%EC%A6%88-35-%EC%84%B1%EB%8A%A5-%ED%8F%AD%EB%B0%9C%EC%A0%81-%ED%96%A5%EC%83%81-Phase-2)
- [4편: 고급 시스템 구축 (Phase 3)](https://velog.io/@rlaejrqo465/Finstage-Market-Data-Python-%EC%84%B1%EB%8A%A5-%EC%B5%9C%EC%A0%81%ED%99%94-%EC%8B%9C%EB%A6%AC%EC%A6%88-45-%EA%B3%A0%EA%B8%89-%EC%8B%9C%EC%8A%A4%ED%85%9C-%EA%B5%AC%EC%B6%95-Phase-3)
- [5편: 메모리 관리 및 최종 성과](https://velog.io/@rlaejrqo465/Finstage-Market-Data-Python-%EC%84%B1%EB%8A%A5-%EC%B5%9C%EC%A0%81%ED%99%94-%EC%8B%9C%EB%A6%AC%EC%A6%88-55-%EB%A9%94%EB%AA%A8%EB%A6%AC-%EA%B4%80%EB%A6%AC-%EB%B0%8F-%EC%B5%9C%EC%A2%85-%EC%84%B1%EA%B3%BC)
