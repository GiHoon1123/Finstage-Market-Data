# Finstage Market Data - 개선 로드맵

## 개요

현재 Finstage Market Data 백엔드는 핵심 기능은 잘 작동하지만, 실제 운영 환경에서 안정적으로 서비스하기 위해서는 여러 부분의 개선이 필요합니다. 이 문서는 우선순위별로 개선해야 할 항목들을 정리했습니다.

---

## 🚨 높은 우선순위 (Critical)

### 1. 로깅 시스템 개선

**현재 문제점:**

```python
# 현재: print문 남발 (100개 이상)
print(f"✅ 경제 뉴스 크롤링 완료: {success_count}/{len(symbols)} 성공")
print(f"❌ {symbol} 처리 실패: {e}")
```

**개선 방안:**

```python
# 개선: 구조화된 로깅
import logging
import structlog

logger = structlog.get_logger()

logger.info(
    "news_crawling_completed",
    source="investing_economic",
    success_count=success_count,
    total_count=len(symbols),
    success_rate=success_count/len(symbols),
    duration_seconds=execution_time
)

logger.error(
    "symbol_processing_failed",
    symbol=symbol,
    error=str(e),
    error_type=type(e).__name__,
    traceback=traceback.format_exc()
)
```

**구체적 작업:**

- [ ] `structlog` 또는 `loguru` 도입
- [ ] 로그 레벨 설정 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- [ ] 로그 파일 로테이션 설정
- [ ] JSON 형태 구조화된 로그 포맷
- [ ] 모든 print문을 적절한 로그 레벨로 변경
- [ ] 로그 중앙화 (ELK Stack 또는 Grafana Loki)

### 2. 환경 설정 및 보안 강화

**현재 문제점:**

```python
# app/config.py
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "1234")  # 하드코딩된 기본값
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")      # 빈 문자열 기본값
```

**개선 방안:**

```python
# 개선: Pydantic Settings 사용
from pydantic import BaseSettings, validator
from typing import Optional

class Settings(BaseSettings):
    # 데이터베이스 설정
    mysql_host: str
    mysql_port: int = 3306
    mysql_user: str
    mysql_password: str  # 기본값 없음 (필수)
    mysql_database: str

    # API 키 설정
    openai_api_key: str  # 필수
    telegram_bot_token: str  # 필수
    telegram_chat_id: str  # 필수

    # 환경 설정
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    @validator('mysql_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

    @validator('openai_api_key')
    def validate_openai_key(cls, v):
        if not v.startswith('sk-'):
            raise ValueError('Invalid OpenAI API key format')
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

**구체적 작업:**

- [ ] Pydantic Settings 도입
- [ ] 환경별 설정 파일 분리 (.env.dev, .env.test, .env.prod)
- [ ] 필수 환경변수 검증 로직
- [ ] 민감 정보 암호화 (AWS Secrets Manager, HashiCorp Vault)
- [ ] 설정 문서화 (README에 필수 환경변수 목록)
- [ ] 설정 검증 테스트 코드

### 3. 에러 처리 표준화

**현재 문제점:**

```python
# 일관성 없는 에러 처리
try:
    result = some_function()
except Exception as e:
    print(f"❌ 실패: {e}")  # 어떤 곳
    return None

try:
    result = some_function()
except Exception as e:
    print(f"❌ 실패: {e}")  # 다른 곳
    raise e
```

**개선 방안:**

```python
# 커스텀 예외 클래스
class FinstageException(Exception):
    """Base exception for Finstage application"""
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class DataCollectionError(FinstageException):
    """Data collection related errors"""
    pass

class AnalysisError(FinstageException):
    """Technical analysis related errors"""
    pass

class NotificationError(FinstageException):
    """Notification sending related errors"""
    pass

# 에러 핸들러 데코레이터
def handle_errors(error_type: Type[FinstageException] = FinstageException):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except error_type as e:
                logger.error(
                    "handled_error",
                    function=func.__name__,
                    error_code=e.error_code,
                    message=e.message,
                    details=e.details
                )
                raise
            except Exception as e:
                logger.error(
                    "unhandled_error",
                    function=func.__name__,
                    error=str(e),
                    traceback=traceback.format_exc()
                )
                raise error_type(f"Unexpected error in {func.__name__}: {str(e)}")
        return wrapper
    return decorator
