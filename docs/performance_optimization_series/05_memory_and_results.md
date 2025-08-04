[Finstage Market Data] Python 성능 최적화 시리즈 (5/5) - 메모리 관리 및 최종 성과

## 개요

Phase 3에서 고급 시스템을 구축한 후, 마지막으로 메모리 관리 시스템, 데이터베이스 최적화, 모니터링 및 관찰성, 개발 생산성 향상을 통해 17개 시스템 최적화를 완성했다. 전체 프로젝트의 최종 성과와 핵심 인사이트, 향후 발전 방향을 정리한다.

## 추가 개선 영역

### 1. 메모리 관리 시스템

**LRU 캐시 시스템 구현**

TTL 지원과 스레드 안전성을 보장하는 메모리 캐시를 구축했다.

```python
# 메모리 관리 시스템
import time
from typing import Any, Optional
from functools import wraps

class LRUCache:
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.cache = {}
        self.timestamps = {}
        self.access_order = []
        self.max_size = max_size
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None

        # TTL 확인
        if self._is_expired(key):
            self.delete(key)
            return None

        # LRU 순서 업데이트
        self.access_order.remove(key)
        self.access_order.append(key)

        return self.cache[key]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        # 캐시 크기 제한
        if len(self.cache) >= self.max_size and key not in self.cache:
            self._evict_oldest()

        self.cache[key] = value
        self.timestamps[key] = (time.time(), ttl or self.default_ttl)

        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)

        return True

# 캐시 데코레이터
def cache_result(cache_name: str = "default", ttl: int = 300):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

            # 캐시 확인
            cached_result = memory_cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 함수 실행 및 캐시 저장
            result = func(*args, **kwargs)
            memory_cache.set(cache_key, result, ttl)

            return result
        return wrapper
    return decorator

memory_cache = LRUCache(max_size=5000, default_ttl=600)
```

**DataFrame 메모리 최적화**

pandas DataFrame의 메모리 사용량을 자동으로 최적화했다.

```python
# DataFrame 메모리 최적화
import pandas as pd
from functools import wraps

def optimize_dataframe_memory(aggressive: bool = False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            if isinstance(result, pd.DataFrame):
                result = _optimize_dataframe(result, aggressive)

            return result
        return wrapper
    return decorator

def _optimize_dataframe(df: pd.DataFrame, aggressive: bool = False) -> pd.DataFrame:
    """DataFrame 메모리 최적화"""
    original_memory = df.memory_usage(deep=True).sum()

    for col in df.columns:
        col_type = df[col].dtype

        # 정수형 다운캐스팅
        if col_type in ['int64', 'int32', 'int16']:
            df[col] = pd.to_numeric(df[col], downcast='integer')

        # 실수형 다운캐스팅
        elif col_type in ['float64', 'float32']:
            if aggressive:
                df[col] = pd.to_numeric(df[col], downcast='float')

        # 문자열 카테고리화
        elif col_type == 'object':
            unique_ratio = df[col].nunique() / len(df)
            if unique_ratio < 0.5:  # 중복이 많은 경우
                df[col] = df[col].astype('category')

    optimized_memory = df.memory_usage(deep=True).sum()
    reduction = (original_memory - optimized_memory) / original_memory * 100

    logger.debug(
        "dataframe_optimized",
        original_mb=round(original_memory / 1024 / 1024, 2),
        optimized_mb=round(optimized_memory / 1024 / 1024, 2),
        reduction_percent=round(reduction, 1)
    )

    return df
```

**성능 개선 결과**

- DataFrame 메모리 사용량: 100MB → 65MB (35% 절약)
- 시스템 메모리 사용률: 85% → 60% (29% 감소)
- 가비지 컬렉션 빈도: 30초 → 2분 (75% 감소)

### 2. 데이터베이스 최적화

**쿼리 성능 모니터링**

슬로우 쿼리 감지 및 자동 최적화 시스템을 구축했다.