```

**구체적 작업:**

- [ ] 커스텀 예외 클래스 정의
- [ ] 에러 핸들링 데코레이터 구현
- [ ] 모든 함수에 일관된 에러 처리 적용
- [ ] 에러 코드 체계 정의
- [ ] 에러 알림 시스템 (Slack, 텔레그램)

---

## ⚠️ 중간 우선순위 (High)

### 4. 테스트 코드 구축

**현재 문제점:**

- 단위 테스트 없음
- 통합 테스트 1개뿐
- 외부 API 모킹 없음
- 테스트 커버리지 불명

**개선 방안:**

```python
# pytest + pytest-asyncio 사용
import pytest
from unittest.mock import Mock, patch
from app.news_crawler.service.investing_news_crawler import InvestingNewsCrawler

class TestInvestingNewsCrawler:
    @pytest.fixture
    def crawler(self):
        return InvestingNewsCrawler("test-symbol")

    @patch('requests.get')
    def test_fetch_rss_success(self, mock_get, crawler):
        # Given
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<rss>...</rss>"
        mock_get.return_value = mock_response

        # When
        result = crawler.fetch_rss()

        # Then
        assert result is not None
        assert len(result) > 0
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_fetch_rss_failure(self, mock_get, crawler):
        # Given
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        # When
        result = crawler.fetch_rss()

        # Then
        assert result == []

    @pytest.mark.asyncio
    async def test_parallel_processing(self):
        # 병렬 처리 테스트
        pass

# 통합 테스트
class TestNewsProcessingFlow:
    def test_end_to_end_news_processing(self):
        # 전체 뉴스 처리 플로우 테스트
        pass
```

**구체적 작업:**

- [ ] pytest, pytest-asyncio, pytest-cov 설정
- [ ] 단위 테스트 작성 (각 서비스 클래스별)
- [ ] 통합 테스트 작성 (전체 플로우)
- [ ] 외부 API 모킹 (requests-mock, aioresponses)
- [ ] 테스트 데이터베이스 설정 (SQLite in-memory)
- [ ] 테스트 커버리지 80% 이상 목표
- [ ] CI/CD에서 테스트 자동 실행

### 5. 모니터링 및 관찰성 강화

**현재 문제점:**

- 성능 메트릭 수집 부족
- 비즈니스 메트릭 추적 없음
- 헬스체크 엔드포인트 부족
- 알림 시스템 단순

**개선 방안:**

```python
# Prometheus 메트릭 수집
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# 메트릭 정의
news_processed_total = Counter(
    'news_processed_total',
    'Total number of news articles processed',
    ['source', 'status']
)

analysis_duration_seconds = Histogram(
    'analysis_duration_seconds',
    'Time spent on technical analysis',
    ['symbol', 'strategy']
)

active_signals_gauge = Gauge(
    'active_signals_total',
    'Number of active trading signals',
    ['signal_type', 'confidence_level']
)

# 메트릭 수집
@news_processed_total.labels(source='investing', status='success').count_exceptions()
def process_investing_news():
    # 뉴스 처리 로직
    pass

# 헬스체크 엔드포인트
@router.get("/health")
async def health_check():
    checks = {
        "database": await check_database_connection(),
        "telegram": await check_telegram_connection(),
        "external_apis": await check_external_apis(),
        "scheduler": check_scheduler_status(),
        "disk_space": check_disk_space(),
        "memory_usage": check_memory_usage()
    }

    overall_status = "healthy" if all(checks.values()) else "unhealthy"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
        "version": get_app_version(),
        "uptime": get_uptime()
    }
```

**구체적 작업:**

- [ ] Prometheus 메트릭 수집 구현
- [ ] Grafana 대시보드 구축
- [ ] 헬스체크 엔드포인트 구현
- [ ] 알림 시스템 고도화 (PagerDuty, Slack)
- [ ] 비즈니스 메트릭 정의 및 수집
- [ ] 성능 임계값 설정 및 알림

### 6. 데이터베이스 최적화

**현재 문제점:**

- 인덱스 최적화 ���족
- 쿼리 성능 모니터링 없음
- 데이터 정리 정책 없음
- 백업 전략 없음

**개선 방안:**

```python
# 인덱스 최적화
class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    published_at = Column(DateTime, nullable=False)
    source = Column(String(50), nullable=False)

    # 복합 인덱스 추가
    __table_args__ = (
        Index('idx_symbol_published', 'symbol', 'published_at'),
        Index('idx_source_published', 'source', 'published_at'),
        Index('idx_published_desc', 'published_at', postgresql_using='btree'),
    )

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
            duration=total,
            statement=statement[:200],
            parameters=parameters
        )
```

**구체적 작업:**

- [ ] 쿼리 성능 분석 및 인덱스 최적화
- [ ] 슬로우 쿼리 모니터링
- [ ] 데이터 파티셔닝 검토
- [ ] 자동 백업 시스템 구축
- [ ] 데이터 보존 정책 수립
- [ ] 읽기 전용 복제본 구성

---

## 📈 낮은 우선순위 (Medium)

### 7. 코드 품질 개선

**현재 문제점:**

- 타입 힌트 부족
- 문서화 일관성 부족
- 매직 넘버 하드코딩
- 긴 함수들

**개선 방안:**

```python
# 타입 힌트 강화
from typing import List, Dict, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum

class SignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

@dataclass
class AnalysisResult:
    symbol: str
    signal_type: SignalType
    confidence: float
    timestamp: datetime
    indicators: Dict[str, float]

def analyze_symbol(
    symbol: str,
    strategies: List[str],
    timeframe: str = "1d"
) -> Optional[AnalysisResult]:
    """
    심볼에 대한 기술적 분석 수행

    Args:
        symbol: 분석할 심볼 (예: "AAPL", "^IXIC")
        strategies: 사용할 분석 전략 목록
        timeframe: 분석 시간프레임 (기본값: "1d")

    Returns:
        분석 결과 또는 None (분석 실패 시)

    Raises:
        AnalysisError: 분석 중 오류 발생 시

    Example:
        >>> result = analyze_symbol("AAPL", ["RSI", "MA_CROSS"])
        >>> if result and result.signal_type == SignalType.BUY:
        ...     print(f"Buy signal for {result.symbol}")
    """
    pass

# 상수 정의
class Config:
    # 병렬 처리 설정
    MAX_WORKERS = 2
    API_DELAY_SECONDS = 0.5

    # 분석 설정
    RSI_OVERSOLD_THRESHOLD = 30
    RSI_OVERBOUGHT_THRESHOLD = 70
    MA_BREAKOUT_THRESHOLD = 0.02  # 2%

    # 알림 설정
    MIN_CONFIDENCE_FOR_ALERT = 75
    ALERT_COOLDOWN_MINUTES = 60