```python
# 쿼리 성능 모니터링
from sqlalchemy import event
from sqlalchemy.engine import Engine
import time

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time

    if total > 1.0:  # 1초 이상 걸린 쿼리 로깅
        logger.warning(
            "slow_query_detected",
            duration=round(total, 3),
            statement=statement[:200],
            parameters=str(parameters)[:100] if parameters else None
        )

# 인덱스 최적화 분석
class IndexOptimizer:
    def analyze_table_indexes(self, table_name: str) -> dict:
        """테이블 인덱스 분석"""
        with session_scope() as session:
            # 인덱스 사용률 분석
            result = session.execute(f"""
                SHOW INDEX FROM {table_name}
            """)

            indexes = result.fetchall()

            analysis = {
                'table': table_name,
                'total_indexes': len(indexes),
                'recommendations': []
            }

            # 인덱스 최적화 권장사항 생성
            if 'symbol' in [idx[4] for idx in indexes]:
                if 'date' in [idx[4] for idx in indexes]:
                    analysis['recommendations'].append(
                        "Consider composite index on (symbol, date) for better performance"
                    )

            return analysis
```

**성능 개선 결과**

- 쿼리 성능: 로그 분석을 통한 쿼리 튜닝으로 50% 향상
- 슬로우 쿼리: 자동 감지 및 알림
- 인덱스: 옵티마이저 분석을 통한 인덱스 최적화

### 3. 모니터링 및 관찰성 강화

**종합 헬스체크 시스템**

시스템 전체 상태를 실시간으로 모니터링하는 시스템을 구축했다.

```python
# 종합 헬스체크 시스템
import psutil
from datetime import datetime

class HealthChecker:
    def __init__(self):
        self.checks = {
            'database': self._check_database,
            'memory': self._check_memory,
            'cpu': self._check_cpu,
            'websocket': self._check_websocket,
            'task_queue': self._check_task_queue
        }

    async def get_health_status(self) -> dict:
        """전체 시스템 헬스체크"""
        results = {}
        overall_healthy = True

        for check_name, check_func in self.checks.items():
            try:
                result = await check_func()
                results[check_name] = result

                if not result.get('healthy', False):
                    overall_healthy = False

            except Exception as e:
                results[check_name] = {
                    'healthy': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                overall_healthy = False

        return {
            'status': 'healthy' if overall_healthy else 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'checks': results
        }

    async def _check_database(self) -> dict:
        """데이터베이스 상태 확인"""
        try:
            with session_scope() as session:
                session.execute("SELECT 1")

            return {
                'healthy': True,
                'message': 'Database connection successful',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def _check_memory(self) -> dict:
        """메모리 상태 확인"""
        memory = psutil.virtual_memory()

        return {
            'healthy': memory.percent < 90,
            'usage_percent': memory.percent,
            'available_gb': round(memory.available / 1024 / 1024 / 1024, 2),
            'timestamp': datetime.now().isoformat()
        }

health_checker = HealthChecker()

# API 엔드포인트
@router.get("/health")
async def health_check():
    return await health_checker.get_health_status()
```

**성능 개선 결과**

- 시스템 상태 실시간 추적
- 자동 알림 시스템 구축
- 99.9% 시스템 가용성 달성

### 4. 개발 생산성 향상

**로깅 시스템 개선**

print문을 구조화된 로깅으로 전환했다.

```python
# 구조화된 로깅 시스템
import structlog
from datetime import datetime

def get_logger(name: str):
    """구조화된 로거 생성"""
    return structlog.get_logger(name)

# 로깅 설정
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# 사용 예시
logger = get_logger("service_name")

logger.info(
    "task_completed",
    symbol="AAPL",
    duration=2.5,
    success=True,
    result_count=100
)
```

**에러 처리 표준화**

커스텀 예외 클래스와 데코레이터 기반 에러 핸들링을 구축했다.

```python
# 표준화된 에러 처리
from enum import Enum

class ErrorCode(Enum):
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    API_ERROR = "API_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"

class FinstageException(Exception):
    def __init__(self, message: str, error_code: ErrorCode, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

def handle_errors(default_exception=FinstageException):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except FinstageException:
                raise
            except Exception as e:
                logger.error(
                    "unhandled_error",
                    function=func.__name__,
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise default_exception(
                    f"Unexpected error in {func.__name__}: {str(e)}",
                    ErrorCode.UNKNOWN_ERROR
                )
        return wrapper
    return decorator
```