```

**구체적 작업:**

- [ ] 모든 함수에 타입 힌트 추가
- [ ] docstring 표준화 (Google 스타일)
- [ ] 매직 넘버를 상수로 분리
- [ ] 긴 함수 리팩토링 (단일 책임 원칙)
- [ ] mypy를 통한 타입 체크
- [ ] black, isort를 통한 코드 포맷팅

### 8. 성능 최적화

**현재 문제점:**

- 캐싱 전략 부족
- 데이터베이스 N+1 쿼리 문제
- 메모리 사용량 최적화 부족

**개선 방안:**

```python
# Redis 캐싱
import redis
from functools import wraps
import json
import pickle

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(expiration: int = 300):
    """결과 캐싱 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

            # 캐시에서 조회
            cached = redis_client.get(cache_key)
            if cached:
                return pickle.loads(cached)

            # 함수 실행 및 캐시 저장
            result = func(*args, **kwargs)
            redis_client.setex(
                cache_key,
                expiration,
                pickle.dumps(result)
            )
            return result
        return wrapper
    return decorator

@cache_result(expiration=600)  # 10분 캐싱
def get_technical_analysis(symbol: str) -> Dict:
    # 기술적 분석 수행
    pass

# 배치 처리 최적화
async def process_symbols_in_batches(
    symbols: List[str],
    batch_size: int = 10
) -> List[Any]:
    """심볼들을 배치로 나누어 처리"""
    results = []
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        batch_results = await asyncio.gather(*[
            process_single_symbol(symbol) for symbol in batch
        ])
        results.extend(batch_results)

        # 배치 간 지연
        if i + batch_size < len(symbols):
            await asyncio.sleep(1.0)

    return results
```

**구체적 작업:**

- [ ] Redis 캐싱 시스템 도입
- [ ] 데이터베이스 쿼리 최적화
- [ ] 메모리 프로파일링 및 최적화
- [ ] 비동기 처리 성능 튜닝
- [ ] 응답 시간 최적화

### 9. 보안 강화

**현재 문제점:**

- API 키 보안 취약
- 입력 검증 부족
- 레이트 리미팅 없음

**개선 방안:**

```python
# API 키 암호화
from cryptography.fernet import Fernet
import base64

class SecureConfig:
    def __init__(self):
        self.cipher_suite = Fernet(self._get_encryption_key())

    def _get_encryption_key(self) -> bytes:
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            raise ValueError("ENCRYPTION_KEY environment variable required")
        return base64.urlsafe_b64decode(key)

    def encrypt_value(self, value: str) -> str:
        return self.cipher_suite.encrypt(value.encode()).decode()

    def decrypt_value(self, encrypted_value: str) -> str:
        return self.cipher_suite.decrypt(encrypted_value.encode()).decode()

# 입력 검증
from pydantic import BaseModel, validator

class SymbolRequest(BaseModel):
    symbol: str
    timeframe: str = "1d"

    @validator('symbol')
    def validate_symbol(cls, v):
        if not v.isalnum() and '^' not in v:
            raise ValueError('Invalid symbol format')
        if len(v) > 10:
            raise ValueError('Symbol too long')
        return v.upper()

    @validator('timeframe')
    def validate_timeframe(cls, v):
        allowed = ['1m', '5m', '15m', '1h', '1d', '1w', '1M']
        if v not in allowed:
            raise ValueError(f'Timeframe must be one of {allowed}')
        return v

# 레이트 리미팅
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/analysis/{symbol}")
@limiter.limit("10/minute")
async def get_analysis(request: Request, symbol: str):
    # API 엔드포인트
    pass
```

**구체적 작업:**

- [ ] API 키 암호화 저장
- [ ] 입력 검증 강화
- [ ] 레이트 리미팅 구현
- [ ] HTTPS 강제 적용
- [ ] 보안 헤더 설정
- [ ] 취약점 스캔 자동화

---

## 🚀 장기 계획 (Low Priority)

### 10. 아키텍처 개선

**마이크로서비스 분리:**

- 뉴스 크롤링 서비스
- 기술적 분석 서비스
- 알림 서비스
- API 게이트웨이

**이벤트 기반 아키텍처:**

- Apache Kafka 또는 RabbitMQ 도입
- 이벤트 소싱 패턴 적용
- CQRS 패턴 검토

### 11. 배포 및 인프라

**컨테이너화:**

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Kubernetes 배포:**

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: finstage-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: finstage-api
  template:
    metadata:
      labels:
        app: finstage-api
    spec:
      containers:
        - name: api
          image: finstage/api:latest
          ports:
            - containerPort: 8000
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: db-secret
                  key: url
```

**구체적 작업:**

- [ ] Docker 컨테이너화
- [ ] Kubernetes 배포 설정
- [ ] CI/CD 파이프라인 구축
- [ ] 무중단 배포 구현
- [ ] 오토스케일링 설정

---

## 📋 우선순위별 실행 계획

### Phase 1 (1-2개월): 안정성 확보

1. 로깅 시스템 개선
2. 환경 설정 및 보안 강화
3. 에러 처리 표준화
4. 기본 테스트 코드 작성

### Phase 2 (2-3개월): 관찰성 및 성능

1. 모니터링 시스템 구축
2. 데이터베이스 최적화
3. 캐싱 시스템 도입
4. 성능 튜닝

### Phase 3 (3-6개월): 확장성 및 운영

1. 코드 품질 개선
2. 보안 강화
3. 배포 자동화
4. 아키텍처 개선 검토

---

## 📊 성공 지표 (KPI)

### 기술적 지표

- **테스트 커버리지**: 80% 이상
- **평균 응답 시간**: 500ms 이하
- **시스템 가동률**: 99.9% 이상
- **에러율**: 1% 이하

### 운영 지표

- **배포 빈도**: 주 1회 이상
- **배포 실패율**: 5% 이하
- **평균 복구 시간**: 30분 이하
- **보안 취약점**: 0개 유지

### 비즈니스 지표

- **신호 정확도**: 75% 이상 유지
- **알림 전송 성공률**: 99% 이상
- **사용자 만족도**: 4.5/5.0 이상

---

이 로드맵을 통해 현재의 프로토타입 수준에서 **운영 가능한 안정적인 서비스**로 발전시킬 수 있을 것입니다.