**성능 개선 결과**

- 개발 효율성 대폭 향상
- 일관된 에러 처리 패턴
- 운영 환경 안정성 확보

## 전체 프로젝트 최종 성과

### 정량적 성과 종합

| 항목                   | 개선 전      | 개선 후        | 개선율         |
| ---------------------- | ------------ | -------------- | -------------- |
| **스케줄러 처리 시간** | 50초         | 10초           | **80% 단축**   |
| **API 응답 시간**      | 1.2초        | 0.3초          | **75% 단축**   |
| **CPU 사용률**         | 85%          | 40%            | **53% 감소**   |
| **메모리 사용량**      | 1.2GB        | 0.8GB          | **33% 감소**   |
| **동시 요청 처리**     | 50 req/s     | 200 req/s      | **300% 증가**  |
| **실시간 데이터 지연** | 30-60초      | 1-2초          | **95% 감소**   |
| **작업 큐 처리량**     | 10 tasks/min | 100+ tasks/min | **1000% 증가** |
| **시스템 가용성**      | -            | 99.9%          | **신규 달성**  |
| **캐시 히트율**        | 0%           | 85%            | **신규 달성**  |
| **네트워크 사용량**    | 높음         | 92% 절약       | **92% 개선**   |

## 핵심 인사이트

### 1. 가장 효과적이었던 최적화

**스케줄러 병렬화 (80% 성능 향상)**

- 순차 처리를 병렬 처리로 전환
- ThreadPoolExecutor 활용
- API 제한 고려한 지능적 지연

**WebSocket 실시간 스트리밍 (95% 지연 감소)**

- REST API 폴링 → WebSocket 양방향 통신
- 서버 요청 99.7% 감소
- 네트워크 사용량 92% 절약

**메모리 관리 시스템 (35% 메모리 절약)**

- LRU 캐시 + TTL 지원
- DataFrame 자동 최적화
- 가비지 컬렉션 빈도 75% 감소

### 2. 예상치 못한 발견들

**캐시 히트율의 중요성**

- 85% 히트율 달성으로 CPU 사용량 80% 감소
- 단순한 메모리 캐시만으로도 극적인 성능 향상

**비동기 처리의 한계**

- I/O 바운드 작업에는 효과적
- CPU 바운드 작업은 ThreadPoolExecutor가 더 효과적

**모니터링의 운영 가치**

- 실시간 모니터링으로 99.9% 가용성 달성
- 자동 튜닝으로 성능 저하 사전 방지

### 3. 제한된 환경에서의 최적화

**외부 인프라 없이 달성한 성과**

- Redis 없이 메모리 캐시로 85% 히트율
- 메시지 큐 없이 내장형 작업 큐로 처리량 증가
- 외부 모니터링 도구 없이 Prometheus 메트릭 구축

## 비즈니스 임팩트

### 사용자 경험 개선

- **실시간성**: 30-60초 → 1-2초 지연으로 즉시성 확보
- **안정성**: 99.9% 가용성으로 서비스 신뢰도 향상
- **응답성**: API 응답 시간 75% 단축으로 사용자 만족도 증가

### 운영 효율성 향상

- **리소스 최적화**: CPU 53% 감소, 메모리 33% 감소로 비용 절약
- **확장성**: 동시 사용자 300% 증가 지원
- **유지보수성**: 구조화된 로깅과 모니터링으로 운영 부담 감소

### 개발 생산성 향상

- **표준화**: 일관된 에러 처리와 로깅 패턴
- **자동화**: 성능 모니터링과 자동 튜닝
- **가시성**: 실시간 성능 추적과 알림 시스템

## 결론

17개 시스템을 체계적으로 최적화하여 다음과 같은 성과를 달성했다:

### 기술적 성과

- **처리 시간 80% 단축**: 50초 → 10초
- **실시간 지연 95% 감소**: 30-60초 → 1-2초
- **시스템 가용성 99.9%**: 안정적인 서비스 운영
- **리소스 효율성**: CPU 53% 감소, 메모리 33% 감소

### 아키텍처 개선

- **실시간 시스템**: WebSocket 기반 즉시 데이터 전송
- **비동기 처리**: I/O 바운드 작업 최적화
- **분산 작업 큐**: 무거운 작업의 백그라운드 처리
- **자동 모니터링**: 실시간 성능 추적과 자동 튜닝

### 운영 완성도

- **구조화된 로깅**: 운영 환경 문제 추적 용이
- **표준화된 에러 처리**: 일관된 예외 관리
- **종합 헬스체크**: 시스템 상태 실시간 모니터링

이 프로젝트를 통해 제한된 환경에서도 체계적인 접근과 단계적 최적화를 통해 성능 향상을 달성할 수 있음을 배웠다. 특히 실제 서버 비용을 직접 부담하는 입장에서, 개선을 통해 비용이 점진적으로 절감되는 것을 체감하며 큰 보람을 느꼈다.

## 시리즈 목록

## 시리즈 목록

- [1편: 성능 문제 분석과 해결 방향](https://velog.io/@rlaejrqo465/Finstage-Market-Data-Python-%EC%84%B1%EB%8A%A5-%EC%B5%9C%EC%A0%81%ED%99%94-%EC%8B%9C%EB%A6%AC%EC%A6%88-15-%EC%84%B1%EB%8A%A5-%EB%AC%B8%EC%A0%9C-%EB%B6%84%EC%84%9D%EA%B3%BC-%ED%95%B4%EA%B2%B0-%EB%B0%A9%ED%96%A5)
- [2편: 기반 시스템 최적화 (Phase 1)](https://velog.io/@rlaejrqo465/Finstage-Market-Data-Python-%EC%84%B1%EB%8A%A5-%EC%B5%9C%EC%A0%81%ED%99%94-%EC%8B%9C%EB%A6%AC%EC%A6%88-25-%EA%B8%B0%EB%B0%98-%EC%8B%9C%EC%8A%A4%ED%85%9C-%EC%B5%9C%EC%A0%81%ED%99%94-Phase-1)
- [3편: 성능 향상 (Phase 2)](https://velog.io/@rlaejrqo465/Finstage-Market-Data-Python-%EC%84%B1%EB%8A%A5-%EC%B5%9C%EC%A0%81%ED%99%94-%EC%8B%9C%EB%A6%AC%EC%A6%88-35-%EC%84%B1%EB%8A%A5-%ED%8F%AD%EB%B0%9C%EC%A0%81-%ED%96%A5%EC%83%81-Phase-2)
- [4편: 고급 시스템 구축 (Phase 3)](https://velog.io/@rlaejrqo465/Finstage-Market-Data-Python-%EC%84%B1%EB%8A%A5-%EC%B5%9C%EC%A0%81%ED%99%94-%EC%8B%9C%EB%A6%AC%EC%A6%88-45-%EA%B3%A0%EA%B8%89-%EC%8B%9C%EC%8A%A4%ED%85%9C-%EA%B5%AC%EC%B6%95-Phase-3)
- [5편: 메모리 관리 및 최종 성과](https://velog.io/@rlaejrqo465/Finstage-Market-Data-Python-%EC%84%B1%EB%8A%A5-%EC%B5%9C%EC%A0%81%ED%99%94-%EC%8B%9C%EB%A6%AC%EC%A6%88-55-%EB%A9%94%EB%AA%A8%EB%A6%AC-%EA%B4%80%EB%A6%AC-%EB%B0%8F-%EC%B5%9C%EC%A2%85-%EC%84%B1%EA%B3%BC) ← 현재 글

---

**Finstage Market Data Python 성능 최적화 시리즈를 읽어주셔서 감사합니다.**

이 시리즈가 여러분의 성능 최적화 프로젝트에 도움이 되기를 바랍니다. 질문이나 피드백이 있으시면 언제든 연락 주세요.
